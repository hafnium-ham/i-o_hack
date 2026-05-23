"use client";

import { useEffect, useRef, useState, useCallback } from "react";

type SpeechState = "idle" | "speaking" | "paused";

export function useTTS() {
  const [isMuted, setIsMuted] = useState(false);
  const [speechState, setSpeechState] = useState<SpeechState>("idle");
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Stop/cancel any current speech
  const stop = useCallback(() => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setSpeechState("idle");
    }
  }, []);

  // Speak a segment of text in a specific language
  const speak = useCallback((text: string, lang: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;

    // Stop current speech first
    window.speechSynthesis.cancel();

    if (isMuted || !text) {
      setSpeechState("idle");
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utteranceRef.current = utterance;

    // Map language code to standard locale
    if (lang === "en") utterance.lang = "en-US";
    else if (lang === "es") utterance.lang = "es-ES";
    else if (lang === "de") utterance.lang = "de-DE";
    else utterance.lang = lang;

    // Try to find a high-quality voice for the target language
    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = voices.find(v => v.lang.startsWith(utterance.lang));
    if (matchingVoice) {
      utterance.voice = matchingVoice;
    }

    // Event handlers to update state
    utterance.onstart = () => setSpeechState("speaking");
    utterance.onend = () => setSpeechState("idle");
    utterance.onerror = () => setSpeechState("idle");

    window.speechSynthesis.speak(utterance);
  }, [isMuted]);

  // Handle cleanup on unmount
  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const toggleMute = useCallback(() => {
    setIsMuted(prev => {
      const next = !prev;
      if (next && typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      return next;
    });
  }, []);

  return {
    isMuted,
    toggleMute,
    speak,
    stop,
    speechState
  };
}
