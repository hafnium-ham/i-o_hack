from __future__ import annotations

import os
from pathlib import Path


_ENV_LOADED = False


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def candidate_env_files() -> list[Path]:
    cwd = Path.cwd()
    return [
        cwd / ".env.local",
        cwd / ".env",
        project_root() / ".env.local",
        project_root() / ".env",
        workspace_root() / ".env.local",
        workspace_root() / ".env",
    ]


def load_env_files(*, override: bool = False) -> list[Path]:
    global _ENV_LOADED
    if _ENV_LOADED and not override:
        return []

    loaded: list[Path] = []
    seen: set[Path] = set()
    for path in candidate_env_files():
        if path in seen or not path.exists():
            continue
        seen.add(path)
        loaded.append(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip()
            if not key or (key in os.environ and not override):
                continue

            os.environ[key] = value.strip().strip("\"'")

    _ENV_LOADED = True
    return loaded


def has_live_ai_credentials() -> bool:
    load_env_files()
    return bool(os.getenv("GOOGLE_API_KEY") and os.getenv("GMI_API_KEY"))


def has_gmi_credentials() -> bool:
    load_env_files()
    return bool(os.getenv("GMI_API_KEY"))
