"use client";

import { useCallback, useMemo, useRef, useState, useEffect } from "react";
import VideoPlayer from "@/components/VideoPlayer";
import RightPanel from "@/components/RightPanel";
import { type DubLanguage } from "@/components/DubSelector";
import { type TranscriptSegment } from "@/components/TranscriptionPanel";
import { useTTS } from "@/hooks/useTTS";
import messiResult from "../../public/messi_interview_result.json";

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

function normalizeSegments(result: any): Record<string, ApiTimedSegment[]> {
  const transcriptSegments = result.transcript?.segments ?? [];
  const speakerById = new Map<string, string>(
    transcriptSegments.map((seg: any) => [String(seg.id), String(seg.speaker ?? "AUDIO")])
  );
  const normalized: Record<string, ApiTimedSegment[]> = {};

  for (const [lang, segments] of Object.entries(result.subtitles ?? {})) {
    if (lang.endsWith("_error") || !Array.isArray(segments)) continue;
    normalized[lang] = segments.map((seg: any) => ({
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

function toVisibleSegments(segments: ApiTimedSegment[], currentTime: number): TranscriptSegment[] {
  return segments.map((seg) => ({
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
  const [selectedVideo, setSelectedVideo] = useState<string | null>("messi-interview.mp4");
  const [pipelineStatus] = useState<PipelineStatus>("complete");
  const [segmentsByLanguage] = useState<Record<string, ApiTimedSegment[]>>(() => normalizeSegments(messiResult));
  const [inferenceTime] = useState<number | null>(messiResult.processing_time_seconds ?? 5.4);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const lastSpokenIdRef = useRef<string | null>(null);

  // Hook up browser SpeechSynthesis for TTS dubs
  const { isMuted: isTtsMuted, toggleMute: onToggleTtsMute, speak, stop: stopSpeech } = useTTS();

  const handleVideoSelect = useCallback((filename: string) => {
    setSelectedVideo(filename);
    setCurrentTime(0);
    lastSpokenIdRef.current = null;
    stopSpeech();
  }, [stopSpeech]);

  const selectedLanguageSegments = useMemo(
    () => segmentsByLanguage[dubLanguage] ?? segmentsByLanguage.en ?? [],
    [dubLanguage, segmentsByLanguage]
  );

  const visibleSegments = useMemo(
    () => toVisibleSegments(selectedLanguageSegments, currentTime),
    [currentTime, selectedLanguageSegments]
  );

  // Identify the active segment text for display as subtitle overlay
  const activeSegment = useMemo(() => {
    return visibleSegments.find((seg) => seg.isActive);
  }, [visibleSegments]);

  // Compute video player volume (ducking original audio to 15% when TTS is speaking, unless listening to native Spanish)
  const videoVolume = useMemo(() => {
    if (dubLanguage === "es" || isTtsMuted || !activeSegment) {
      return 1.0;
    }
    return 0.15;
  }, [dubLanguage, isTtsMuted, activeSegment]);

  // Trigger TTS dubbing in sync with active segment
  useEffect(() => {
    // If video is paused, or we are listening to native Spanish, do not use TTS dubs
    if (!isPlaying || dubLanguage === "es") {
      stopSpeech();
      return;
    }

    if (activeSegment) {
      if (lastSpokenIdRef.current !== activeSegment.id) {
        lastSpokenIdRef.current = activeSegment.id;
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
          onPlayChange={setIsPlaying}
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
          languageLabel={LANGUAGE_LABELS[dubLanguage]}
          totalSegments={selectedLanguageSegments.length}
          errorMessage={null}
          isTtsMuted={isTtsMuted}
          onToggleTtsMute={onToggleTtsMute}
        />
      </div>
    </div>
  );
}
