from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.pipeline_runner import run_pipeline


def main() -> None:
    os.environ.setdefault("MOCK_AI", "true")
    result = run_pipeline(
        {
            "source_type": "file_path",
            "source_value": "tests/fixtures/sample_interview.wav",
            "target_languages": ["es", "pt"],
            "job_id": "smoke-test-001",
        }
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
