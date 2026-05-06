from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from anthropic import Anthropic

from news_briefing.db import save_summary
from news_briefing.llm_json import extract_json_object


SYSTEM_PROMPT = """You are writing a daily intelligence briefing for a senior analyst and data scientist at a UK
automotive protection and GAP insurance company. They have strong experience in BI and data
analysis and are expanding into ML and data science. They deal with LLMs daily.

Write in a sharp, direct briefing style — like The Economist meets a sell-side research note.
No filler, no hedging, no AI disclaimers. Every sentence must add information.
Output valid JSON only."""


USER_PROMPT_TEMPLATE = """Summarise this article for a senior analyst at a UK automotive protection and GAP insurance company.

Return JSON with this schema:
{{
  "summary": string,
  "insurance_callout": string | null,
  "key_themes": [string]
}}

Rules for summary:
- Exactly 3 to 5 sentences.
- Lead with the single most important fact or development.
- Include any concrete numbers, percentages, or named institutions mentioned in the article.
- End with the most relevant forward-looking implication.
- Never use phrases like "this article discusses" or "the author explores".

{insurance_callout_instruction}

Rules for key_themes:
- Up to 3 short tags such as "claims inflation", "FCA regulation", "motor finance", "gradient boosting"

Assigned domain: {domain}
Source: {source}
Title: {title}
Relevance score: {score}
Key themes from scoring: {key_themes}
Raw summary: {raw_summary}
Content excerpt: {content}"""


INSURANCE_CALLOUT_INSTRUCTIONS = {
    "Economics/Markets": '''Rules for insurance_callout — this field is REQUIRED for this domain:
- Explain specifically how this development affects automotive protection or GAP insurance profitability.
- Consider these pressure vectors explicitly: claims frequency and severity, vehicle values and negative
  equity rates, motor finance volumes which drive GAP attach rates, consumer ability to pay premiums,
  investment return on float, reinsurance cost.
- Be concrete — name the mechanism, not just "this could affect insurers".
- 3 to 5 sentences. No generic statements.
- Bad example: "This may impact the insurance industry."
- Good example: "A sustained rise in used car values reduces negative equity exposure, directly
  compressing GAP claims frequency. However, higher vehicle prices increase average claim severity
  on motor policies. Dealers may accelerate GAP product promotion as customer affordability risk falls."''',
    "Insurance/Actuarial": """Rules for insurance_callout — this field is REQUIRED for this domain:
- Focus specifically on the automotive protection and GAP insurance angle.
- If the article covers broader P&C or life insurance, extract only what applies to motor or automotive.
- Cover regulatory, pricing, reserving, or competitive implications where relevant to the business.
- 2 to 4 sentences. Be direct about the business implication.
- If the article has no conceivable automotive protection angle, set to null.""",
    "default": """Rules for insurance_callout:
- Set to null unless the article has a direct and non-obvious connection to automotive protection,
  GAP insurance, or motor insurance profitability.
- Do not force a connection — null is the correct answer for most AI/ML and Data Science articles
  unless the technique is directly applicable to insurance pricing, fraud detection, or churn modelling.""",
}


def summarise_articles(
    connection: sqlite3.Connection,
    articles: list[sqlite3.Row] | list[dict[str, Any]],
    api_key: str,
    model: str,
) -> int:
    client = Anthropic(api_key=api_key)
    summarised = 0

    for article in articles:
        result = _summarise_article(client, model, article)
        summary = _normalise_summary(result.get("summary"), article)
        insurance_callout = _normalise_optional_text(result.get("insurance_callout"))
        save_summary(
            connection,
            article["id"],
            summary,
            insurance_callout,
        )
        summarised += 1

    return summarised


def _summarise_article(
    client: Anthropic,
    model: str,
    article: sqlite3.Row | Mapping[str, Any],
) -> dict:
    domain = article["domain"]
    prompt = USER_PROMPT_TEMPLATE.format(
        domain=domain,
        source=article["source"],
        title=article["title"],
        score=article["score"],
        key_themes=_get_optional(article, "key_themes") or "None",
        raw_summary=article["raw_summary"] or "None",
        content=article["raw_content"][:6000] if article["raw_content"] else "None",
        insurance_callout_instruction=INSURANCE_CALLOUT_INSTRUCTIONS.get(
            domain,
            INSURANCE_CALLOUT_INSTRUCTIONS["default"],
        ),
    )

    response = client.messages.create(
        model=model,
        max_tokens=700,
        temperature=0.2,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    payload = _extract_text(response)
    return extract_json_object(payload)


def _get_optional(article: sqlite3.Row | Mapping[str, Any], key: str) -> Any:
    if isinstance(article, sqlite3.Row):
        return article[key] if key in article.keys() else None
    return article.get(key)


def _normalise_summary(value: Any, article: sqlite3.Row | Mapping[str, Any]) -> str:
    summary = _normalise_optional_text(value)
    if summary:
        return summary

    article_id = _get_optional(article, "id")
    title = _get_optional(article, "title") or "Untitled article"
    print(f"Warning: summariser returned no summary for article {article_id}: {title}")

    fallback = _normalise_optional_text(_get_optional(article, "raw_summary"))
    if fallback:
        return fallback
    return str(title).strip()


def _normalise_optional_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _extract_text(response) -> str:
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()
