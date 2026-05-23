"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import VideoPlayer from "@/components/VideoPlayer";
import RightPanel from "@/components/RightPanel";
import { type DubLanguage } from "@/components/DubSelector";
import { type TranscriptSegment } from "@/components/TranscriptionPanel";

type PipelineStatus = "idle" | "processing" | "complete" | "error";

type ApiTimedSegment = {
  id: number | string;
  start: number;
  end: number;
  speaker?: string;
  text: string;
};

type JobResult = {
  processing_time_seconds?: number;
  transcript?: {
    detected_language?: string;
    segments?: ApiTimedSegment[];
  };
  subtitles?: Record<string, Array<Omit<ApiTimedSegment, "speaker">>>;
};

const TARGET_LANGUAGES: DubLanguage[] = ["en", "es", "de"];

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

function normalizeSegments(result: JobResult): Record<string, ApiTimedSegment[]> {
  const transcriptSegments = result.transcript?.segments ?? [];
  const speakerById = new Map(transcriptSegments.map((seg) => [String(seg.id), seg.speaker ?? "Audio"]));
  const normalized: Record<string, ApiTimedSegment[]> = {};

  for (const [lang, segments] of Object.entries(result.subtitles ?? {})) {
    if (lang.endsWith("_error") || !Array.isArray(segments)) continue;
    normalized[lang] = segments.map((seg) => ({
      id: seg.id,
      start: Number(seg.start),
      end: Number(seg.end),
      speaker: speakerById.get(String(seg.id)) ?? "Audio",
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

function toVisibleSegments(segments: ApiTimedSegment[], currentTime: number): TranscriptSegment[] {
  return segments
    .filter((seg) => seg.start <= currentTime + 0.2)
    .map((seg) => ({
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
  const [currentTime, setCurrentTime] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const handleVideoSelect = useCallback((filename: string) => {
    stopPolling();
    setSelectedVideo(filename);
    setPipelineStatus("idle");
    setSegmentsByLanguage({});
    setInferenceTime(null);
    setCurrentTime(0);
    setErrorMessage(null);
  }, []);

  const handleTranscribe = useCallback(async () => {
    if (!selectedVideo) return;
    stopPolling();
    setPipelineStatus("processing");
    setSegmentsByLanguage({});
    setInferenceTime(null);
    setCurrentTime(0);
    setErrorMessage(null);

    let jobId: string;
    try {
      const res = await fetch("/api/transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: selectedVideo, targetLanguages: TARGET_LANGUAGES }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Submit failed");
      jobId = data.job_id;
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Submit failed");
      setPipelineStatus("error");
      return;
    }

    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        const job = await res.json();

        if (job.status === "complete" && job.result) {
          stopPolling();
          setSegmentsByLanguage(normalizeSegments(job.result));
          setInferenceTime(job.result.processing_time_seconds ?? null);
          setPipelineStatus("complete");
        } else if (job.status === "error") {
          stopPolling();
          setErrorMessage(job.error ?? "Pipeline job failed");
          setPipelineStatus("error");
        }
      } catch {
        // Keep polling on transient dev-server errors.
      }
    }, 1200);
  }, [selectedVideo]);

  const selectedLanguageSegments = useMemo(
    () => segmentsByLanguage[dubLanguage] ?? segmentsByLanguage.en ?? [],
    [dubLanguage, segmentsByLanguage]
  );
  const visibleSegments = useMemo(
    () => toVisibleSegments(selectedLanguageSegments, currentTime),
    [currentTime, selectedLanguageSegments]
  );

  return (
    <div className="flex h-full" style={{ background: "#ffffff" }}>
      <div className="flex flex-col flex-1 min-w-0 p-4">
        <VideoPlayer onVideoSelect={handleVideoSelect} onTimeChange={setCurrentTime} />
      </div>

      <div className="w-[420px] shrink-0 flex flex-col">
        <RightPanel
          dubLanguage={dubLanguage}
          onDubLanguageChange={setDubLanguage}
          segments={visibleSegments}
          pipelineStatus={pipelineStatus}
          inferenceTime={inferenceTime}
          selectedVideo={selectedVideo}
          onTranscribe={handleTranscribe}
          currentTime={currentTime}
          languageLabel={LANGUAGE_LABELS[dubLanguage]}
          totalSegments={selectedLanguageSegments.length}
          errorMessage={errorMessage}
        />
      </div>
    </div>
  );
}
