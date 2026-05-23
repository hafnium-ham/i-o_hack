"use client";

import { useState } from "react";
import VideoPlayer from "@/components/VideoPlayer";
import RightPanel from "@/components/RightPanel";
import { type DubLanguage } from "@/components/DubSelector";

export default function Home() {
  const [dubLanguage, setDubLanguage] = useState<DubLanguage>("en");

  return (
    <div className="flex h-full" style={{ background: "#ffffff" }}>
      {/* Left: Video */}
      <div className="flex flex-col flex-1 min-w-0 p-4">
        {/* dubLanguage passed here when audio track switching is wired */}
        <VideoPlayer dubLanguage={dubLanguage} />
      </div>

      {/* Right: Panel */}
      <div className="w-[420px] shrink-0 flex flex-col">
        <RightPanel dubLanguage={dubLanguage} onDubLanguageChange={setDubLanguage} />
      </div>
    </div>
  );
}
