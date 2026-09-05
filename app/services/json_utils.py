"""Tolerant JSON parsing for LLM completions.

Even with `response_format={"type": "json_object"}`, models occasionally wrap
the object in a ```json fence or add a stray sentence before/after it. Every
strict-JSON completion should be parsed through this rather than
`json.loads` directly.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = _FENCE_RE.sub("", text.strip()).strip()
    try:
        return json.loads(cleaned)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        match = _OBJECT_RE.search(cleaned)
        if not match:
            raise
        return json.loads(match.group(0))  # type: ignore[no-any-return]
