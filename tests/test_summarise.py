from __future__ import annotations

import unittest
from contextlib import redirect_stdout
from io import StringIO

from news_briefing.summarise import _normalise_optional_text, _normalise_summary


class SummaryNormalisationTests(unittest.TestCase):
    def test_uses_raw_summary_when_model_summary_is_none(self) -> None:
        article = {
            "id": 42,
            "title": "Fallback title",
            "raw_summary": "Fallback RSS summary.",
        }

        stdout = StringIO()
        with redirect_stdout(stdout):
            summary = _normalise_summary(None, article)

        self.assertEqual(summary, "Fallback RSS summary.")
        self.assertIn("Warning: summariser returned no summary", stdout.getvalue())

    def test_uses_title_when_model_and_raw_summaries_are_blank(self) -> None:
        article = {
            "id": 42,
            "title": "Fallback title",
            "raw_summary": "   ",
        }

        stdout = StringIO()
        with redirect_stdout(stdout):
            summary = _normalise_summary("", article)

        self.assertEqual(summary, "Fallback title")
        self.assertIn("Warning: summariser returned no summary", stdout.getvalue())

    def test_normalises_optional_text_without_assuming_string_input(self) -> None:
        self.assertIsNone(_normalise_optional_text(None))
        self.assertIsNone(_normalise_optional_text("   "))
        self.assertEqual(_normalise_optional_text(123), "123")


if __name__ == "__main__":
    unittest.main()
