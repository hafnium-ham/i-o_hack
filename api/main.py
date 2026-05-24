from __future__ import annotations

import asyncio
import os
import traceback
import uuid
from typing import Any

from dotenv import load_dotenv
load_dotenv()

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.pipeline_runner import run_pipeline
from utils.schemas import RawInput


app = FastAPI(title="World Cup AI Broadcast API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

JOB_STORE: dict[str, dict[str, Any]] = {}


class ProcessRequest(BaseModel):
    source_type: str = Field(pattern="^(youtube_url|file_path)$")
    source_value: str = Field(min_length=1)
    target_languages: list[str] = Field(default_factory=lambda: ["es", "pt", "fr"])
    mode: str = Field(default="direct", pattern="^(direct|rocketride)$")


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    partial_transcript: dict[str, Any] | None = None
    partial_subtitles: dict[str, Any] | None = None


async def _run_direct(job_id: str, request: ProcessRequest) -> dict:
    def on_partial(partial: dict) -> None:
        JOB_STORE[job_id]["partial_transcript"] = partial.get("transcript", partial)
        JOB_STORE[job_id]["partial_subtitles"] = partial.get("subtitles", {})

    payload = RawInput(
        job_id=job_id,
        source_type=request.source_type,
        source_value=request.source_value,
        target_languages=request.target_languages,
    ).model_dump()
    return await asyncio.to_thread(run_pipeline, payload, on_partial)


async def _run_rocketride(job_id: str, request: ProcessRequest) -> dict:
    url = os.getenv("ROCKETRIDE_PROCESS_URL", "http://localhost:5565/process")
    payload = RawInput(
        job_id=job_id,
        source_type=request.source_type,
        source_value=request.source_value,
        target_languages=request.target_languages,
    ).model_dump()
    async with httpx.AsyncClient(timeout=float(os.getenv("PIPELINE_TIMEOUT_SECONDS", "300"))) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def _run_job(job_id: str, request: ProcessRequest) -> None:
    JOB_STORE[job_id]["status"] = "processing"
    try:
        result = await (_run_rocketride(job_id, request) if request.mode == "rocketride" else _run_direct(job_id, request))
    except Exception as exc:
        traceback.print_exc()
        JOB_STORE[job_id]["status"] = "error"
        JOB_STORE[job_id]["error"] = str(exc)
        return

    JOB_STORE[job_id]["status"] = "complete"
    JOB_STORE[job_id]["result"] = result


@app.post("/process", response_model=JobStatus)
async def submit_job(request: ProcessRequest, background_tasks: BackgroundTasks) -> JobStatus:
    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {"status": "queued", "result": None, "error": None, "partial_transcript": None, "partial_subtitles": None}
    background_tasks.add_task(_run_job, job_id, request)
    return JobStatus(job_id=job_id, status="queued")


@app.post("/process/sync")
async def process_sync(request: ProcessRequest) -> dict:
    job_id = str(uuid.uuid4())
    result = await (_run_rocketride(job_id, request) if request.mode == "rocketride" else _run_direct(job_id, request))
    return result


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str) -> JobStatus:
    if job_id not in JOB_STORE:
        raise HTTPException(status_code=404, detail="Job not found")
    job = JOB_STORE[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        result=job.get("result"),
        error=job.get("error"),
        partial_transcript=job.get("partial_transcript"),
        partial_subtitles=job.get("partial_subtitles"),
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "mode_default": "direct"}
