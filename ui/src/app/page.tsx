"use client";

import { useCallback, useRef, useState } from "react";
import VideoPlayer from "@/components/VideoPlayer";
import RightPanel from "@/components/RightPanel";
import { type DubLanguage } from "@/components/DubSelector";
import { type TranscriptSegment } from "@/components/TranscriptionPanel";

type PipelineStatus = "idle" | "processing" | "complete" | "error";

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function Home() {
  const [dubLanguage, setDubLanguage] = useState<DubLanguage>("en");
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>("idle");
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [inferenceTime, setInferenceTime] = useState<number | null>(null);
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
    setSegments([]);
    setInferenceTime(null);
  }, []);

  const handleTranscribe = useCallback(async () => {
    if (!selectedVideo) return;
    stopPolling();
    setPipelineStatus("processing");
    setSegments([]);
    setInferenceTime(null);

    let jobId: string;
    try {
      const res = await fetch("/api/transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: selectedVideo, targetLanguages: ["es", "pt", "fr"] }),
      });
      if (!res.ok) throw new Error("Submit failed");
      const data = await res.json();
      jobId = data.job_id;
    } catch {
      setPipelineStatus("error");
      return;
    }

    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        const job = await res.json();

        if (job.status === "complete" && job.result) {
          stopPolling();
          const rawSegments: Array<{
            id: number;
            start: number;
            end: number;
            speaker: string;
            text: string;
          }> = job.result.transcript?.segments ?? [];

          setSegments(
            rawSegments.map((seg) => ({
              id: String(seg.id),
              speaker: seg.speaker,
              text: seg.text,
              timestamp: formatTimestamp(seg.start),
              isFinal: true,
            }))
          );
          setInferenceTime(job.result.processing_time_seconds ?? null);
          setPipelineStatus("complete");
        } else if (job.status === "error") {
          stopPolling();
          console.error("[pipeline] job failed:", job.error);
          setPipelineStatus("error");
        }
      } catch {
        // keep polling on transient errors
      }
    }, 2000);
  }, [selectedVideo]);

  return (
    <div className="flex h-full" style={{ background: "#ffffff" }}>
      <div className="flex flex-col flex-1 min-w-0 p-4">
        <VideoPlayer dubLanguage={dubLanguage} onVideoSelect={handleVideoSelect} />
      </div>

      <div className="w-[420px] shrink-0 flex flex-col">
        <RightPanel
          dubLanguage={dubLanguage}
          onDubLanguageChange={setDubLanguage}
          segments={segments}
          pipelineStatus={pipelineStatus}
          inferenceTime={inferenceTime}
          selectedVideo={selectedVideo}
          onTranscribe={handleTranscribe}
        />
      </div>
    </div>
  );
}
