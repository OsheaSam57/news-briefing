from __future__ import annotations

import mimetypes
import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path


DEFAULT_DIGEST_PATH = Path("output/digest.html")
DEFAULT_SUBJECT = "Morning Briefing"
DEFAULT_BODY = "Your morning news briefing is attached."


@dataclass(frozen=True)
class EmailSettings:
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    email_from: str
    email_to: list[str]
    digest_path: Path
    subject: str
    body: str
    use_starttls: bool


def load_email_settings() -> EmailSettings:
    missing = [
        name
        for name in (
            "SMTP_HOST",
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "EMAIL_FROM",
            "EMAIL_TO",
        )
        if not os.getenv(name)
    ]
    if missing:
        raise ValueError(f"Missing email environment variables: {', '.join(missing)}")

    return EmailSettings(
        smtp_host=os.environ["SMTP_HOST"],
        smtp_port=int(os.getenv("SMTP_PORT") or "587"),
        smtp_username=os.environ["SMTP_USERNAME"],
        smtp_password=os.environ["SMTP_PASSWORD"],
        email_from=os.environ["EMAIL_FROM"],
        email_to=_split_recipients(os.environ["EMAIL_TO"]),
        digest_path=Path(os.getenv("DIGEST_OUTPUT_PATH") or DEFAULT_DIGEST_PATH),
        subject=os.getenv("EMAIL_SUBJECT") or DEFAULT_SUBJECT,
        body=os.getenv("EMAIL_BODY") or DEFAULT_BODY,
        use_starttls=_as_bool(os.getenv("SMTP_STARTTLS") or "true"),
    )


def send_digest(settings: EmailSettings) -> None:
    if not settings.digest_path.exists():
        raise FileNotFoundError(f"Digest attachment not found: {settings.digest_path}")

    message = build_digest_message(settings)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.use_starttls:
            smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


def build_digest_message(settings: EmailSettings) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = settings.subject
    message["From"] = settings.email_from
    message["To"] = ", ".join(settings.email_to)
    message.set_content(settings.body)

    attachment = settings.digest_path.read_bytes()
    content_type, _ = mimetypes.guess_type(settings.digest_path.name)
    maintype, subtype = (content_type or "text/html").split("/", maxsplit=1)
    message.add_attachment(
        attachment,
        maintype=maintype,
        subtype=subtype,
        filename=settings.digest_path.name,
    )
    return message


def _split_recipients(value: str) -> list[str]:
    recipients = [recipient.strip() for recipient in value.split(",") if recipient.strip()]
    if not recipients:
        raise ValueError("EMAIL_TO must contain at least one recipient.")
    return recipients


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    try:
        settings = load_email_settings()
        send_digest(settings)
    except Exception as exc:
        print(f"Email delivery failed: {exc}")
        return 1

    print(f"Emailed digest attachment to {', '.join(settings.email_to)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
