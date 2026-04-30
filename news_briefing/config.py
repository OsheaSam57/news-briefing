from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"
TEMPLATE_DIR = ROOT_DIR / "templates"


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    anthropic_model: str
    database_path: Path
    output_path: Path
    max_articles_per_feed: int


def load_settings() -> Settings:
    load_dotenv()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
        database_path=Path(os.getenv("DATABASE_PATH", DATA_DIR / "news_briefing.db")),
        output_path=Path(os.getenv("DIGEST_OUTPUT_PATH", OUTPUT_DIR / "digest.html")),
        max_articles_per_feed=int(os.getenv("MAX_ARTICLES_PER_FEED", "10")),
    )
