"use client";

import { useEffect, useRef, useState } from "react";

export type TranscriptSegment = {
  id: string;
  speaker?: string;
  text: string;
  timestamp?: string;
  isFinal: boolean;
};

// Placeholder segments — replace with real SSE/WebSocket feed later
const PLACEHOLDER: TranscriptSegment[] = [
  {
    id: "1",
    speaker: "Reporter",
    text: "How do you feel about tonight's performance?",
    timestamp: "0:12",
    isFinal: true,
  },
  {
    id: "2",
    speaker: "Player",
    text: "I mean, we came out strong. The whole team bought in from tip-off.",
    timestamp: "0:18",
    isFinal: true,
  },
];

export default function TranscriptionPanel() {
  const [segments] = useState<TranscriptSegment[]>(PLACEHOLDER);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom as new segments arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [segments]);

  return (
    <div className="flex flex-col h-full rounded-xl border border-[#2e2e2e] bg-[#1a1a1a] overflow-hidden">
      {/* Panel header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2e2e2e]">
        <span className="text-xs font-semibold text-[#888] uppercase tracking-wider">
          Live Transcription
        </span>
        <span className="flex items-center gap-1.5 text-xs text-[#555]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#2e2e2e]" />
          Waiting
        </span>
      </div>

      {/* Scrollable transcript */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 text-sm">
        {segments.length === 0 ? (
          <p className="text-[#555] text-center mt-8">
            Transcription will appear here…
          </p>
        ) : (
          segments.map((seg) => (
            <div key={seg.id} className="flex flex-col gap-0.5">
              <div className="flex items-baseline gap-2">
                {seg.speaker && (
                  <span className="text-xs font-semibold text-blue-400 shrink-0">
                    {seg.speaker}
                  </span>
                )}
                {seg.timestamp && (
                  <span className="text-xs text-[#555]">{seg.timestamp}</span>
                )}
              </div>
              <p
                className={
                  seg.isFinal ? "text-[#f0f0f0]" : "text-[#888] italic"
                }
              >
                {seg.text}
              </p>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
