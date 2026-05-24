from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.pipeline_runner import run_pipeline
from utils.env_loader import has_gmi_credentials, load_env_files


DEFAULT_SOURCE = ROOT / "ui" / "public" / "messi-interview.mp4"
DEFAULT_OUTPUT = ROOT / "outputs" / "messi_interview_result.json"


def _parse_languages(raw: str) -> list[str]:
    return [lang.strip() for lang in raw.split(",") if lang.strip()]


def _redacted_missing_keys() -> list[str]:
    required = ["GMI_API_KEY"]
    provider = os.getenv("TRANSCRIBE_PROVIDER", "auto").lower()
    if provider in {"gemini", "google"}:
        required.append("GOOGLE_API_KEY")
    return [key for key in required if not os.getenv(key)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the direct local pipeline on an interview file.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="Local audio/video file path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="JSON output path.")
    parser.add_argument("--target-languages", default="en,es,de", help="Comma-separated subtitle languages.")
    parser.add_argument("--job-id", default="messi-interview-direct", help="Stable job id for output/cache paths.")
    parser.add_argument("--mock-ai", action="store_true", help="Run without Gemini/GMI by using mock transcript/analysis/translation.")
    args = parser.parse_args()

    load_env_files()

    if args.mock_ai:
        os.environ["MOCK_AI"] = "true"
    elif os.getenv("MOCK_AI", "").lower() not in {"1", "true", "yes"} and not has_gmi_credentials():
        missing = ", ".join(_redacted_missing_keys())
        raise SystemExit(
            "Live mode needs credentials before this interview can be translated/analyzed. "
            f"Missing: {missing}. Add them to .env, or rerun with --mock-ai."
        )

    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"Source file not found: {source}")

    payload = {
        "source_type": "file_path",
        "source_value": str(source),
        "target_languages": _parse_languages(args.target_languages),
        "job_id": args.job_id,
    }
    result = run_pipeline(payload)

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote direct pipeline result: {output}")
    print(f"Job id: {result['job_id']}")
    print(f"Duration seconds: {result.get('duration_seconds')}")
    print(f"Transcript segments: {len(result.get('transcript', {}).get('segments', []))}")
    print(f"Stat events: {len(result.get('stat_events', []))}")


if __name__ == "__main__":
    main()
