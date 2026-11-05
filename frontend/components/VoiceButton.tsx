"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Mic, MicOff } from "lucide-react";

import { cn } from "./ui";

type RecognitionResult = {
  results: { [index: number]: { [index: number]: { transcript: string } } };
};

type Recognition = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start(): void;
  stop(): void;
  onresult: ((event: RecognitionResult) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
};

type RecognitionConstructor = new () => Recognition;

function getConstructor(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const scope = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return scope.SpeechRecognition ?? scope.webkitSpeechRecognition ?? null;
}

const subscribeSupport = () => () => {};
const getSupportSnapshot = () => getConstructor() !== null;
const getServerSnapshot = () => false;

export function VoiceButton({
  onTranscript,
  disabled,
}: {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<Recognition | null>(null);
  // Feature detection is an external, stable value; no effect or render setState.
  const supported = useSyncExternalStore(
    subscribeSupport,
    getSupportSnapshot,
    getServerSnapshot,
  );

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      recognitionRef.current = null;
    };
  }, []);

  if (!supported) {
    return (
      <button
        type="button"
        disabled
        aria-label="Voice input is not supported in this browser"
        title="Voice input is not supported in this browser"
        className="rounded-lg p-2 text-muted-foreground/50"
      >
        <MicOff size={16} aria-hidden />
      </button>
    );
  }

  function toggle() {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }
    const Constructor = getConstructor();
    if (!Constructor) return;
    const recognition = new Constructor();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript;
      if (transcript) onTranscript(transcript.trim());
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={disabled}
      aria-pressed={listening}
      aria-label={listening ? "Stop dictation" : "Dictate a question"}
      title={listening ? "Stop dictation" : "Dictate a question"}
      className={cn(
        "rounded-lg p-2 transition-colors disabled:opacity-50",
        listening
          ? "bg-danger/10 text-danger"
          : "text-muted-foreground hover:bg-muted hover:text-foreground",
      )}
    >
      <Mic size={16} aria-hidden />
    </button>
  );
}
