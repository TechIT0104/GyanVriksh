import { useCallback, useEffect, useState } from "react";

/** Text-to-speech readback of answers — so a technician can simply listen.
 *  Uses the browser SpeechSynthesis API (no dependency, works offline). */
export function useSpeech() {
  const [speaking, setSpeaking] = useState(false);
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;

  const speak = useCallback((text: string, language = "en") => {
    if (!supported || !text) return;
    window.speechSynthesis.cancel();
    // strip inline citations and markdown so it reads naturally
    const clean = text
      .replace(/\[Doc:[^\]]*\]/g, "")
      .replace(/[*_`#>]/g, "")
      .trim();
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = language === "hi" ? "hi-IN" : "en-IN";
    u.rate = 0.98;
    u.pitch = 1;
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(u);
  }, [supported]);

  const stop = useCallback(() => {
    if (supported) window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  // stop speech if the component unmounts
  useEffect(() => () => { if (supported) window.speechSynthesis.cancel(); }, [supported]);

  return { speak, stop, speaking, supported };
}
