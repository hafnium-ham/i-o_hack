from __future__ import annotations

import json
import re
from typing import Any


def parse_json_object(raw: str) -> Any:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)

