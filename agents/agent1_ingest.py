from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from utils.schemas import AudioPayload, RawInput


JOBS_DIR = Path(os.getenv("JOBS_DIR", "/tmp/jobs"))


def _run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        command = " ".join(args)
        stderr = exc.stderr.strip() if exc.stderr else ""
        stdout = exc.stdout.strip() if exc.stdout else ""
        detail = stderr or stdout or f"exit code {exc.returncode}"
        raise RuntimeError(f"Command failed: {command}\n{detail}") from exc


def _require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Missing required system binary: {name}")


def _probe_duration(path: Path) -> float:
    probe = _run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ]
    )
    return float(json.loads(probe.stdout)["format"]["duration"])


def run(raw_input: dict) -> dict:
    request = RawInput.model_validate(raw_input)
    job_id = request.job_id or str(uuid.uuid4())
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    _require_binary("ffmpeg")
    _require_binary("ffprobe")

    title = "Unknown Interview"
    source_url = None

    if request.source_type == "youtube_url":
        _require_binary("yt-dlp")
        source_url = request.source_value
        raw_audio_prefix = job_dir / "raw_audio"
        result = _run_command(
            [
                "yt-dlp",
                "--extract-audio",
                "--audio-format",
                "wav",
                "--audio-quality",
                "0",
                "--output",
                str(raw_audio_prefix) + ".%(ext)s",
                "--print",
                "title",
                request.source_value,
            ]
        )
        title = result.stdout.strip().splitlines()[0] if result.stdout.strip() else "YouTube Interview"
        matches = list(job_dir.glob("raw_audio.*"))
        if not matches:
            raise RuntimeError("yt-dlp did not produce an audio file.")
        raw_path = matches[0]
    else:
        raw_path = Path(request.source_value).expanduser().resolve()
        if not raw_path.exists():
            raise FileNotFoundError(f"Input file not found: {raw_path}")
        title = raw_path.stem

    normalized_path = job_dir / "audio.wav"
    _run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(raw_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(normalized_path),
        ]
    )

    payload = AudioPayload(
        job_id=job_id,
        audio_path=str(normalized_path),
        duration_seconds=_probe_duration(normalized_path),
        source_title=title,
        source_url=source_url,
        target_languages=request.target_languages,
    )
    return payload.model_dump()
