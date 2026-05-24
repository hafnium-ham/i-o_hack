from __future__ import annotations

from typing import Any

import httpx
import pytest

from utils import api_sports_client as api_sports


def _response(status_code: int = 200, payload: Any = None, content: bytes | None = None) -> httpx.Response:
    request = httpx.Request("GET", "https://example.test/players")
    if content is not None:
        return httpx.Response(status_code=status_code, content=content, request=request)
    if status_code == 204:
        return httpx.Response(status_code=status_code, request=request)
    return httpx.Response(status_code=status_code, json=payload or {"errors": [], "response": []}, request=request)


class FakeClientFactory:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []
        self.timeouts: list[float] = []

    def __call__(self, timeout: float) -> "FakeClient":
        self.timeouts.append(timeout)
        return FakeClient(self)


class FakeClient:
    def __init__(self, factory: FakeClientFactory) -> None:
        self.factory = factory

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def get(self, url: str, params: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
        self.factory.calls.append({"url": url, "params": params, "headers": headers})
        next_response = self.factory.responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return next_response


@pytest.fixture(autouse=True)
def reset_api_sports(monkeypatch: pytest.MonkeyPatch) -> None:
    api_sports.clear_api_sports_cache()
    monkeypatch.setattr(api_sports, "_ENV_LOADED", False)
    monkeypatch.setattr(api_sports, "_candidate_env_files", lambda: [])
    for key in [
        "APISPORTS_KEY",
        "API_SPORTS_KEY",
        "VITE_APISPORTS_KEY",
        "APISPORTS_DEFAULT_SPORT",
        "APISPORTS_BASKETBALL_BASE_URL",
        "APISPORTS_FOOTBALL_LEAGUE",
        "APISPORTS_FOOTBALL_TEAM",
        "APISPORTS_FOOTBALL_SEASON",
        "APISPORTS_REQUEST_TIMEOUT_SECONDS",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("APISPORTS_FOOTBALL_BASE_URL", "https://example.test")


def _install_client(monkeypatch: pytest.MonkeyPatch, responses: list[Any]) -> FakeClientFactory:
    factory = FakeClientFactory(responses)
    monkeypatch.setattr(api_sports.httpx, "Client", factory)
    return factory


def test_api_sports_get_requires_key() -> None:
    with pytest.raises(api_sports.ApiSportsError) as error:
        api_sports.api_sports_get("/players/profiles", {"search": "mbappe"})

    assert error.value.stage == "auth"
    assert error.value.to_error()["endpoint"] == "/players/profiles"


def test_api_sports_get_rejects_unsupported_sport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")

    with pytest.raises(api_sports.ApiSportsError) as error:
        api_sports.api_sports_get("/players/profiles", {"search": "mbappe"}, sport="basketball")

    assert error.value.stage == "config"
    assert error.value.to_error()["params"] == {"search": "mbappe"}


def test_api_sports_get_defaults_invalid_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")
    monkeypatch.setenv("APISPORTS_REQUEST_TIMEOUT_SECONDS", "not-a-number")
    factory = _install_client(monkeypatch, [_response(payload={"errors": [], "response": []})])

    api_sports.api_sports_get("/players/profiles", {"search": "mbappe"})

    assert factory.timeouts == [8.0]


@pytest.mark.parametrize("status_code", [499, 500])
def test_api_sports_get_reports_http_errors(monkeypatch: pytest.MonkeyPatch, status_code: int) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")
    _install_client(monkeypatch, [_response(status_code=status_code, payload={"message": "failed"})])

    with pytest.raises(api_sports.ApiSportsError) as error:
        api_sports.api_sports_get("/players/profiles", {"search": "mbappe"})

    error_payload = error.value.to_error()
    assert error_payload["stage"] == "http"
    assert error_payload["http_status"] == status_code


def test_api_sports_get_reports_network_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")
    _install_client(monkeypatch, [httpx.TimeoutException("slow response for secret-key")])

    with pytest.raises(api_sports.ApiSportsError) as error:
        api_sports.api_sports_get("/players/profiles", {"search": "mbappe"})

    assert error.value.stage == "timeout"
    assert "secret-key" not in str(error.value)


def test_api_sports_get_accepts_204_no_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")
    _install_client(monkeypatch, [_response(status_code=204)])

    result = api_sports.api_sports_get("/players/profiles", {"search": "mbappe"})

    assert result["payload"]["response"] == []
    assert result["payload"]["results"] == 0


def test_api_sports_get_reports_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")
    _install_client(monkeypatch, [_response(content=b"{invalid-json")])

    with pytest.raises(api_sports.ApiSportsError) as error:
        api_sports.api_sports_get("/players/profiles", {"search": "mbappe"})

    assert error.value.stage == "decode"


def test_api_sports_get_reports_non_object_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")
    _install_client(monkeypatch, [_response(payload=[{"unexpected": True}])])

    with pytest.raises(api_sports.ApiSportsError) as error:
        api_sports.api_sports_get("/players/profiles", {"search": "mbappe"})

    assert error.value.stage == "decode"


def test_api_sports_get_reports_api_payload_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")
    _install_client(monkeypatch, [_response(payload={"errors": {"token": "bad secret-key"}, "response": []})])

    with pytest.raises(api_sports.ApiSportsError) as error:
        api_sports.api_sports_get("/players/profiles", {"search": "mbappe"})

    error_payload = error.value.to_error()
    assert error_payload["stage"] == "api"
    assert "secret-key" not in error_payload["message"]


def test_fetch_player_intelligence_returns_not_found_for_empty_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")
    _install_client(monkeypatch, [_response(payload={"errors": [], "response": []})])

    result = api_sports.fetch_player_intelligence({"name": "Ghost Player", "aliases": []})

    assert result["status"] == "not_found"
    assert result["errors"][0]["stage"] == "profile"


def test_fetch_player_intelligence_handles_unexpected_response_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")
    _install_client(monkeypatch, [_response(payload={"errors": [], "response": {"player": {"id": 1}}})])

    result = api_sports.fetch_player_intelligence({"name": "Ghost Player", "aliases": []})

    assert result["status"] == "not_found"


def test_fetch_player_intelligence_keeps_profile_on_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")
    monkeypatch.setenv("APISPORTS_FOOTBALL_SEASON", "2026")
    _install_client(
        monkeypatch,
        [
            _response(payload={"errors": [], "response": [{"player": {"id": 276, "name": "Kylian Mbappe"}}]}),
            _response(status_code=500, payload={"message": "teams down"}),
            _response(payload={"errors": {"season": "stats unavailable"}, "response": []}),
        ],
    )

    result = api_sports.fetch_player_intelligence({"name": "Kylian Mbappe", "aliases": ["Mbappe"]})

    assert result["status"] == "partial"
    assert result["player_id"] == 276
    assert "profile" in result
    assert [error["stage"] for error in result["errors"]] == ["http", "api"]


def test_api_sports_get_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APISPORTS_KEY", "secret-key")
    factory = _install_client(monkeypatch, [_response(payload={"errors": [], "response": [{"ok": True}]})])

    first = api_sports.api_sports_get("/players/profiles", {"search": "mbappe"})
    second = api_sports.api_sports_get("/players/profiles", {"search": "mbappe"})

    assert first == second
    assert len(factory.calls) == 1
