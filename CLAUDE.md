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
| **GMI Cloud** | STT/TTS/translation inference | OpenAI-compatible API; team has credits. Use for Whisper, Gemma, or other hosted models. |
| **Google AI Studio / Gemini** | Stat detection, NER, translation | Use Gemma 4 or Gemini models via AI Studio API for entity extraction and language tasks. |
| **RocketRide** | AI orchestration & deployment | Open-source runtime; wire the pipeline stages together and deploy via RocketRide. |

## Development Notes

- Hackathon project — favor working demos over production-grade code.
- The `ui` branch is the active development branch; `main` is the base.
- All inference should route through GMI Cloud (OpenAI-compatible endpoint) to use available credits.
- Language/NLP tasks (stat entity detection, translation) should use Gemini/Gemma via Google AI Studio.
- RocketRide should be the glue/runtime that orchestrates the audio → transcript → stats → dub pipeline.
