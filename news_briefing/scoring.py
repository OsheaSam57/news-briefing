from __future__ import annotations

import sqlite3
from typing import Any

from anthropic import Anthropic

from news_briefing.db import save_score
from news_briefing.llm_json import extract_json_object


ARTICLES_PER_SOURCE = 3


SYSTEM_PROMPT = """You are an expert editorial ranker for a senior analyst and data scientist at a UK automotive
protection and GAP insurance company. You have deep knowledge of the insurance industry,
financial markets, AI/ML, and data science.

Your job is to rank articles by how genuinely useful they are to someone in this role.
Do not be overly strict: even moderately relevant market, insurance, AI, or data science news
can be useful when it is one of the stronger items from its source on a given day.
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

Scoring guidance:
- Score from 1 to 10 to rank relative usefulness, not to decide whether the article is included.
- Reserve 9 to 10 for direct, high-impact relevance to automotive protection, GAP insurance,
  motor finance, motor insurance profitability, or practical insurance/data science work.
- Use 6 to 8 for useful adjacent news that keeps the reader commercially or technically sharp.
- Use 3 to 5 for general domain news with limited direct relevance but some situational value.
- Use 1 to 2 only for spam, duplicate, pure promotion, or clearly off-topic items.
- On a quiet news day, a score of 5 or 6 can still be worth reading if it is among the best
  items available from that source.

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
    scored_articles: list[dict[str, Any]] = []

    for article in articles:
        result = _score_article(client, model, article)
        score = int(result["score"])
        reason = str(result["reason"]).strip()
        key_themes = _normalise_key_themes(result.get("key_themes", []))
        key_themes_text = ", ".join(key_themes)
        scored_article = dict(article)
        scored_article.update(
            {
                "score": score,
                "reason": reason,
                "key_themes": key_themes_text,
            }
        )
        scored_articles.append(scored_article)

    approved, rejected = _select_articles_for_digest(scored_articles)

    for article in approved:
        article["status"] = "approved"
        save_score(
            connection,
            article["id"],
            article["score"],
            article["reason"],
            article["key_themes"],
            article["status"],
        )

    for article in rejected:
        article["status"] = "rejected"
        save_score(
            connection,
            article["id"],
            article["score"],
            article["reason"],
            article["key_themes"],
            article["status"],
        )

    print(
        f"Scored {len(articles)} articles: selected {len(approved)} for the digest "
        f"as the top {ARTICLES_PER_SOURCE} per source, rejected {len(rejected)}."
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


def _select_articles_for_digest(
    articles: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped_articles: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for article in articles:
        grouped_articles.setdefault((article["domain"], article["source"]), []).append(article)

    approved_ids: set[int] = set()
    for group in grouped_articles.values():
        ranked_group = sorted(
            group,
            key=lambda article: (
                int(article["score"]),
                str(article["published"] or ""),
                int(article["id"]),
            ),
            reverse=True,
        )
        approved_ids.update(article["id"] for article in ranked_group[:ARTICLES_PER_SOURCE])

    approved = [article for article in articles if article["id"] in approved_ids]
    rejected = [article for article in articles if article["id"] not in approved_ids]
    return approved, rejected


def _extract_text(response) -> str:
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()
