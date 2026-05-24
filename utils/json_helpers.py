from __future__ import annotations

import json
import re
from typing import Any


def parse_json_object(raw: str) -> Any:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Gemini sometimes returns object contents without outer braces
        try:
            return json.loads("{" + text + "}")
        except json.JSONDecodeError:
            pass
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char not in "[{":
                continue
            try:
                parsed, _ = decoder.raw_decode(text[index:])
                return parsed
            except json.JSONDecodeError:
                continue
        raise
