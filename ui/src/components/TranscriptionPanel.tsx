"use client";

import { useEffect, useRef } from "react";

export type TranscriptSegment = {
  id: string;
  speaker?: string;
  text: string;
  timestamp?: string;
  endTimestamp?: string;
  start: number;
  end: number;
  isActive: boolean;
  isFinal: boolean;
};

type PipelineStatus = "idle" | "processing" | "complete" | "error";

type Props = {
  segments?: TranscriptSegment[];
  pipelineStatus?: PipelineStatus;
  inferenceTime?: number | null;
  currentTime?: number;
  languageLabel?: string;
  totalSegments?: number;
  errorMessage?: string | null;
};


export default function TranscriptionPanel({
  segments = [],
  pipelineStatus = "idle",
  inferenceTime,
  currentTime = 0,
  languageLabel = "English",
  totalSegments = 0,
  errorMessage,
}: Props) {
  const activeRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [currentTime, segments]);

  return (
    <div
      className="flex flex-col h-full rounded-xl overflow-hidden"
      style={{
        border: "3px solid var(--gold)",
        background: "#ffffff",
        boxShadow: "0 0 30px rgba(245,184,0,0.15), 4px 4px 0 var(--orange)",
      }}
    >
      <div
        className="px-4 py-3"
        style={{
          borderBottom: "3px solid var(--gold)",
          background: "#ffffff",
        }}
      >
        <span className="text-xs font-black uppercase tracking-widest" style={{ color: "var(--orange)" }}>
          {languageLabel} Transcription
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 text-sm">
        {pipelineStatus === "processing" ? (
          <p className="text-center mt-8" style={{ color: "#aaa" }}>
            Transcribing and translating the full video. Captions will stream with playback when ready.
          </p>
        ) : pipelineStatus === "error" ? (
          <p className="text-center mt-8" style={{ color: "#ef4444" }}>
            {errorMessage || "Transcription failed. Try again."}
          </p>
        ) : pipelineStatus === "complete" && segments.length === 0 ? (
          <p className="text-center mt-8" style={{ color: "#aaa" }}>
            Press play or scrub the video to reveal the translated transcript in sync.
          </p>
        ) : segments.length === 0 ? (
          <p className="text-center mt-8" style={{ color: "#aaa" }}>
            Select a video and click Transcribe.
          </p>
        ) : (
          segments.map((seg) => (
            <div
              key={seg.id}
              ref={seg.isActive ? activeRef : null}
              className="flex flex-col gap-0.5 rounded-lg px-2 py-1.5 transition-all"
              style={{
                background: seg.isActive ? "rgba(255,106,0,0.09)" : "transparent",
                borderLeft: seg.isActive ? "3px solid var(--orange)" : "3px solid transparent",
              }}
            >
              <div className="flex items-baseline gap-2">
                {seg.speaker && (
                  <span className="text-xs font-black uppercase tracking-wide" style={{ color: "var(--gold)" }}>
                    {seg.speaker}
                  </span>
                )}
                {seg.timestamp && (
                  <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                    {seg.timestamp}{seg.endTimestamp ? `-${seg.endTimestamp}` : ""}
                  </span>
                )}
              </div>
              <p style={{ color: seg.isFinal ? "#111111" : "var(--text-secondary)" }}>
                {seg.text}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
