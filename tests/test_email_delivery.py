from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from news_briefing.email_delivery import EmailSettings, build_digest_message


class EmailDeliveryTests(unittest.TestCase):
    def test_builds_digest_message_with_html_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            digest_path = Path(directory) / "digest.html"
            digest_path.write_text("<html><body>Briefing</body></html>", encoding="utf-8")

            message = build_digest_message(
                EmailSettings(
                    smtp_host="smtp.example.com",
                    smtp_port=587,
                    smtp_username="user",
                    smtp_password="password",
                    email_from="briefing@example.com",
                    email_to=["first@example.com", "second@example.com"],
                    digest_path=digest_path,
                    subject="Morning Briefing",
                    body="Attached.",
                    use_starttls=True,
                )
            )

        self.assertEqual(message["Subject"], "Morning Briefing")
        self.assertEqual(message["From"], "briefing@example.com")
        self.assertEqual(message["To"], "first@example.com, second@example.com")

        attachments = list(message.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_filename(), "digest.html")
        self.assertEqual(attachments[0].get_content_type(), "text/html")


if __name__ == "__main__":
    unittest.main()
