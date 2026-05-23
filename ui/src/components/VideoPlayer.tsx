"use client";

import { useEffect, useRef, useState } from "react";

function VideoThumbnail({ src }: { src: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [thumb, setThumb] = useState<string | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const onSeeked = () => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d")?.drawImage(video, 0, 0);
      setThumb(canvas.toDataURL("image/jpeg", 0.7));
    };

    video.addEventListener("seeked", onSeeked);
    video.addEventListener("loadeddata", () => { video.currentTime = 3; });

    return () => video.removeEventListener("seeked", onSeeked);
  }, [src]);

  return (
    <>
      <video ref={videoRef} src={src} className="hidden" preload="metadata" />
      <canvas ref={canvasRef} className="hidden" />
      {thumb ? (
        <img src={thumb} alt="" className="w-full h-full object-cover" />
      ) : (
        <div className="w-full h-full bg-[#242424] flex items-center justify-center">
          <svg className="text-[#444]" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      )}
    </>
  );
}

export default function VideoPlayer() {
  const [videos, setVideos] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/videos")
      .then((r) => r.json())
      .then((files: string[]) => {
        setVideos(files);
        if (files.length > 0) setSelected(`/${files[0]}`);
      });
  }, []);

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Main player */}
      <div className="flex-1 rounded-xl overflow-hidden bg-[#1a1a1a] border border-[#2e2e2e]">
        {selected && (
          <video
            key={selected}
            src={selected}
            controls
            className="w-full h-full object-contain"
          />
        )}
      </div>

      {/* Video strip */}
      {videos.length > 0 && (
        <div className="flex gap-3 overflow-x-auto pb-1">
          {videos.map((file) => {
            const src = `/${file}`;
            return (
              <button
                key={file}
                onClick={() => setSelected(src)}
                className={`shrink-0 w-36 h-20 rounded-lg overflow-hidden border transition-colors ${
                  selected === src
                    ? "border-blue-500"
                    : "border-[#2e2e2e] hover:border-[#444]"
                }`}
              >
                <VideoThumbnail src={src} />
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
