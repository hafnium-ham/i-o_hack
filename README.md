# SportsCast

Post-game interview transcription and stats overlay. Paste a sports interview video, get live subtitles, player stat cards, and dubbed audio in your language.

## Running the UI

```bash
cd ui
bun install
bun dev
```

Open [http://localhost:3000](http://localhost:3000). Paste a YouTube URL and hit **Load**.

## Stack

- **UI** — Next.js 16 + TypeScript + Tailwind (`ui/`)
# World Cup AI Broadcast Assistant

Backend pipeline for a hackathon demo that turns post-match interview audio/video into:

- normalized audio
- speaker-labeled transcript
- translated subtitles
- player stat overlay events
- interview summary and sentiment
- one frontend-ready JSON payload

The backend can run in two modes:

- `direct`: FastAPI calls the local Python agents directly. Use this for frontend development and local demos.
- `rocketride`: FastAPI forwards the request to a running RocketRide process endpoint.

External AI calls are isolated behind environment variables. Set `MOCK_AI=true` to run the local smoke path without Gemini or GMI keys.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

System binaries required for real ingest:

```bash
sudo apt install ffmpeg
```

You also need `yt-dlp` from `requirements.txt` for YouTube sources.

## Environment

Required for live AI mode:

- `GOOGLE_API_KEY`: Gemini transcription
- `GMI_API_KEY`: GMI Cloud OpenAI-compatible inference
- `GMI_ORGANIZATION_ID`: optional GMI organization header for multi-organization accounts

Useful local defaults:

```bash
MOCK_AI=true
JOBS_DIR=/tmp/jobs
PLAYERS_DB_PATH=data/players.json
```

GMI Cloud is configured through `GMI_BASE_URL`, defaulting to `https://api.gmi-serving.com/v1`.

Optional API-SPORTS live player enrichment:

```bash
APISPORTS_KEY=your_api_sports_key
APISPORTS_LIVE_LOOKUP=true
APISPORTS_FOOTBALL_SEASON=2026
APISPORTS_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
```

When `APISPORTS_LIVE_LOOKUP=true`, `agent4_stats` keeps the local player database as a fallback and adds an `api_sports` object to each matched `player_card` with player profile, team history, and season stats when the API has coverage. Leave it `false` for tests, offline demos, and runs that should not spend API quota.

## Run API

```bash
MOCK_AI=true uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Submit a synchronous local job:

```bash
curl -X POST http://localhost:8000/process/sync \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "file_path",
    "source_value": "tests/fixtures/sample_interview.wav",
    "target_languages": ["es", "pt"],
    "mode": "direct"
  }'
```

For async frontend flow, use `POST /process`, then poll `GET /jobs/{job_id}`.

## Run UI

The Next UI is in `ui/`. It lists local MP4 files from `ui/public`.

```bash
cd ui
npm install --package-lock=false
npm run dev
```

For the local Messi interview file, put the MP4 directly in `ui/public`:

```bash
mv YTDown_YouTube_Messi-Postgame-Interview-After-Leading-I_Media_8VIgdcabDHE_001_1080p.mp4 ui/public/messi-interview.mp4
```

## Run Directly Without RocketRide

Use the direct script for a local audio/video file. It loads `.env.local`/`.env` from this project or the parent workspace and writes a frontend-ready JSON payload.

Mock/offline verification:

```bash
.venv/bin/python scripts/process_interview_direct.py --mock-ai
```

Live interview processing:

```bash
MOCK_AI=false .venv/bin/python scripts/process_interview_direct.py
```

The default source is `ui/public/messi-interview.mp4`, and the default output is `outputs/messi_interview_result.json`. Without `GOOGLE_API_KEY`, live mode uses local faster-whisper for transcription and `GMI_API_KEY` for translation/analysis. Rerun with `--mock-ai` to verify ingest, subtitles, stats, analysis shape, and final assembly without external AI calls.

## RocketRide

The RocketRide graph is in `pipeline/worldcup_broadcast.pipe`. It is a thin RocketRide wrapper around the working FastAPI pipeline:

1. Start FastAPI:

```bash
MOCK_AI=true uvicorn api.main:app --host 0.0.0.0 --port 8000
```

2. Open `pipeline/worldcup_broadcast.pipe` in RocketRide and run it.

The graph accepts the same JSON payload as `POST /process/sync`, forwards it to `ROCKETRIDE_FASTAPI_PROCESS_SYNC_URL` (default `http://localhost:8000/process/sync`), and returns the final JSON payload. `pipeline/reference_builder_sample.pipe` is the original builder export kept only as a reference.

FastAPI can forward to RocketRide by setting:

```bash
ROCKETRIDE_PROCESS_URL=http://localhost:5565/process
```

Then call the API with `"mode": "rocketride"`.

## Test

```bash
python3 -m pytest -q
MOCK_AI=true python3 scripts/test_pipeline.py
```

The smoke script uses `tests/fixtures/sample_interview.wav` and returns the complete final payload.
