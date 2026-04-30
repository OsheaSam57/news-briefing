from __future__ import annotations

import unittest

from news_briefing.llm_json import extract_json_object


class ExtractJsonObjectTests(unittest.TestCase):
    def test_parses_raw_json_object(self) -> None:
        self.assertEqual(extract_json_object('{"score": 7, "rationale": "Useful"}')["score"], 7)

    def test_parses_fenced_json_object(self) -> None:
        payload = """```json
{"score": 8, "rationale": "Timely"}
```"""

        self.assertEqual(extract_json_object(payload)["rationale"], "Timely")

    def test_parses_embedded_json_object(self) -> None:
        payload = 'Here is the JSON:\n{"summary": "Brief.", "insurance_callout": null}'

        self.assertEqual(extract_json_object(payload)["summary"], "Brief.")

    def test_rejects_empty_response(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty response"):
            extract_json_object("")

    def test_rejects_non_object_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "Expected a JSON object"):
            extract_json_object("[1, 2, 3]")


if __name__ == "__main__":
    unittest.main()
