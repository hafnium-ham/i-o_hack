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
        // Data-URL thumbnails are generated client-side from the local video element.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={thumb} alt="" className="w-full h-full object-cover" />
      ) : (
        <div className="w-full h-full flex items-center justify-center" style={{ background: "#e5e5e5" }}>
          <svg className="opacity-40" width="20" height="20" viewBox="0 0 24 24" fill="#333">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      )}
    </>
  );
}

type Props = {
  onVideoSelect?: (filename: string) => void;
  onTimeChange?: (seconds: number) => void;
  onPlayChange?: (isPlaying: boolean) => void;
  activeSegmentText?: string;
  volume?: number;
};

export default function VideoPlayer({
  onVideoSelect,
  onTimeChange,
  onPlayChange,
  activeSegmentText,
  volume = 1.0,
}: Props) {
  const [videos, setVideos] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const mainVideoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    fetch("/api/videos")
      .then((r) => r.json())
      .then((files: string[]) => {
        setVideos(files);
        if (files.length > 0) {
          setSelected(`/${files[0]}`);
          onVideoSelect?.(files[0]);
          onTimeChange?.(0);
        }
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (mainVideoRef.current) {
      mainVideoRef.current.volume = volume;
    }
  }, [volume]);

  const handleSelect = (file: string) => {
    setSelected(`/${file}`);
    onVideoSelect?.(file);
    onTimeChange?.(0);
  };

  return (
    <div className="flex flex-col h-full gap-3">
      <div
        className="flex-1 rounded-2xl overflow-hidden relative group"
        style={{
          border: "3px solid var(--orange)",
          boxShadow: "0 0 40px rgba(255,106,0,0.25), 6px 6px 0px var(--gold)",
        }}
      >
        {selected ? (
          <>
            <video
              key={selected}
              ref={mainVideoRef}
              src={selected}
              controls
              preload="metadata"
              onLoadedMetadata={(event) => onTimeChange?.(event.currentTarget.currentTime)}
              onTimeUpdate={(event) => onTimeChange?.(event.currentTarget.currentTime)}
              onSeeked={(event) => onTimeChange?.(event.currentTarget.currentTime)}
              onPlay={() => onPlayChange?.(true)}
              onPause={() => onPlayChange?.(false)}
              onEnded={() => onPlayChange?.(false)}
              className="w-full h-full object-contain"
              style={{ background: "#000" }}
            />
            {activeSegmentText && (
              <div
                className="absolute bottom-16 left-1/2 transform -translate-x-1/2 w-11/12 max-w-2xl px-5 py-3 rounded-xl text-center select-none pointer-events-none transition-all duration-300"
                style={{
                  background: "rgba(10, 10, 10, 0.8)",
                  backdropFilter: "blur(12px)",
                  border: "1.5px solid rgba(255, 255, 255, 0.15)",
                  boxShadow: "0 10px 30px rgba(0, 0, 0, 0.5), 0 0 15px rgba(255, 106, 0, 0.1)",
                }}
              >
                <p className="text-white text-base md:text-lg font-black tracking-wide leading-relaxed drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]">
                  {activeSegmentText}
                </p>
              </div>
            )}
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center" style={{ background: "#f5f5f5" }}>
            <p className="text-sm" style={{ color: "#aaa" }}>Loading…</p>
          </div>
        )}
      </div>

      {videos.length > 0 && (
        <div className="flex gap-3 overflow-x-auto pb-1">
          {videos.map((file) => {
            const src = `/${file}`;
            const isActive = selected === src;
            return (
              <button
                key={file}
                onClick={() => handleSelect(file)}
                className="shrink-0 w-36 h-20 rounded-xl overflow-hidden transition-all"
                style={{
                  outline: isActive ? "3px solid var(--orange)" : "none",
                  boxShadow: isActive ? "0 0 16px rgba(255,106,0,0.4), 3px 3px 0 var(--gold)" : "none",
                }}
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
