"use client";

import VideoPlayer from "@/components/VideoPlayer";
import RightPanel from "@/components/RightPanel";

export default function Home() {
  return (
    <div className="flex h-full bg-[#0f0f0f]">
      {/* Left: Video */}
      <div className="flex flex-col flex-1 min-w-0 p-4">
        <VideoPlayer />
      </div>

      {/* Divider */}
      <div className="w-px bg-[#2e2e2e] shrink-0" />

      {/* Right: Panel */}
      <div className="w-[420px] shrink-0 flex flex-col">
        <RightPanel />
      </div>
    </div>
  );
}
