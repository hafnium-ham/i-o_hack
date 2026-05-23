from __future__ import annotations

import time

from utils.schemas import FinalOutput


def run(
    audio_payload: dict,
    transcript_payload: dict,
    subtitle_payload: dict,
    stat_events_payload: dict,
    analysis_payload: dict,
    started_at: float | None = None,
) -> dict:
    now = time.time()
    return FinalOutput(
        job_id=transcript_payload["job_id"],
        source_title=audio_payload.get("source_title"),
        source_url=audio_payload.get("source_url"),
        duration_seconds=audio_payload.get("duration_seconds"),
        transcript=transcript_payload,
        subtitles=subtitle_payload.get("subtitles", {}),
        stat_events=stat_events_payload.get("stat_events", []),
        analysis=analysis_payload,
        processing_time_seconds=round(now - started_at, 3) if started_at else 0.0,
        processed_at=now,
    ).model_dump()

