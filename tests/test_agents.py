from __future__ import annotations

import os

from agents import agent3_translate, agent4_stats, agent5_analysis, output_assembler
from utils.json_helpers import parse_json_object


TRANSCRIPT = {
    "job_id": "test-001",
    "segments": [
        {
            "id": 0,
            "start": 0.0,
            "end": 4.0,
            "speaker": "REPORTER",
            "text": "Mbappe, you scored 3 goals tonight.",
            "confidence": 0.97,
        },
        {
            "id": 1,
            "start": 4.2,
            "end": 8.0,
            "speaker": "PLAYER",
            "text": "Lionel Messi helped with two assists and the team stayed calm.",
            "confidence": 0.95,
        },
    ],
    "full_text": "Mbappe, you scored 3 goals tonight. Lionel Messi helped with two assists and the team stayed calm.",
    "detected_language": "en",
    "word_count": 16,
    "target_languages": ["es", "pt"],
}


def test_translation_mock_preserves_languages() -> None:
    os.environ["MOCK_AI"] = "true"
    result = agent3_translate.run(TRANSCRIPT)
    assert set(["en", "es", "pt"]).issubset(result["subtitles"])
    assert result["subtitles"]["es"][0]["id"] == 0


def test_fuzzy_lookup_mbappe() -> None:
    player = agent4_stats.fuzzy_lookup_player("Mabppe")
    assert player is not None
    assert player["name"] == "Kylian Mbappe"


def test_stats_extracts_named_players() -> None:
    result = agent4_stats.run(TRANSCRIPT)
    names = {event["player_name"] for event in result["stat_events"]}
    assert "Kylian Mbappe" in names
    assert "Lionel Messi" in names


def test_stats_can_enrich_players_when_live_lookup_enabled(monkeypatch) -> None:
    monkeypatch.setenv("APISPORTS_LIVE_LOOKUP", "true")
    calls: list[str] = []

    def fake_enrich_player_card(player: dict) -> dict:
        calls.append(player["name"])
        return {**player, "api_sports": {"source": "api-sports", "status": "ok", "player_id": 1, "errors": []}}

    monkeypatch.setattr(agent4_stats, "enrich_player_card", fake_enrich_player_card)

    result = agent4_stats.run(TRANSCRIPT)
    cards = [event["player_card"] for event in result["stat_events"]]

    assert "Kylian Mbappe" in calls
    assert "Lionel Messi" in calls
    assert all(card["api_sports"]["source"] == "api-sports" for card in cards)


def test_stats_live_lookup_disabled_never_enriches(monkeypatch) -> None:
    monkeypatch.setenv("APISPORTS_LIVE_LOOKUP", "false")

    def fail_enrich_player_card(player: dict) -> dict:
        raise AssertionError(f"Unexpected API-SPORTS enrichment for {player['name']}")

    monkeypatch.setattr(agent4_stats, "enrich_player_card", fail_enrich_player_card)

    result = agent4_stats.run(TRANSCRIPT)

    assert result["stat_events"]
    assert all("api_sports" not in event["player_card"] for event in result["stat_events"])


def test_stats_live_lookup_failure_keeps_local_player_cards(monkeypatch) -> None:
    monkeypatch.setenv("APISPORTS_LIVE_LOOKUP", "true")

    def fail_enrich_player_card(player: dict) -> dict:
        raise RuntimeError("API-SPORTS exploded")

    monkeypatch.setattr(agent4_stats, "enrich_player_card", fail_enrich_player_card)

    result = agent4_stats.run(TRANSCRIPT)
    cards = [event["player_card"] for event in result["stat_events"]]

    assert {card["name"] for card in cards} == {"Kylian Mbappe", "Lionel Messi"}
    assert all(card["api_sports"]["status"] == "error" for card in cards)
    assert all(card["api_sports"]["errors"][0]["stage"] == "unexpected" for card in cards)


def test_stats_keeps_sentence_level_stat_attribution() -> None:
    transcript = {
        **TRANSCRIPT,
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 8.0,
                "speaker": "PLAYER",
                "text": "I scored three goals tonight. Lionel Messi and Kylian Mbappe pushed the tempo all match.",
                "confidence": 0.95,
            }
        ],
        "full_text": "I scored three goals tonight. Lionel Messi and Kylian Mbappe pushed the tempo all match.",
    }
    result = agent4_stats.run(transcript)
    events = result["stat_events"]
    assert {event["stat_category"] for event in events} == {"general"}
    assert all(event["mentioned_value"] == "" for event in events)


def test_analysis_mock_shape() -> None:
    os.environ["MOCK_AI"] = "true"
    result = agent5_analysis.run(TRANSCRIPT)
    assert result["overall_sentiment"] == "confident"
    assert result["tone_timeline"][0]["segment_id"] == 0


def test_output_assembler_shape() -> None:
    final = output_assembler.run(
        {"job_id": "test-001", "source_title": "sample", "duration_seconds": 8.0},
        TRANSCRIPT,
        {"job_id": "test-001", "subtitles": {"en": []}},
        {"job_id": "test-001", "stat_events": []},
        {"job_id": "test-001", "summary_bullets": [], "overall_sentiment": "neutral", "speaker_sentiment": {}, "tone_timeline": []},
        started_at=1.0,
    )
    assert final["job_id"] == "test-001"
    assert "processing_time_seconds" in final


def test_parse_json_object_recovers_prefixed_json() -> None:
    assert parse_json_object('Result:\n```json\n{"ok": true}\n```') == {"ok": True}
    assert parse_json_object('Here is the payload: [{"id": 1}]') == [{"id": 1}]
