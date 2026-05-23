from __future__ import annotations

import os
from typing import Any


DEFAULT_GMI_BASE_URL = "https://api.gmi-serving.com/v1"


def get_gmi_default_headers() -> dict[str, str]:
    organization_id = os.getenv("GMI_ORGANIZATION_ID")
    return {"X-Organization-ID": organization_id} if organization_id else {}


def get_gmi_client() -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the 'openai' package to use GMI Cloud inference.") from exc

    api_key = os.getenv("GMI_API_KEY")
    if not api_key:
        raise RuntimeError("GMI_API_KEY is required for GMI Cloud inference.")

    kwargs: dict[str, Any] = {
        "base_url": os.getenv("GMI_BASE_URL", DEFAULT_GMI_BASE_URL),
        "api_key": api_key,
    }
    default_headers = get_gmi_default_headers()
    if default_headers:
        kwargs["default_headers"] = default_headers

    return OpenAI(**kwargs)


def list_available_models() -> list[str]:
    client = get_gmi_client()
    return [model.id for model in client.models.list().data]


def check_gmi_connection() -> dict[str, Any]:
    models = list_available_models()
    return {
        "base_url": os.getenv("GMI_BASE_URL", DEFAULT_GMI_BASE_URL),
        "model_count": len(models),
        "models": models,
    }
