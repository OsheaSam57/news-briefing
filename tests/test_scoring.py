from __future__ import annotations

import unittest

from news_briefing.scoring import _select_articles_for_digest


class SelectArticlesForDigestTests(unittest.TestCase):
    def test_selects_top_three_articles_per_source_without_score_threshold(self) -> None:
        articles = [
            {
                "id": 1,
                "domain": "Economics/Markets",
                "source": "Example Feed",
                "score": 2,
                "published": "2026-05-01",
            },
            {
                "id": 2,
                "domain": "Economics/Markets",
                "source": "Example Feed",
                "score": 5,
                "published": "2026-05-02",
            },
            {
                "id": 3,
                "domain": "Economics/Markets",
                "source": "Example Feed",
                "score": 4,
                "published": "2026-05-03",
            },
            {
                "id": 4,
                "domain": "Economics/Markets",
                "source": "Example Feed",
                "score": 3,
                "published": "2026-05-04",
            },
        ]

        approved, rejected = _select_articles_for_digest(articles)

        self.assertEqual({article["id"] for article in approved}, {2, 3, 4})
        self.assertEqual({article["id"] for article in rejected}, {1})


if __name__ == "__main__":
    unittest.main()
