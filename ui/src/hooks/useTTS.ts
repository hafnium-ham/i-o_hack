"use client";

import { useEffect, useRef, useState, useCallback } from "react";

type SpeechState = "idle" | "speaking" | "paused";

const MALE_HINTS = [
  "male", "man", "guy",
  // macOS
  "alex", "fred", "daniel", "gordon", "ralph", "bruce", "tom",
  // Windows
  "david", "mark", "richard", "george", "james", "peter", "paul",
  // Spanish
  "jorge", "diego", "carlos", "miguel",
  // German
  "stefan", "markus", "hans", "otto",
];

function pickMaleVoice(langPrefix: string): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();
  const langVoices = voices.filter(v => v.lang.startsWith(langPrefix));
  console.log(`[TTS] available ${langPrefix} voices:`, langVoices.map(v => v.name));
  const picked = langVoices.find(v => MALE_HINTS.some(h => v.name.toLowerCase().includes(h))) ?? langVoices[0] ?? null;
  console.log(`[TTS] picked:`, picked?.name);
  return picked;
}

export function useTTS() {
  const [isMuted, setIsMuted] = useState(false);
  const [speechState, setSpeechState] = useState<SpeechState>("idle");
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const voicesReadyRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const synth = window.speechSynthesis;
    const onVoicesChanged = () => { voicesReadyRef.current = true; };
    synth.addEventListener("voiceschanged", onVoicesChanged);
    if (synth.getVoices().length > 0) voicesReadyRef.current = true;
    return () => synth.removeEventListener("voiceschanged", onVoicesChanged);
  }, []);

  const stop = useCallback(() => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setSpeechState("idle");
    }
  }, []);

  const speak = useCallback((text: string, lang: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;

    window.speechSynthesis.cancel();

    if (isMuted || !text) {
      setSpeechState("idle");
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utteranceRef.current = utterance;

    let langPrefix = "en";
    if (lang === "en") { utterance.lang = "en-US"; langPrefix = "en"; }
    else if (lang === "es") { utterance.lang = "es-ES"; langPrefix = "es"; }
    else if (lang === "de") { utterance.lang = "de-DE"; langPrefix = "de"; }
    else { utterance.lang = lang; langPrefix = lang.slice(0, 2); }

    utterance.voice = pickMaleVoice(langPrefix);

    utterance.onstart = () => setSpeechState("speaking");
    utterance.onend = () => setSpeechState("idle");
    utterance.onerror = () => setSpeechState("idle");

    window.speechSynthesis.speak(utterance);
  }, [isMuted]);

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

  return { isMuted, toggleMute, speak, stop, speechState };
}
