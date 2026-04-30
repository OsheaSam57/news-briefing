from __future__ import annotations

from email.utils import parsedate_to_datetime

import feedparser
import requests

from news_briefing.sources import FEED_CATEGORIES


USER_AGENT = "news-briefing-bot/0.1 (+https://local.dev)"


def ingest_feeds(max_articles_per_feed: int) -> list[dict]:
    articles: list[dict] = []

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for domain, feeds in FEED_CATEGORIES.items():
        for feed in feeds:
            response = session.get(feed["url"], timeout=20)
            response.raise_for_status()
            parsed_feed = feedparser.parse(response.content)
            if not parsed_feed.entries:
                detail = getattr(parsed_feed, "bozo_exception", "no entries found")
                raise ValueError(f"{feed['name']} returned no RSS entries: {detail}")

            for entry in parsed_feed.entries[:max_articles_per_feed]:
                url = entry.get("link")
                title = entry.get("title", "").strip()
                if not url or not title:
                    continue

                articles.append(
                    {
                        "domain": domain,
                        "source": feed["name"],
                        "title": title,
                        "url": url.strip(),
                        "published": _normalize_published(entry),
                        "raw_summary": _extract_summary(entry),
                        "raw_content": _extract_content(entry),
                    }
                )

    return articles


def _normalize_published(entry: feedparser.FeedParserDict) -> str | None:
    published = entry.get("published") or entry.get("updated")
    if not published:
        return None

    try:
        return parsedate_to_datetime(published).isoformat()
    except (TypeError, ValueError, OverflowError):
        return str(published)


def _extract_summary(entry: feedparser.FeedParserDict) -> str:
    return (entry.get("summary") or entry.get("description") or "").strip()


def _extract_content(entry: feedparser.FeedParserDict) -> str:
    content = entry.get("content", [])
    if content and isinstance(content, list):
        first = content[0]
        if isinstance(first, dict):
            return str(first.get("value", "")).strip()
    return _extract_summary(entry)
