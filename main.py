from __future__ import annotations

import sys

from news_briefing.config import load_settings
from news_briefing.db import (
    fetch_articles_for_summary,
    fetch_digest_articles,
    fetch_unprocessed_articles,
    get_connection,
    initialize_database,
    upsert_articles,
)
from news_briefing.delivery import render_digest
from news_briefing.ingest import ingest_feeds
from news_briefing.scoring import score_articles
from news_briefing.summarise import summarise_articles


def main() -> int:
    settings = load_settings()
    if not settings.anthropic_api_key:
        print("Missing ANTHROPIC_API_KEY. Populate .env before running.")
        return 1

    connection = get_connection(settings.database_path)
    initialize_database(connection)

    try:
        print("Fetching RSS feeds...")
        articles = ingest_feeds(settings.max_articles_per_feed)
        stored_count = upsert_articles(connection, articles)
        print(f"Stored or refreshed {stored_count} articles.")

        print("Scoring newly ingested articles...")
        unprocessed = fetch_unprocessed_articles(connection)
        approved, rejected = score_articles(
            connection,
            unprocessed,
            settings.anthropic_api_key,
            settings.anthropic_model,
        )
        print(f"Approved {approved} articles and rejected {rejected}.")

        print("Summarising approved articles...")
        approved_articles = fetch_articles_for_summary(connection)
        summarised = summarise_articles(
            connection,
            approved_articles,
            settings.anthropic_api_key,
            settings.anthropic_model,
        )
        print(f"Summarised {summarised} articles.")

        print("Rendering HTML digest...")
        digest_articles = fetch_digest_articles(connection)
        render_digest(digest_articles, settings.output_path)
        print(f"Digest written to {settings.output_path}")
    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
