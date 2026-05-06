from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


def get_connection(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            published TEXT,
            raw_summary TEXT,
            raw_content TEXT,
            score INTEGER,
            reason TEXT,
            rationale TEXT,
            key_themes TEXT,
            summary TEXT,
            insurance_callout TEXT,
            status TEXT NOT NULL DEFAULT 'ingested',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _ensure_column(connection, "articles", "reason", "TEXT")
    _ensure_column(connection, "articles", "key_themes", "TEXT")
    connection.commit()


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_type: str,
) -> None:
    cursor = connection.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def upsert_articles(connection: sqlite3.Connection, articles: Iterable[dict]) -> int:
    inserted = 0
    for article in articles:
        cursor = connection.execute(
            """
            INSERT INTO articles (
                domain, source, title, url, published, raw_summary, raw_content
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                domain = excluded.domain,
                source = excluded.source,
                title = excluded.title,
                published = excluded.published,
                raw_summary = excluded.raw_summary,
                raw_content = excluded.raw_content,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                article["domain"],
                article["source"],
                article["title"],
                article["url"],
                article.get("published"),
                article.get("raw_summary"),
                article.get("raw_content"),
            ),
        )
        if cursor.rowcount:
            inserted += 1
    connection.commit()
    return inserted


def fetch_unprocessed_articles(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    cursor = connection.execute(
        """
        SELECT *
        FROM articles
        WHERE status = 'ingested'
        ORDER BY created_at ASC, id ASC
        """
    )
    return cursor.fetchall()


def save_score(
    connection: sqlite3.Connection,
    article_id: int,
    score: int,
    reason: str,
    key_themes: str,
    status: str,
) -> None:
    connection.execute(
        """
        UPDATE articles
        SET score = ?,
            reason = ?,
            rationale = ?,
            key_themes = ?,
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (score, reason, reason, key_themes, status, article_id),
    )
    connection.commit()


def mark_article_scored(
    connection: sqlite3.Connection,
    article_id: int,
    score: int,
    rationale: str,
    status: str,
) -> None:
    save_score(connection, article_id, score, rationale, "", status)


def fetch_articles_for_summary(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    cursor = connection.execute(
        """
        SELECT *
        FROM articles
        WHERE status = 'approved'
        ORDER BY score DESC, created_at ASC
        """
    )
    return cursor.fetchall()


def save_summary(
    connection: sqlite3.Connection,
    article_id: int,
    summary: str,
    insurance_callout: str | None,
) -> None:
    connection.execute(
        """
        UPDATE articles
        SET summary = ?, insurance_callout = ?, status = 'summarised', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (summary, insurance_callout, article_id),
    )
    connection.commit()


def fetch_digest_articles(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    cursor = connection.execute(
        """
        SELECT *
        FROM articles
        WHERE status = 'summarised'
        ORDER BY domain ASC, score DESC, created_at ASC
        """
    )
    return cursor.fetchall()
