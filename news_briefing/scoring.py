from __future__ import annotations

import sqlite3

from anthropic import Anthropic

from news_briefing.db import mark_article_scored
from news_briefing.llm_json import extract_json_object


def score_articles(
    connection: sqlite3.Connection,
    articles: list[sqlite3.Row],
    api_key: str,
    model: str,
) -> tuple[int, int]:
    client = Anthropic(api_key=api_key)
    approved = 0
    rejected = 0

    for article in articles:
        result = _score_article(client, model, article)
        score = int(result["score"])
        rationale = result["rationale"].strip()
        status = "approved" if score >= 6 else "rejected"

        mark_article_scored(connection, article["id"], score, rationale, status)

        if status == "approved":
            approved += 1
        else:
            rejected += 1

    return approved, rejected


def _score_article(client: Anthropic, model: str, article: sqlite3.Row) -> dict:
    prompt = f"""
You are scoring articles for a personal news briefing.

Return only JSON with this schema:
{{
  "score": integer,
  "rationale": string
}}

Scoring rules:
- Score from 1 to 10.
- Prioritize relevance to the article's assigned domain.
- Prefer articles that are substantive, timely, and useful to a technical or business reader.
- Penalize low-information posts, pure clickbait, or off-topic items.

Assigned domain: {article["domain"]}
Source: {article["source"]}
Title: {article["title"]}
URL: {article["url"]}
Published: {article["published"] or "Unknown"}
Summary: {article["raw_summary"] or "None"}
Content excerpt: {article["raw_content"][:4000] if article["raw_content"] else "None"}
""".strip()

    response = client.messages.create(
        model=model,
        max_tokens=300,
        temperature=0,
        system="You are a precise JSON API. Output valid JSON only.",
        messages=[{"role": "user", "content": prompt}],
    )
    payload = _extract_text(response)
    return extract_json_object(payload)


def _extract_text(response) -> str:
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()
