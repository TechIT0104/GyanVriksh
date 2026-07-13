import { useEffect, useRef, useState } from "react";
import { get, wsUrl } from "../../api/client";
import { useAuth } from "../../store/auth";
import { useHighlight } from "../../store/highlight";
import { useVoiceInput } from "../../hooks/useVoiceInput";
import MessageBubble from "./MessageBubble";
import CitationPanel from "./CitationPanel";
import Icon from "../shared/Icon";
import MissMinutes from "../shared/MissMinutes";

export interface ReasoningStep {
  step: string;
  label: string;
  state?: string;
  detail?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  confidence?: string;
  citations?: any[];
  capsules?: any[];
  related?: string[];
  steps?: ReasoningStep[];
  language?: string;
  timeMs?: number;
}

const SUGGESTIONS = [
  "What is the correct procedure for replacing the mechanical seal on P-101, and what does OISD-116 say about it?",
  "Is FI-101 accurate?",
  "Why do P-101 seals keep failing?",
  "What must be checked before confined space entry?",
  "P-101 ka seal baar baar kyun fail ho raha hai? Hindi mein batao",
];

export default function ChatInterface({ compact = false, initialQuery }: { compact?: boolean; initialQuery?: string }) {
  const token = useAuth((s) => s.token);
  const setHighlight = useHighlight((s) => s.set);
  const sentInit = useRef(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [citationDoc, setCitationDoc] = useState<{ docId: string; page: number } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { listening, toggle } = useVoiceInput((text) => setInput(text));

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // auto-send a question passed in from a QR scan or a one-tap button
  useEffect(() => {
    if (initialQuery && !sentInit.current) {
      sentInit.current = true;
      send(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  useEffect(() => {
    // Offline cache of last 50 Q&A for the mobile PWA
    if (!navigator.onLine) {
      get("/copilot/history").catch(() => {
        const cached = localStorage.getItem("gv_history");
        if (cached) {
          const h = JSON.parse(cached);
          setMessages(h.flatMap((x: any) => [
            { role: "user", text: x.query },
            { role: "assistant", text: x.answer, confidence: x.confidence, citations: x.citations },
          ]));
        }
      });
    }
  }, []);

  function send(query?: string) {
    const q = (query ?? input).trim();
    if (!q || streaming) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }, { role: "assistant", text: "" }]);
    setStreaming(true);

    const ws = new WebSocket(wsUrl("/ws/copilot/stream"));
    wsRef.current = ws;
    ws.onopen = () => ws.send(JSON.stringify({ token, query: q }));
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if ((msg.type === "meta" || msg.type === "done") && Array.isArray(msg.graph_nodes)) {
        setHighlight(msg.graph_nodes, q);
      }
      setMessages((m) => {
        const copy = [...m];
        const last = { ...copy[copy.length - 1] };
        if (msg.type === "status") {
          const steps = [...(last.steps || [])];
          const idx = steps.findIndex((s) => s.step === msg.step);
          const entry = { step: msg.step, label: msg.label, state: msg.state, detail: msg.detail };
          if (idx >= 0) steps[idx] = entry;
          else steps.push(entry);
          last.steps = steps;
        } else if (msg.type === "meta") {
          last.confidence = msg.confidence;
          last.related = msg.related_entities;
          last.language = msg.language;
        } else if (msg.type === "token") {
          last.text += msg.token;
        } else if (msg.type === "done") {
          last.citations = msg.citations;
          last.capsules = msg.knowledge_capsules;
          last.timeMs = msg.response_time_ms;
          setStreaming(false);
          ws.close();
          // cache for offline
          const hist = JSON.parse(localStorage.getItem("gv_history") || "[]");
          hist.unshift({ query: q, answer: last.text, confidence: last.confidence, citations: last.citations });
          localStorage.setItem("gv_history", JSON.stringify(hist.slice(0, 50)));
        } else if (msg.type === "error") {
          last.text = `Error: ${msg.detail}`;
          setStreaming(false);
        }
        copy[copy.length - 1] = last;
        return copy;
      });
    };
    ws.onerror = () => setStreaming(false);
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="max-w-xl mx-auto mt-8 text-center">
              <MissMinutes className="w-40 mx-auto mb-2 animate-float" />
              <div className="kicker mb-1">AI Assistant · Online</div>
              <h2 className="text-xl font-semibold gradient-text mb-1">Miss Minutes at your service</h2>
              <p className="text-sm text-amber-300/70 mb-4 max-w-md mx-auto">
                Ask me anything about Unit-3 — procedures, equipment, incidents, compliance.
                Every answer is drawn from your indexed knowledge base, with citations.
              </p>
              <div className="space-y-2">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)}
                    className="block w-full text-left text-sm card hover:border-gold-500">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <MessageBubble key={i} msg={m} onCitationClick={(docId, page) => setCitationDoc({ docId, page })} />
          ))}
          <div ref={bottomRef} />
        </div>
        <div className="p-4 border-t border-navy-600 flex gap-2">
          <button onClick={toggle}
            className={`btn-ghost grid place-items-center ${compact ? "px-5" : ""} ${listening ? "!bg-red-900/50 !border-red-500 animate-pulse text-red-300" : "text-loki-400"}`}
            title="Voice input">
            <Icon name="mic" className="w-5 h-5" />
          </button>
          <input className="input flex-1" placeholder={listening ? "Listening..." : "Ask about equipment, procedures, incidents, compliance..."}
            value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()} />
          <button className="btn-gold" onClick={() => send()} disabled={streaming}>
            {streaming ? "..." : "Ask"}
          </button>
        </div>
      </div>
      {citationDoc && <CitationPanel doc={citationDoc} onClose={() => setCitationDoc(null)} />}
    </div>
  );
}
