from __future__ import annotations

import json
from pathlib import Path

from utils import gmi_client


ROOT = Path(__file__).resolve().parents[1]


def test_rocketride_pipe_uses_builder_components_shape() -> None:
    pipe = json.loads((ROOT / "pipeline/worldcup_broadcast.pipe").read_text())
    assert "components" in pipe
    assert "nodes" not in pipe

    providers = {component["provider"] for component in pipe["components"]}
    assert {"webhook", "tool_http", "response_text"}.issubset(providers)


def test_reference_pipe_is_not_primary_runtime_pipe() -> None:
    reference_pipe = ROOT / "pipeline/reference_builder_sample.pipe"
    assert reference_pipe.exists()
    assert not (ROOT / "new.pipe").exists()


def test_gmi_default_headers_include_optional_org(monkeypatch) -> None:
    monkeypatch.delenv("GMI_ORGANIZATION_ID", raising=False)
    assert gmi_client.get_gmi_default_headers() == {}

    monkeypatch.setenv("GMI_ORGANIZATION_ID", "org-123")
    assert gmi_client.get_gmi_default_headers() == {"X-Organization-ID": "org-123"}
