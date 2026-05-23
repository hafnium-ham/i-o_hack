"use client";

import { useEffect, useRef } from "react";

export type TranscriptSegment = {
  id: string;
  speaker?: string;
  text: string;
  timestamp?: string;
  isFinal: boolean;
};

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

type Props = {
  segments?: TranscriptSegment[];
};

export default function TranscriptionPanel({ segments = PLACEHOLDER }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [segments]);

  return (
    <div
      className="flex flex-col h-full rounded-xl overflow-hidden"
      style={{
        border: "3px solid var(--gold)",
        background: "#ffffff",
        boxShadow: "0 0 30px rgba(245,184,0,0.15), 4px 4px 0 var(--orange)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{
          borderBottom: "3px solid var(--gold)",
          background: "#ffffff",
        }}
      >
        <span
          className="text-xs font-black uppercase tracking-widest"
          style={{ color: "var(--orange)" }}
        >
          Live Transcription
        </span>
        <span className="flex items-center gap-1.5 text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#444" }} />
          Waiting
        </span>
      </div>

      {/* Transcript */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 text-sm">
        {segments.length === 0 ? (
          <p className="text-center mt-8" style={{ color: "#aaa" }}>
            Transcription will appear here…
          </p>
        ) : (
          segments.map((seg) => (
            <div key={seg.id} className="flex flex-col gap-0.5">
              <div className="flex items-baseline gap-2">
                {seg.speaker && (
                  <span className="text-xs font-black uppercase tracking-wide" style={{ color: "var(--gold)" }}>
                    {seg.speaker}
                  </span>
                )}
                {seg.timestamp && (
                  <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                    {seg.timestamp}
                  </span>
                )}
              </div>
              <p style={{ color: seg.isFinal ? "#111111" : "var(--text-secondary)" }}>
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
