"use client";

import { useMemo, useState, useEffect, useRef } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type StatEvent = {
  segment_id: number;
  timestamp_start: number;
  timestamp_end: number;
  player_name: string;
  stat_category: string;
  mentioned_value: string;
  highlight_text: string;
  player_card: {
    name: string;
    aliases?: string[];
    nation?: string;
    club?: string;
    position?: string;
    age?: number;
    caps?: number;
    goals_international?: number;
    tournament_goals?: number;
    tournament_assists?: number;
    tournament_appearances?: number;
    tournament_minutes?: number;
    tournament_yellow_cards?: number;
    tournament_red_cards?: number;
    club_season_goals?: number;
    club_season_assists?: number;
    market_value_m?: number;
  } | null;
  gemini_extraction?: {
    entity_type: string;
    context: string;
    confidence: number;
  } | null;
};

type Props = {
  statEvents: StatEvent[];
  currentTime: number;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const NATION_FLAGS: Record<string, string> = {
  Argentina: "🇦🇷",
  France: "🇫🇷",
  Brazil: "🇧🇷",
  England: "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
  Portugal: "🇵🇹",
  Spain: "🇪🇸",
  Germany: "🇩🇪",
  Norway: "🇳🇴",
  USA: "🇺🇸",
  Italy: "🇮🇹",
  Netherlands: "🇳🇱",
  Belgium: "🇧🇪",
  Uruguay: "🇺🇾",
  Colombia: "🇨🇴",
  Mexico: "🇲🇽",
};

const POSITION_LABELS: Record<string, string> = {
  FW: "Forward",
  ST: "Striker",
  LW: "Left Wing",
  RW: "Right Wing",
  AM: "Att. Midfield",
  MF: "Midfielder",
  CM: "Central Mid",
  DM: "Def. Midfield",
  DF: "Defender",
  CB: "Centre-Back",
  LB: "Left-Back",
  RB: "Right-Back",
  GK: "Goalkeeper",
};

const CATEGORY_ICONS: Record<string, string> = {
  goals: "⚽",
  assists: "🅰️",
  saves: "🧤",
  tackles: "🦵",
  yellow_cards: "🟡",
  red_cards: "🔴",
  minutes_played: "⏱️",
  shots_on_target: "🎯",
  general: "📊",
};

function getFlag(nation?: string): string {
  if (!nation) return "🏳️";
  return NATION_FLAGS[nation] ?? "🏳️";
}

function getPositionLabel(pos?: string): string {
  if (!pos) return "";
  return POSITION_LABELS[pos] ?? pos;
}

function getCategoryIcon(cat: string): string {
  return CATEGORY_ICONS[cat] ?? "📊";
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatPill({ label, value, icon }: { label: string; value: string | number; icon?: string }) {
  return (
    <div
      className="flex flex-col items-center gap-0.5 px-2.5 py-1.5 rounded-lg"
      style={{
        background: "rgba(255, 255, 255, 0.06)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
      }}
    >
      {icon && <span className="text-xs">{icon}</span>}
      <span
        className="text-sm font-black tabular-nums"
        style={{
          background: "linear-gradient(135deg, #fff, #f5b800)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}
      >
        {value}
      </span>
      <span className="text-[9px] font-semibold uppercase tracking-wider" style={{ color: "rgba(255,255,255,0.5)" }}>
        {label}
      </span>
    </div>
  );
}

function GeminiBadge({ confidence }: { confidence: number }) {
  return (
    <div
      className="flex items-center gap-1 px-2 py-0.5 rounded-full"
      style={{
        background: "rgba(66, 133, 244, 0.15)",
        border: "1px solid rgba(66, 133, 244, 0.3)",
      }}
    >
      <span className="text-[9px]">✨</span>
      <span className="text-[9px] font-bold tracking-wide" style={{ color: "rgba(66, 133, 244, 0.9)" }}>
        GEMINI NER
      </span>
      <span className="text-[9px] font-medium" style={{ color: "rgba(255,255,255,0.4)" }}>
        {(confidence * 100).toFixed(0)}%
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function StatCardOverlay({ statEvents, currentTime }: Props) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const lastEventIdRef = useRef<number | null>(null);

  // Find the active stat event for the current playback time
  const activeEvent = useMemo(() => {
    // Add a small buffer (0.5s) before the event to pre-trigger
    return statEvents.find(
      (ev) => currentTime >= ev.timestamp_start - 0.3 && currentTime < ev.timestamp_end + 0.5
    ) ?? null;
  }, [statEvents, currentTime]);

  // Animate in/out based on active event
  useEffect(() => {
    if (activeEvent) {
      if (lastEventIdRef.current !== activeEvent.segment_id) {
        // New event — animate in
        setIsExiting(false);
        setIsVisible(false);
        // Small delay to trigger CSS transition
        const timer = setTimeout(() => setIsVisible(true), 50);
        lastEventIdRef.current = activeEvent.segment_id;
        return () => clearTimeout(timer);
      }
    } else if (lastEventIdRef.current !== null) {
      // Event ended — animate out
      setIsExiting(true);
      const timer = setTimeout(() => {
        setIsVisible(false);
        setIsExiting(false);
        lastEventIdRef.current = null;
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [activeEvent]);

  if (!activeEvent && !isExiting) return null;

  const event = activeEvent ?? statEvents.find((ev) => ev.segment_id === lastEventIdRef.current);
  if (!event) return null;

  const card = event.player_card;
  const gemini = event.gemini_extraction;

  return (
    <div
      id="stat-card-overlay"
      className="absolute bottom-20 left-4 z-20 pointer-events-none select-none"
      style={{
        maxWidth: "340px",
        opacity: isVisible && !isExiting ? 1 : 0,
        transform: isVisible && !isExiting ? "translateY(0) scale(1)" : "translateY(16px) scale(0.96)",
        transition: "opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1), transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      <div
        className="rounded-2xl overflow-hidden"
        style={{
          background: "rgba(12, 12, 14, 0.85)",
          backdropFilter: "blur(24px) saturate(180%)",
          WebkitBackdropFilter: "blur(24px) saturate(180%)",
          border: "1.5px solid rgba(255, 255, 255, 0.1)",
          boxShadow: `
            0 20px 60px rgba(0, 0, 0, 0.6),
            0 0 0 1px rgba(255, 106, 0, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.05),
            0 0 40px rgba(255, 106, 0, 0.08)
          `,
        }}
      >
        {/* Header gradient accent bar */}
        <div
          style={{
            height: "3px",
            background: "linear-gradient(90deg, #ff6a00, #f5b800, #ff6a00)",
            backgroundSize: "200% auto",
            animation: "stat-card-shimmer 2s ease-in-out infinite",
          }}
        />

        {/* Player header */}
        <div className="flex items-center gap-3 px-4 pt-3 pb-2">
          {/* Player initial avatar */}
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center text-lg font-black shrink-0"
            style={{
              background: "linear-gradient(135deg, #ff6a00, #f5b800)",
              color: "#fff",
              boxShadow: "0 4px 12px rgba(255, 106, 0, 0.3)",
            }}
          >
            {card?.name?.charAt(0) ?? "?"}
          </div>

          <div className="flex flex-col min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-black text-white truncate">{card?.name ?? event.player_name}</span>
              <span className="text-sm shrink-0">{getFlag(card?.nation)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              {card?.position && (
                <span
                  className="text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
                  style={{
                    background: "rgba(255, 106, 0, 0.2)",
                    color: "#ff6a00",
                  }}
                >
                  {getPositionLabel(card.position)}
                </span>
              )}
              {card?.club && (
                <span className="text-[10px] font-medium truncate" style={{ color: "rgba(255,255,255,0.5)" }}>
                  {card.club}
                </span>
              )}
            </div>
          </div>

          {/* Category icon */}
          <div className="ml-auto shrink-0 text-xl" title={event.stat_category}>
            {getCategoryIcon(event.stat_category)}
          </div>
        </div>

        {/* Context quote */}
        <div className="px-4 pb-2">
          <p
            className="text-[11px] italic leading-relaxed"
            style={{
              color: "rgba(255, 255, 255, 0.55)",
              borderLeft: "2px solid rgba(245, 184, 0, 0.4)",
              paddingLeft: "8px",
            }}
          >
            &ldquo;{event.highlight_text}&rdquo;
          </p>
        </div>

        {/* Stats grid */}
        {card && (
          <div className="px-4 pb-3">
            <div className="grid grid-cols-4 gap-1.5">
              {card.tournament_goals !== undefined && (
                <StatPill label="Goals" value={card.tournament_goals} icon="⚽" />
              )}
              {card.tournament_assists !== undefined && (
                <StatPill label="Assists" value={card.tournament_assists} icon="🅰️" />
              )}
              {card.tournament_appearances !== undefined && (
                <StatPill label="Apps" value={card.tournament_appearances} icon="🏟️" />
              )}
              {card.tournament_minutes !== undefined && (
                <StatPill label="Mins" value={card.tournament_minutes} icon="⏱️" />
              )}
            </div>

            {/* Secondary stats row */}
            <div className="grid grid-cols-3 gap-1.5 mt-1.5">
              {card.goals_international !== undefined && (
                <StatPill label="Intl Goals" value={card.goals_international} icon="🌍" />
              )}
              {card.caps !== undefined && <StatPill label="Caps" value={card.caps} icon="🏅" />}
              {card.club_season_goals !== undefined && (
                <StatPill label="Club Goals" value={card.club_season_goals} icon="🏆" />
              )}
            </div>
          </div>
        )}

        {/* Gemini badge footer */}
        {gemini && (
          <div
            className="flex items-center justify-between px-4 py-2"
            style={{
              borderTop: "1px solid rgba(255, 255, 255, 0.06)",
              background: "rgba(0, 0, 0, 0.2)",
            }}
          >
            <GeminiBadge confidence={gemini.confidence} />
            <span className="text-[9px] font-medium" style={{ color: "rgba(255,255,255,0.25)" }}>
              {gemini.entity_type.replace(/_/g, " ")}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
