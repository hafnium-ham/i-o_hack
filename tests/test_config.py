from __future__ import annotations

import json
from pathlib import Path

from utils import gmi_client
from utils import env_loader


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


def test_env_loader_reads_local_env_without_overwriting(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GOOGLE_API_KEY=from-file\nGMI_API_KEY=from-file\nEXISTING=from-file\n", encoding="utf-8")

    monkeypatch.setattr(env_loader, "_ENV_LOADED", False)
    monkeypatch.setattr(env_loader, "candidate_env_files", lambda: [env_file])
    monkeypatch.setenv("EXISTING", "from-env")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GMI_API_KEY", raising=False)

    loaded = env_loader.load_env_files()

    assert loaded == [env_file]
    assert env_loader.has_live_ai_credentials()
    assert env_loader.os.getenv("GOOGLE_API_KEY") == "from-file"
    assert env_loader.os.getenv("EXISTING") == "from-env"
