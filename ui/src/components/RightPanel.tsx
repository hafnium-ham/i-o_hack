"use client";

import TranscriptionPanel from "./TranscriptionPanel";

export default function RightPanel() {
  return (
    <div className="flex flex-col h-full p-4 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-sm font-semibold text-[#f0f0f0] tracking-wide uppercase">
          SportsCast
        </h1>
        <span className="flex items-center gap-1.5 text-xs text-[#888]">
          <span className="w-2 h-2 rounded-full bg-[#2e2e2e]" />
          Offline
        </span>
      </div>

      {/* Transcription — takes remaining space */}
      <div className="flex-1 min-h-0">
        <TranscriptionPanel />
      </div>

      {/* Placeholders for later panels */}
      <div className="rounded-xl border border-[#2e2e2e] border-dashed p-4 text-center text-xs text-[#555]">
        Stats cards — coming soon
      </div>
      <div className="rounded-xl border border-[#2e2e2e] border-dashed p-3 flex items-center justify-center gap-3 text-xs text-[#555]">
        Dub language flags — coming soon
      </div>
    </div>
  );
}
