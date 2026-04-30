from __future__ import annotations

import sqlite3

from anthropic import Anthropic

from news_briefing.db import save_summary
from news_briefing.llm_json import extract_json_object


def summarise_articles(
    connection: sqlite3.Connection,
    articles: list[sqlite3.Row],
    api_key: str,
    model: str,
) -> int:
    client = Anthropic(api_key=api_key)
    summarised = 0

    for article in articles:
        result = _summarise_article(client, model, article)
        save_summary(
            connection,
            article["id"],
            result["summary"].strip(),
            (result.get("insurance_callout") or "").strip() or None,
        )
        summarised += 1

    return summarised


def _summarise_article(client: Anthropic, model: str, article: sqlite3.Row) -> dict:
    extra_instruction = ""
    if article["domain"] == "Economics/Markets":
        extra_instruction = """
- Also provide an `insurance_callout` field as a second paragraph explaining why this matters for automotive protection products and GAP insurance.
- The insurance callout should be explicit and concrete, not generic.
""".strip()

    prompt = f"""
Create a concise article summary for a daily digest.

Return only JSON with this schema:
{{
  "summary": string,
  "insurance_callout": string | null
}}

Rules:
- The summary must be 3 to 5 sentences.
- Write in a direct briefing style.
- Do not mention that you are an AI.
- If the article is not in Economics/Markets, set `insurance_callout` to null.
{extra_instruction}

Assigned domain: {article["domain"]}
Source: {article["source"]}
Title: {article["title"]}
URL: {article["url"]}
Relevance score: {article["score"]}
Summary: {article["raw_summary"] or "None"}
Content excerpt: {article["raw_content"][:5000] if article["raw_content"] else "None"}
""".strip()

    response = client.messages.create(
        model=model,
        max_tokens=600,
        temperature=0.2,
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
