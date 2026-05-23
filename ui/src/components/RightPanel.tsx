"use client";

import TranscriptionPanel from "./TranscriptionPanel";
import DubSelector, { type DubLanguage } from "./DubSelector";

type Props = {
  dubLanguage: DubLanguage;
  onDubLanguageChange: (lang: DubLanguage) => void;
};

export default function RightPanel({ dubLanguage, onDubLanguageChange }: Props) {
  return (
    <div className="flex flex-col h-full p-4 gap-4" style={{ background: "#ffffff" }}>
      {/* Header */}
      <div className="flex items-center gap-2">
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
      </div>

      {/* Transcription — fills remaining space */}
      <div className="flex-1 min-h-0">
        <TranscriptionPanel />
      </div>

      {/* Dub language selector */}
      <DubSelector selected={dubLanguage} onChange={onDubLanguageChange} />
    </div>
  );
}
