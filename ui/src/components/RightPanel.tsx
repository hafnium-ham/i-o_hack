"use client";

import TranscriptionPanel, { type TranscriptSegment } from "./TranscriptionPanel";
import DubSelector, { type DubLanguage } from "./DubSelector";

type PipelineStatus = "idle" | "processing" | "complete" | "error";

type Props = {
  dubLanguage: DubLanguage;
  onDubLanguageChange: (lang: DubLanguage) => void;
  segments: TranscriptSegment[];
  pipelineStatus: PipelineStatus;
  inferenceTime: number | null;
  selectedVideo: string | null;
  currentTime: number;
  languageLabel: string;
  totalSegments: number;
  errorMessage: string | null;
  isTtsMuted: boolean;
  onToggleTtsMute: () => void;
};

export default function RightPanel({
  dubLanguage,
  onDubLanguageChange,
  segments,
  pipelineStatus,
  inferenceTime,
  selectedVideo,
  currentTime,
  languageLabel,
  totalSegments,
  errorMessage,
  isTtsMuted,
  onToggleTtsMute,
}: Props) {
  return (
    <div className="flex flex-col h-full p-4 gap-4" style={{ background: "#ffffff" }}>
      <div className="flex items-center justify-between gap-2">
        <h1
          className="text-base font-black tracking-widest uppercase"
          style={{
            background: "linear-gradient(90deg, var(--orange), var(--gold))",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Scribe
        </h1>

        <button
          onClick={onToggleTtsMute}
          className="px-3 py-1.5 rounded-lg text-xs font-black uppercase tracking-widest transition-all flex items-center gap-1.5"
          style={{
            background: isTtsMuted
              ? "#e5e5e5"
              : "linear-gradient(90deg, var(--orange), var(--gold))",
            color: isTtsMuted ? "#666" : "#fff",
            cursor: "pointer",
            boxShadow: isTtsMuted ? "none" : "0 4px 12px rgba(255,106,0,0.25)",
            border: isTtsMuted ? "1px solid #ccc" : "none",
          }}
        >
          <span>{isTtsMuted ? "🔇 Voice Dub Off" : "🔊 Voice Dub On"}</span>
        </button>
      </div>

      <DubSelector selected={dubLanguage} onChange={onDubLanguageChange} />

      <div className="flex-1 min-h-0">
        <TranscriptionPanel
          segments={segments}
          pipelineStatus={pipelineStatus}
          inferenceTime={inferenceTime}
          currentTime={currentTime}
          languageLabel={languageLabel}
          totalSegments={totalSegments}
          errorMessage={errorMessage}
        />
      </div>
    </div>
  );
}
