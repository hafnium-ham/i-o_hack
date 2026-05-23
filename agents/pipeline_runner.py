from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from utils.env_loader import load_env_files

load_env_files()

from agents import agent1_ingest, agent2_transcribe, agent3_translate, agent4_stats, agent5_analysis, output_assembler


def run_pipeline(raw_input: dict) -> dict:
    started_at = time.time()
    payload = dict(raw_input)
    payload.setdefault("job_id", str(uuid.uuid4()))

    audio = agent1_ingest.run(payload)
    transcript = agent2_transcribe.run(audio)
    transcript["target_languages"] = payload.get("target_languages", audio.get("target_languages", []))

    with ThreadPoolExecutor(max_workers=3) as executor:
        subtitles_future = executor.submit(agent3_translate.run, transcript)
        stats_future = executor.submit(agent4_stats.run, transcript)
        analysis_future = executor.submit(agent5_analysis.run, transcript)
        subtitles = subtitles_future.result()
        stats = stats_future.result()
        analysis = analysis_future.result()

    return output_assembler.run(audio, transcript, subtitles, stats, analysis, started_at=started_at)
