from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any


def extract_json_object(payload: str) -> dict[str, Any]:
    cleaned = _strip_code_fence(payload.strip())
    if not cleaned:
        raise ValueError("Model returned an empty response instead of JSON.")

    try:
        parsed = json.loads(cleaned)
    except JSONDecodeError:
        parsed = _load_embedded_json(cleaned)

    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a JSON object, got {type(parsed).__name__}.")
    return parsed


def _strip_code_fence(payload: str) -> str:
    if not payload.startswith("```"):
        return payload

    lines = payload.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return payload


def _load_embedded_json(payload: str) -> Any:
    decoder = json.JSONDecoder()
    start = payload.find("{")
    while start != -1:
        try:
            parsed, _ = decoder.raw_decode(payload[start:])
            return parsed
        except JSONDecodeError:
            start = payload.find("{", start + 1)

    preview = payload[:300].replace("\n", "\\n")
    raise ValueError(f"Could not parse model response as JSON. Response preview: {preview}")
