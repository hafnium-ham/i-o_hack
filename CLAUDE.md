# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**i-o hack** is a post-game interview transcription and enrichment application. The core value proposition:

1. **Subtitles** — transcribe sports interview audio to text in real time or post-game
2. **Dubs** — translate transcribed text and synthesize audio in the viewer's preferred language (audio → text → audio)
3. **Player stats overlay** — detect when a specific player or stat is mentioned and surface relevant stats inline (e.g., highlight or pop-up during the interview playback)

## Architecture (planned)

The pipeline has three stages:

```
Audio input
  └─> Transcription (STT)          e.g. Whisper / AssemblyAI / Deepgram
        └─> Translation (optional) e.g. Google Translate / DeepL
              └─> TTS (for dubs)   e.g. ElevenLabs / Azure TTS

Transcript text
  └─> Entity/stat detection        NER or keyword matching against a stats API
        └─> Stats lookup           e.g. Sportradar / ESPN API
              └─> UI overlay       highlight word + show stat card
```

Key components to build:
- **Ingestion layer** — accepts audio file upload or live stream URL
- **Transcription service** — returns timestamped transcript segments
- **Stat detection** — scans segments for player names / stat keywords; fetches live stats
- **Dubbing pipeline** — translation + TTS synthesis per segment
- **Playback UI** — synced subtitle/dub track with stat pop-up overlays

## Required Technologies (Mandatory for Prize Eligibility)

All three must be used — this is a hard requirement from the hackathon organizers:

| Technology | Role in this project | Notes |
|---|---|---|
| **GMI Cloud** | Translation, analysis, stat detection | OpenAI-compatible API; team has credits. Models: `google/gemma-4-31b-it` for translation + analysis. |
| **Google AI Studio / Gemini** | Transcription (STT) | `gemini-2.5-flash` via `google-genai` SDK; used for audio file upload + transcription. |
| **RocketRide** | AI orchestration & deployment | Open-source runtime; wire the pipeline stages together and deploy via RocketRide. |

## Model Configuration

| Env var | Value | Used by |
|---|---|---|
| `GEMINI_TRANSCRIBE_MODEL` | `gemini-2.5-flash` | agent2 — audio → transcript via Google AI Studio |
| `GMI_TRANSLATION_MODEL` | `google/gemma-4-31b-it` | agent3 — translation via GMI Cloud |
| `GMI_ANALYSIS_MODEL` | `google/gemma-4-31b-it` | agent5 — sentiment/analysis via GMI Cloud |

## Development Notes

- Hackathon project — favor working demos over production-grade code.
- The `fastapi-ui` branch is active development; `main` is the base.
- Transcription routes through Google AI Studio (requires `GOOGLE_API_KEY`) — GMI has no audio upload endpoint.
- Translation and analysis route through GMI Cloud (requires `GMI_API_KEY`) using `google/gemma-4-31b-it`.
- RocketRide should be the glue/runtime that orchestrates the audio → transcript → stats → dub pipeline.
- FastAPI runs on port 8000; Next.js UI runs on port 3000 (bun dev in `ui/`).
- Set `MOCK_AI=true` to skip all AI calls and return placeholder data for UI testing.
