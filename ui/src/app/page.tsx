"use client";

import { useCallback, useMemo, useRef, useState, useEffect } from "react";
import VideoPlayer from "@/components/VideoPlayer";
import RightPanel from "@/components/RightPanel";
import { type DubLanguage } from "@/components/DubSelector";
import { type TranscriptSegment } from "@/components/TranscriptionPanel";
import { useTTS } from "@/hooks/useTTS";

type PipelineStatus = "idle" | "processing" | "partial" | "complete" | "error";

type ApiTimedSegment = {
  id: number | string;
  start: number;
  end: number;
  speaker?: string;
  text: string;
};

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";
const POLL_INTERVAL_MS = 2500;

const LANGUAGE_LABELS: Record<DubLanguage, string> = {
  en: "English",
  es: "Spanish",
  de: "German",
};

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function normalizeSegments(result: any): Record<string, ApiTimedSegment[]> {
  const transcriptSegments = result.transcript?.segments ?? [];
  const speakerById = new Map<string, string>(
    transcriptSegments.map((seg: any) => [String(seg.id), String(seg.speaker ?? "AUDIO")])
  );
  const normalized: Record<string, ApiTimedSegment[]> = {};

  for (const [lang, segments] of Object.entries(result.subtitles ?? {})) {
    if (lang.endsWith("_error") || !Array.isArray(segments)) continue;
    normalized[lang] = (segments as any[]).map((seg: any) => ({
      id: seg.id,
      start: Number(seg.start),
      end: Number(seg.end),
      speaker: speakerById.get(String(seg.id)) ?? "AUDIO",
      text: seg.text,
    }));
  }

  if (!normalized.en && transcriptSegments.length > 0) {
    normalized.en = transcriptSegments;
  }

  const detected = result.transcript?.detected_language;
  if (detected && !normalized[detected] && transcriptSegments.length > 0) {
    normalized[detected] = transcriptSegments;
  }

  return normalized;
}

function toVisibleSegments(
  segments: ApiTimedSegment[],
  currentTime: number,
  hasStartedPlaying: boolean
): TranscriptSegment[] {
  if (!hasStartedPlaying) return [];
  return segments.filter((seg) => currentTime >= seg.start).map((seg) => ({
    id: String(seg.id),
    speaker: seg.speaker,
    text: seg.text,
    timestamp: formatTimestamp(seg.start),
    endTimestamp: formatTimestamp(seg.end),
    start: seg.start,
    end: seg.end,
    isActive: currentTime >= seg.start && currentTime < seg.end,
    isFinal: currentTime >= seg.end,
  }));
}

export default function Home() {
  const [dubLanguage, setDubLanguage] = useState<DubLanguage>("en");
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>("idle");
  const [segmentsByLanguage, setSegmentsByLanguage] = useState<Record<string, ApiTimedSegment[]>>({});
  const [inferenceTime, setInferenceTime] = useState<number | null>(null);
  const [firstChunkTime, setFirstChunkTime] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasStartedPlaying, setHasStartedPlaying] = useState(false);
  const lastSpokenIdRef = useRef<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const transcriptionStartRef = useRef<number | null>(null);

  const { isMuted: isTtsMuted, toggleMute: onToggleTtsMute, speak, stop: stopSpeech } = useTTS();

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const startTranscription = useCallback(async (filename: string) => {
    stopPolling();
    setPipelineStatus("processing");
    setSegmentsByLanguage({});
    setInferenceTime(null);
    setFirstChunkTime(null);
    setErrorMessage(null);
    setHasStartedPlaying(false);
    transcriptionStartRef.current = Date.now();

    try {
      const res = await fetch("/api/transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, targetLanguages: ["en", "es", "de"] }),
      });
      if (!res.ok) throw new Error(`Transcribe request failed: ${res.status}`);
      const { job_id } = await res.json();

      pollTimerRef.current = setInterval(async () => {
        try {
          const statusRes = await fetch(`${FASTAPI_URL}/jobs/${job_id}`);
          if (!statusRes.ok) return;
          const job = await statusRes.json();

          if (job.partial_transcript?.segments?.length > 0 && job.status === "processing") {
            setSegmentsByLanguage(normalizeSegments({
              transcript: job.partial_transcript,
              subtitles: job.partial_subtitles ?? {},
            }));
            setPipelineStatus((prev) => {
              if (prev === "processing" && transcriptionStartRef.current) {
                setFirstChunkTime(Math.round((Date.now() - transcriptionStartRef.current) / 100) / 10);
              }
              return "partial";
            });
          }
          if (job.status === "complete" && job.result) {
            stopPolling();
            setSegmentsByLanguage(normalizeSegments(job.result));
            setInferenceTime(job.result.processing_time_seconds ?? null);
            setPipelineStatus("complete");
          } else if (job.status === "error") {
            stopPolling();
            setErrorMessage(job.error ?? "Transcription failed.");
            setPipelineStatus("error");
          }
        } catch {
          // transient poll error — keep polling
        }
      }, POLL_INTERVAL_MS);
    } catch (err: any) {
      setErrorMessage(err.message ?? "Failed to start transcription.");
      setPipelineStatus("error");
    }
  }, [stopPolling]);

  const handleVideoSelect = useCallback((filename: string) => {
    setSelectedVideo(filename);
    setCurrentTime(0);
    setIsPlaying(false);
    setHasStartedPlaying(false);
    lastSpokenIdRef.current = null;
    stopSpeech();
    startTranscription(filename);
  }, [stopSpeech, startTranscription]);

  const handlePlayChange = useCallback((playing: boolean) => {
    setIsPlaying(playing);
    if (playing) setHasStartedPlaying(true);
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const isLanguageReady = dubLanguage in segmentsByLanguage;

  const selectedLanguageSegments = useMemo(
    () => segmentsByLanguage[dubLanguage] ?? segmentsByLanguage.en ?? [],
    [dubLanguage, segmentsByLanguage]
  );

  const visibleSegments = useMemo(
    () => toVisibleSegments(selectedLanguageSegments, currentTime, hasStartedPlaying),
    [currentTime, selectedLanguageSegments, hasStartedPlaying]
  );

  const activeSegment = useMemo(
    () => visibleSegments.find((seg) => seg.isActive),
    [visibleSegments]
  );

  const videoVolume = useMemo(() => {
    if (dubLanguage === "es" || isTtsMuted || !activeSegment) return 1.0;
    return 0.15;
  }, [dubLanguage, isTtsMuted, activeSegment]);

  useEffect(() => {
    if (!isPlaying || dubLanguage === "es") {
      stopSpeech();
      return;
    }
    if (activeSegment) {
      const key = `${dubLanguage}:${activeSegment.id}`;
      if (lastSpokenIdRef.current !== key) {
        lastSpokenIdRef.current = key;
        speak(activeSegment.text, dubLanguage);
      }
    } else {
      stopSpeech();
      lastSpokenIdRef.current = null;
    }
  }, [activeSegment, dubLanguage, isPlaying, speak, stopSpeech]);

  return (
    <div className="flex h-full" style={{ background: "#ffffff" }}>
      <div className="flex flex-col flex-1 min-w-0 p-4">
        <VideoPlayer
          onVideoSelect={handleVideoSelect}
          onTimeChange={setCurrentTime}
          onPlayChange={handlePlayChange}
          activeSegmentText={activeSegment?.text}
          volume={videoVolume}
        />
      </div>

      <div className="w-[420px] shrink-0 flex flex-col">
        <RightPanel
          dubLanguage={dubLanguage}
          onDubLanguageChange={setDubLanguage}
          segments={visibleSegments}
          pipelineStatus={pipelineStatus}
          inferenceTime={inferenceTime}
          selectedVideo={selectedVideo}
          currentTime={currentTime}
          languageLabel={isLanguageReady ? LANGUAGE_LABELS[dubLanguage] : `${LANGUAGE_LABELS[dubLanguage]} (translating…)`}
          firstChunkTime={firstChunkTime}
          totalSegments={selectedLanguageSegments.length}
          errorMessage={errorMessage}
          isTtsMuted={isTtsMuted}
          onToggleTtsMute={onToggleTtsMute}
        />
      </div>
    </div>
  );
}
