"use client";

import VideoPlayer from "@/components/VideoPlayer";
import RightPanel from "@/components/RightPanel";

export default function Home() {
  return (
    <div className="flex h-full" style={{ background: "var(--bg)" }}>
      {/* Left: Video */}
      <div className="flex flex-col flex-1 min-w-0 p-4">
        <VideoPlayer />
      </div>

      {/* Right: Panel */}
      <div className="w-[420px] shrink-0 flex flex-col">
        <RightPanel />
      </div>
    </div>
  );
}
