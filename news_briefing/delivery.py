from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from news_briefing.config import TEMPLATE_DIR
from news_briefing.sources import FEED_CATEGORIES


def render_digest(articles: list[sqlite3.Row], output_path: Path) -> None:
    dataframe = pd.DataFrame([dict(article) for article in articles])
    grouped_articles: dict[str, list[dict]] = {}
    if not dataframe.empty:
        dataframe = dataframe.sort_values(
            by=["domain", "score", "created_at"],
            ascending=[True, False, True],
        )
        grouped_articles = {
            domain: frame.to_dict(orient="records")
            for domain, frame in dataframe.groupby("domain", sort=False)
        }

    sections = [
        {
            "name": domain,
            "articles": grouped_articles.get(domain, []),
        }
        for domain in FEED_CATEGORIES
    ]

    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = environment.get_template("digest.html.j2")

    html = template.render(sections=sections)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
