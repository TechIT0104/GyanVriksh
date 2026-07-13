import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { get } from "../api/client";
import { useAuth } from "../store/auth";
import ChatInterface from "../components/Copilot/ChatInterface";
import Icon from "../components/shared/Icon";

/** Field-worker mobile experience: big touch targets, voice-first, QR-aware.
 *  Scanning an equipment QR opens /mobile?tag=P-101 and offers one-tap
 *  questions about that machine — no typing, answers can be read aloud. */
export default function MobileField() {
  const { name, logout } = useAuth();
  const [params] = useSearchParams();
  const tag = (params.get("tag") || "").toUpperCase();
  const [view, setView] = useState<"home" | "ask">(tag ? "home" : "home");
  const [pendingQ, setPendingQ] = useState<string | undefined>();
  const { data: alerts } = useQuery({ queryKey: ["alerts"], queryFn: () => get("/maintenance/alerts"), retry: false });
  const online = navigator.onLine;

  function ask(q: string) { setPendingQ(q); setView("ask"); }

  const tagQuestions = tag ? [
    `What is the correct procedure to service ${tag}?`,
    `Why does ${tag} fail? Show its history`,
    `What was the last work order on ${tag}?`,
    `What must I check before working on ${tag}?`,
  ] : [];
  const genericQuestions = [
    "What must be checked before confined space entry?",
    "Emergency shutdown procedure for a pump",
    "Latest safety alerts I should know",
  ];

  if (view === "ask") {
    return (
      <div className="h-screen flex flex-col bg-navy-900">
        <div className="p-3 border-b border-brass-400/25 flex items-center gap-3">
          <button onClick={() => { setView("home"); setPendingQ(undefined); }} className="text-amber-400 text-2xl leading-none">‹</button>
          <span className="font-semibold">Ask GyanVriksh</span>
          {!online && <span className="badge bg-red-900 text-red-300 ml-auto">Offline · cached</span>}
        </div>
        <div className="flex-1 overflow-hidden"><ChatInterface compact initialQuery={pendingQ} /></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-navy-900 p-4 max-w-md mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <img src="/logo.png" className="w-9 h-9 rounded-full ring-1 ring-brass-400/40" alt="" />
          <span className="font-bold gradient-text">GyanVriksh Field</span>
        </div>
        <button onClick={logout} className="text-xs text-slate-400">Sign out</button>
      </div>
      <div className="text-sm text-brass-300/70 mb-4">Namaste, {name}</div>

      {tag && (
        <div className="card mb-4 border-amber-400/50">
          <div className="kicker mb-1">Scanned Equipment</div>
          <div className="text-2xl font-bold text-amber-400 mono">{tag}</div>
          <div className="text-xs text-slate-400 mt-1">Tap a question — the answer can be read aloud.</div>
          <div className="mt-3 space-y-2">
            {tagQuestions.map((q) => (
              <button key={q} onClick={() => ask(q)}
                className="w-full text-left text-sm card !p-3 hover:border-amber-400 flex items-center gap-2">
                <Icon name="ask" className="w-4 h-4 text-amber-400 shrink-0" /> {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <button onClick={() => ask("")}
        className="w-full card text-left mb-4 hover:border-amber-400 flex items-center gap-4 !p-5">
        <span className="grid place-items-center w-12 h-12 rounded-full bg-amber-400/15 text-amber-400 shrink-0">
          <Icon name="mic" className="w-6 h-6" />
        </span>
        <div>
          <div className="font-semibold text-lg">Ask a question</div>
          <div className="text-xs text-slate-400">Voice or text · answers read aloud · works offline for recent queries</div>
        </div>
      </button>

      {!tag && (
        <div className="space-y-2 mb-5">
          <div className="kicker">Quick questions</div>
          {genericQuestions.map((q) => (
            <button key={q} onClick={() => ask(q)}
              className="w-full text-left text-sm card !p-3 hover:border-amber-400 flex items-center gap-2">
              <Icon name="ask" className="w-4 h-4 text-amber-400 shrink-0" /> {q}
            </button>
          ))}
        </div>
      )}

      <h3 className="text-sm font-semibold text-amber-400 mb-2">Active Alerts</h3>
      <div className="space-y-2">
        {(alerts ?? []).slice(0, 5).map((a: any) => (
          <div key={a.id} className="card !p-3 text-sm">
            <span className="badge bg-red-900 text-red-300 mr-2">{a.equipment_tag}</span>
            {a.message}
          </div>
        ))}
        {!alerts?.length && <div className="text-slate-500 text-sm">No active alerts</div>}
      </div>
    </div>
  );
}
