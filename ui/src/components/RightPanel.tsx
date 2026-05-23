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
  onTranscribe: () => void;
};

export default function RightPanel({
  dubLanguage,
  onDubLanguageChange,
  segments,
  pipelineStatus,
  inferenceTime,
  selectedVideo,
  onTranscribe,
}: Props) {
  const canTranscribe = selectedVideo && pipelineStatus !== "processing";

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
          onClick={onTranscribe}
          disabled={!canTranscribe}
          className="px-3 py-1.5 rounded-lg text-xs font-black uppercase tracking-widest transition-all"
          style={{
            background: canTranscribe
              ? "linear-gradient(90deg, var(--orange), var(--gold))"
              : "#e5e5e5",
            color: canTranscribe ? "#fff" : "#aaa",
            cursor: canTranscribe ? "pointer" : "not-allowed",
          }}
        >
          {pipelineStatus === "processing" ? "Processing…" : "Transcribe"}
        </button>
      </div>

      <div className="flex-1 min-h-0">
        <TranscriptionPanel segments={segments} pipelineStatus={pipelineStatus} inferenceTime={inferenceTime} />
      </div>

      <DubSelector selected={dubLanguage} onChange={onDubLanguageChange} />
    </div>
  );
}
