from __future__ import annotations

import sqlite3
from typing import Any

from anthropic import Anthropic

from news_briefing.db import save_score
from news_briefing.llm_json import extract_json_object


SYSTEM_PROMPT = """You are an expert editorial filter for a senior analyst and data scientist at a UK automotive
protection and GAP insurance company. You have deep knowledge of the insurance industry,
financial markets, AI/ML, and data science.

Your job is to score articles by how genuinely useful they are to someone in this role.
Output valid JSON only."""


USER_PROMPT_TEMPLATE = """Score this article for relevance to a senior analyst and data scientist at a UK automotive
protection and GAP insurance company. They want to stay sharp across four areas:

HIGH VALUE signals:
- UK/EU insurance regulation changes (FCA, PRA, Consumer Duty, add-on product rules)
- Motor finance, GAP insurance, and mechanical breakdown protection market developments
- Used car market dynamics: pricing, volumes, negative equity trends
- Claims inflation drivers: vehicle repair costs, parts shortages, EV complexity
- Interest rate and BoE decisions affecting motor finance demand and investment returns
- Reinsurance market conditions and capacity changes
- AI/ML techniques applicable to insurance: pricing models, fraud detection, churn, reserving
- Practical data science methods: survival analysis, gradient boosting, time series, causal inference
- LLM and agentic AI developments with enterprise or insurance applications
- Macroeconomic indicators: inflation, consumer confidence, employment, vehicle sales volumes

Return JSON only — no preamble, no markdown:
{{
  "score": <integer 1 to 10>,
  "reason": <one sentence explaining the score>,
  "key_themes": [<up to 3 short theme tags, e.g. "claims inflation", "FCA regulation", "motor finance">]
}}

Source: {source}
Domain: {domain}
Title: {title}
Summary: {summary}
Content excerpt: {content}"""


def score_articles(
    connection: sqlite3.Connection,
    articles: list[sqlite3.Row],
    api_key: str,
    model: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    client = Anthropic(api_key=api_key)
    approved: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for article in articles:
        result = _score_article(client, model, article)
        score = int(result["score"])
        reason = str(result["reason"]).strip()
        key_themes = _normalise_key_themes(result.get("key_themes", []))
        key_themes_text = ", ".join(key_themes)
        status = "approved" if score >= 7 else "rejected"

        save_score(connection, article["id"], score, reason, key_themes_text, status)

        scored_article = dict(article)
        scored_article.update(
            {
                "score": score,
                "reason": reason,
                "key_themes": key_themes_text,
                "status": status,
            }
        )
        if status == "approved":
            approved.append(scored_article)
        else:
            rejected.append(scored_article)

    print(
        f"Scored {len(articles)} articles: {len(approved)} passed the threshold, "
        f"{len(rejected)} rejected."
    )
    return approved, rejected


def _score_article(client: Anthropic, model: str, article: sqlite3.Row) -> dict:
    prompt = USER_PROMPT_TEMPLATE.format(
        source=article["source"],
        domain=article["domain"],
        title=article["title"],
        summary=article["raw_summary"] or "None",
        content=article["raw_content"][:3000] if article["raw_content"] else "None",
    )

    response = client.messages.create(
        model=model,
        max_tokens=300,
        temperature=0.1,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    payload = _extract_text(response)
    return extract_json_object(payload)


def _normalise_key_themes(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    themes: list[str] = []
    for theme in value[:3]:
        text = str(theme).strip()
        if text:
            themes.append(text)
    return themes


def _extract_text(response) -> str:
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()
