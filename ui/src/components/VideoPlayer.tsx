"use client";

import { useState, useRef, KeyboardEvent } from "react";

function extractYouTubeId(input: string): string | null {
  try {
    const url = new URL(input);
    if (url.hostname === "youtu.be") return url.pathname.slice(1);
    if (url.hostname.includes("youtube.com")) {
      return url.searchParams.get("v");
    }
  } catch {
    // treat bare video IDs
    if (/^[a-zA-Z0-9_-]{11}$/.test(input.trim())) return input.trim();
  }
  return null;
}

export default function VideoPlayer() {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function loadVideo() {
    const id = extractYouTubeId(inputValue.trim());
    if (!id) {
      setError("Couldn't parse a YouTube URL or video ID.");
      return;
    }
    setError(null);
    setVideoId(id);
  }

  function handleKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") loadVideo();
  }

  return (
    <div className="flex flex-col h-full gap-3">
      {/* URL bar */}
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Paste a YouTube URL or video ID…"
          className="flex-1 rounded-lg bg-[#1a1a1a] border border-[#2e2e2e] text-[#f0f0f0] text-sm px-3 py-2 outline-none focus:border-blue-500 placeholder:text-[#555] transition-colors"
        />
        <button
          onClick={loadVideo}
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors shrink-0"
        >
          Load
        </button>
      </div>

      {error && <p className="text-red-400 text-xs">{error}</p>}

      {/* Video frame */}
      <div className="flex-1 rounded-xl overflow-hidden bg-[#1a1a1a] border border-[#2e2e2e] flex items-center justify-center">
        {videoId ? (
          <iframe
            key={videoId}
            src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0`}
            title="YouTube video"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            className="w-full h-full"
          />
        ) : (
          <div className="flex flex-col items-center gap-3 text-[#555]">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
              <path d="M21.58 7.19a2.76 2.76 0 0 0-1.94-1.95C18 5 12 5 12 5s-6 0-7.64.24a2.76 2.76 0 0 0-1.94 1.95A28.65 28.65 0 0 0 2 12a28.65 28.65 0 0 0 .42 4.81 2.76 2.76 0 0 0 1.94 1.95C6 19 12 19 12 19s6 0 7.64-.24a2.76 2.76 0 0 0 1.94-1.95A28.65 28.65 0 0 0 22 12a28.65 28.65 0 0 0-.42-4.81zM10 15V9l5.2 3-5.2 3z" />
            </svg>
            <p className="text-sm">Paste a YouTube link to get started</p>
          </div>
        )}
      </div>
    </div>
  );
}
