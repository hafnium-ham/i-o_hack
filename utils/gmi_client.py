from __future__ import annotations

import os
from typing import Any


DEFAULT_GMI_BASE_URL = "https://api.gmi-serving.com/v1"


def get_gmi_client() -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the 'openai' package to use GMI Cloud inference.") from exc

    api_key = os.getenv("GMI_API_KEY")
    if not api_key:
        raise RuntimeError("GMI_API_KEY is required for GMI Cloud inference.")

    return OpenAI(
        base_url=os.getenv("GMI_BASE_URL", DEFAULT_GMI_BASE_URL),
        api_key=api_key,
    )


def list_available_models() -> list[str]:
    client = get_gmi_client()
    return [model.id for model in client.models.list().data]

