"use client";

import TranscriptionPanel from "./TranscriptionPanel";

export default function RightPanel() {
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

      {/* Transcription — fills all remaining space */}
      <div className="flex-1 min-h-0">
        <TranscriptionPanel />
      </div>
    </div>
  );
}
