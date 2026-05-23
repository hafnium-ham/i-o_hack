from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx


TRUE_VALUES = {"1", "true", "yes", "on"}
ENV_PREFIXES = ("APISPORTS_", "API_SPORTS_", "VITE_APISPORTS_")
DEFAULT_BASE_URLS = {
    "football": "https://v3.football.api-sports.io",
}

_ENV_LOADED = False
_REQUEST_CACHE: dict[tuple[str, str, tuple[tuple[str, str], ...]], dict[str, Any]] = {}


class ApiSportsError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        stage: str = "request",
        endpoint: str | None = None,
        params: dict[str, Any] | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(_redact_secret(message))
        self.stage = stage
        self.endpoint = endpoint
        self.params = _clean_params(params)
        self.http_status = http_status

    def to_error(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "stage": self.stage,
            "message": _redact_secret(str(self)),
        }
        if self.endpoint:
            error["endpoint"] = self.endpoint
        if self.params:
            error["params"] = self.params
        if self.http_status is not None:
            error["http_status"] = self.http_status
        return error


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _candidate_env_files() -> list[Path]:
    cwd = Path.cwd()
    return [
        cwd / ".env.local",
        cwd / ".env",
        _project_root() / ".env.local",
        _project_root() / ".env",
        _workspace_root() / ".env.local",
        _workspace_root() / ".env",
    ]


def load_api_sports_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    seen: set[Path] = set()
    for path in _candidate_env_files():
        if path in seen or not path.exists():
            continue
        seen.add(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip()
            if not key.startswith(ENV_PREFIXES) or key in os.environ:
                continue

            value = value.strip().strip("\"'")
            os.environ[key] = value

    _ENV_LOADED = True


def get_api_key() -> str | None:
    load_api_sports_env()
    return (
        os.getenv("APISPORTS_KEY")
        or os.getenv("API_SPORTS_KEY")
        or os.getenv("VITE_APISPORTS_KEY")
    )


def is_live_lookup_enabled() -> bool:
    load_api_sports_env()
    return os.getenv("APISPORTS_LIVE_LOOKUP", "false").lower() in TRUE_VALUES


def clear_api_sports_cache() -> None:
    _REQUEST_CACHE.clear()


def redact_api_sports_secret(message: str) -> str:
    return _redact_secret(message)


def _base_url_for_sport(sport: str) -> str:
    load_api_sports_env()
    env_name = f"APISPORTS_{sport.upper().replace('-', '_')}_BASE_URL"
    base_url = os.getenv(env_name) or DEFAULT_BASE_URLS.get(sport)
    if not base_url:
        raise ApiSportsError(
            f"No API-SPORTS base URL configured for sport '{sport}'. "
            f"Set {env_name} before making live requests.",
            stage="config",
        )
    return base_url.rstrip("/")


def _timeout_seconds() -> float:
    load_api_sports_env()
    raw = os.getenv("APISPORTS_REQUEST_TIMEOUT_SECONDS", "8")
    try:
        return float(raw)
    except ValueError:
        return 8.0


def _cache_key(
    sport: str,
    endpoint: str,
    params: dict[str, Any] | None,
) -> tuple[str, str, tuple[tuple[str, str], ...]]:
    normalized_params = tuple(
        sorted((str(key), str(value)) for key, value in (params or {}).items() if value not in (None, ""))
    )
    return (sport, endpoint, normalized_params)


def _redact_secret(message: str) -> str:
    api_key = get_api_key()
    return message.replace(api_key, "[redacted]") if api_key else message


def _clean_params(params: dict[str, Any] | None) -> dict[str, Any]:
    return {key: value for key, value in (params or {}).items() if value not in (None, "")}


def _empty_payload() -> dict[str, Any]:
    return {
        "get": "",
        "parameters": {},
        "errors": [],
        "results": 0,
        "paging": {"current": 1, "total": 1},
        "response": [],
    }


def _api_errors(payload: dict[str, Any]) -> list[str]:
    errors = payload.get("errors")
    if not errors:
        return []
    if isinstance(errors, list):
        return [str(error) for error in errors if str(error)]
    if isinstance(errors, dict):
        return [f"{key}: {value}" for key, value in errors.items() if str(value)]
    return [str(errors)]


def _format_api_errors(errors: list[str]) -> str:
    return "; ".join(_redact_secret(error) for error in errors) or "Unknown API-SPORTS error."


def api_sports_get(
    endpoint: str,
    params: dict[str, Any] | None = None,
    *,
    sport: str | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    load_api_sports_env()
    sport = sport or os.getenv("APISPORTS_DEFAULT_SPORT", "football")
    endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    clean_params = _clean_params(params)
    cache_key = _cache_key(sport, endpoint, params)

    if use_cache and cache_key in _REQUEST_CACHE:
        return _REQUEST_CACHE[cache_key]

    api_key = get_api_key()
    if not api_key:
        raise ApiSportsError(
            "APISPORTS_KEY is not configured.",
            stage="auth",
            endpoint=endpoint,
            params=clean_params,
        )

    try:
        url = f"{_base_url_for_sport(sport)}{endpoint}"
    except ApiSportsError as exc:
        exc.endpoint = endpoint
        exc.params = clean_params
        raise

    try:
        with httpx.Client(timeout=_timeout_seconds()) as client:
            response = client.get(url, params=clean_params, headers={"x-apisports-key": api_key})
            response.raise_for_status()
            payload = _empty_payload() if response.status_code == 204 else response.json()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        raise ApiSportsError(
            f"API-SPORTS HTTP request failed with status {status_code}.",
            stage="http",
            endpoint=endpoint,
            params=clean_params,
            http_status=status_code,
        ) from exc
    except httpx.TimeoutException as exc:
        raise ApiSportsError(
            "API-SPORTS request timed out.",
            stage="timeout",
            endpoint=endpoint,
            params=clean_params,
        ) from exc
    except httpx.HTTPError as exc:
        raise ApiSportsError(
            f"API-SPORTS request failed: {_redact_secret(str(exc))}",
            stage="network",
            endpoint=endpoint,
            params=clean_params,
        ) from exc
    except ValueError as exc:
        raise ApiSportsError(
            "API-SPORTS returned invalid JSON.",
            stage="decode",
            endpoint=endpoint,
            params=clean_params,
        ) from exc

    if not isinstance(payload, dict):
        raise ApiSportsError(
            "API-SPORTS returned non-object JSON payload.",
            stage="decode",
            endpoint=endpoint,
            params=clean_params,
        )

    errors = _api_errors(payload)
    if errors:
        raise ApiSportsError(
            f"API-SPORTS payload errors: {_format_api_errors(errors)}",
            stage="api",
            endpoint=endpoint,
            params=clean_params,
        )

    result = {
        "endpoint": endpoint,
        "params": clean_params,
        "payload": payload,
    }
    if use_cache:
        _REQUEST_CACHE[cache_key] = result
    return result


def _profile_player(profile_item: dict[str, Any]) -> dict[str, Any]:
    player = profile_item.get("player")
    return player if isinstance(player, dict) else profile_item


def _normalized_names(player_card: dict[str, Any]) -> set[str]:
    names = [player_card.get("name", ""), *player_card.get("aliases", [])]
    return {str(name).casefold() for name in names if str(name).strip()}


def _select_best_profile(
    response: list[Any],
    player_card: dict[str, Any],
) -> dict[str, Any] | None:
    profiles = [item for item in response if isinstance(item, dict)]
    if not profiles:
        return None

    known_names = _normalized_names(player_card)
    for item in profiles:
        player = _profile_player(item)
        candidate_names = {
            str(player.get("name", "")).casefold(),
            str(player.get("firstname", "")).casefold(),
            str(player.get("lastname", "")).casefold(),
        }
        if known_names & {name for name in candidate_names if name}:
            return item

    return profiles[0]


def _response_items(result: dict[str, Any]) -> list[Any]:
    payload = result.get("payload", {})
    response = payload.get("response", []) if isinstance(payload, dict) else []
    return response if isinstance(response, list) else []


def _extract_player_id(profile_item: dict[str, Any] | None) -> int | None:
    if not profile_item:
        return None
    player = _profile_player(profile_item)
    value = player.get("id") or player.get("player")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _search_terms(player_card: dict[str, Any]) -> list[str]:
    terms = [player_card.get("name", ""), *player_card.get("aliases", [])]
    return [str(term).strip() for term in terms if len(str(term).strip()) >= 3]


def fetch_player_intelligence(player_card: dict[str, Any], *, sport: str = "football") -> dict[str, Any]:
    existing_id = player_card.get("api_sports_player_id") or player_card.get("api_sports_id")
    bundle: dict[str, Any] = {
        "source": "api-sports",
        "sport": sport,
        "status": "ok",
        "errors": [],
    }

    try:
        if existing_id:
            profile = api_sports_get("/players/profiles", {"player": existing_id}, sport=sport)
            profile_response = _response_items(profile)
            selected_profile = profile_response[0] if profile_response else None
            bundle["profile"] = profile
        else:
            selected_profile = None
            for term in _search_terms(player_card):
                profile = api_sports_get("/players/profiles", {"search": term}, sport=sport)
                selected_profile = _select_best_profile(_response_items(profile), player_card)
                bundle["profile"] = profile
                if selected_profile:
                    break
    except ApiSportsError as exc:
        bundle["status"] = "error"
        bundle["errors"].append(exc.to_error())
        return bundle

    player_id = _extract_player_id(selected_profile)
    if not player_id:
        profile_params = bundle.get("profile", {}).get("params", {})
        bundle["status"] = "not_found"
        bundle["errors"].append(
            {
                "stage": "profile",
                "message": "No API-SPORTS player id found for this player.",
                "endpoint": "/players/profiles",
                "params": profile_params,
            }
        )
        return bundle

    bundle["player_id"] = player_id

    try:
        bundle["teams"] = api_sports_get("/players/teams", {"player": player_id}, sport=sport)
    except ApiSportsError as exc:
        bundle["status"] = "partial"
        bundle["errors"].append(exc.to_error())

    season = os.getenv("APISPORTS_FOOTBALL_SEASON")
    if season:
        try:
            season_params: dict[str, Any] = {
                "id": player_id,
                "season": season,
                "league": os.getenv("APISPORTS_FOOTBALL_LEAGUE"),
                "team": os.getenv("APISPORTS_FOOTBALL_TEAM"),
            }
            bundle["season_stats"] = api_sports_get("/players", season_params, sport=sport)
        except ApiSportsError as exc:
            bundle["status"] = "partial"
            bundle["errors"].append(exc.to_error())

    return bundle


def enrich_player_card(player_card: dict[str, Any], *, sport: str = "football") -> dict[str, Any]:
    enriched = dict(player_card)
    try:
        enriched["api_sports"] = fetch_player_intelligence(player_card, sport=sport)
    except Exception as exc:
        enriched["api_sports"] = {
            "source": "api-sports",
            "sport": sport,
            "status": "error",
            "errors": [
                {
                    "stage": "unexpected",
                    "message": _redact_secret(str(exc)),
                }
            ],
        }
    return enriched
