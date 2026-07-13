import ConfidenceBadge from "../shared/ConfidenceBadge";
import Icon from "../shared/Icon";
import MissMinutes from "../shared/MissMinutes";
import { useSpeech } from "../../hooks/useSpeech";
import type { ChatMessage } from "./ChatInterface";

export default function MessageBubble({ msg, onCitationClick }:
  { msg: ChatMessage; onCitationClick: (docId: string, page: number) => void }) {
  const { speak, stop, speaking, supported } = useSpeech();
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="bg-navy-700 rounded-2xl rounded-br-sm px-4 py-2 max-w-2xl">{msg.text}</div>
      </div>
    );
  }

  // Render inline [Doc: X, Page N] citations as clickable links
  const parts = msg.text.split(/(\[Doc:\s*[^,\]]+(?:,\s*Page\s*\d+)?\])/g);

  return (
    <div className="flex justify-start">
      <div className="card max-w-3xl w-full">
        <div className="flex items-center gap-2 mb-2">
          <MissMinutes className="w-7 h-7 object-contain" />
          <span className="text-gold-400 font-semibold text-sm">Miss Minutes</span>
          <span className="mono text-[10px] text-amber-400/50 uppercase">· GyanVriksh</span>
          {msg.confidence && <ConfidenceBadge level={msg.confidence} />}
          {msg.language && msg.language !== "en" && (
            <span className="badge bg-purple-900/60 text-purple-300 uppercase">{msg.language}</span>
          )}
          {msg.timeMs != null && <span className="text-xs text-slate-500">{(msg.timeMs / 1000).toFixed(1)}s</span>}
          {supported && !!msg.text && (
            <button
              onClick={() => (speaking ? stop() : speak(msg.text, msg.language))}
              title={speaking ? "Stop" : "Listen to this answer"}
              className={`ml-auto grid place-items-center w-7 h-7 rounded border border-amber-400/30 transition-colors ${speaking ? "text-amber-400 bg-amber-400/10 animate-pulse" : "text-amber-400/70 hover:text-amber-400 hover:border-amber-400/60"}`}>
              <Icon name={speaking ? "stop" : "speaker"} className="w-4 h-4" />
            </button>
          )}
        </div>

        {!!msg.steps?.length && (
          <div className="mb-3 rounded-lg border border-navy-600/70 bg-navy-900/40 p-3 space-y-1.5">
            {msg.steps.map((s, i) => {
              const done = s.state === "done";
              return (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className={`mt-0.5 shrink-0 ${done ? "text-emerald-400" : "text-gold-400"}`}>
                    {done ? "✓" : <span className="inline-block animate-spin">◠</span>}
                  </span>
                  <span className="text-slate-300">
                    <span className={done ? "" : "text-gold-300"}>{s.label}</span>
                    {s.detail && <span className="text-slate-500"> — {s.detail}</span>}
                  </span>
                </div>
              );
            })}
          </div>
        )}
        <div className="whitespace-pre-wrap text-sm leading-relaxed">
          {parts.map((p, i) => {
            const m = p.match(/\[Doc:\s*([^,\]]+)(?:,\s*Page\s*(\d+))?\]/);
            if (m) {
              return (
                <button key={i} onClick={() => onCitationClick(m[1].trim(), parseInt(m[2] || "1"))}
                  className="text-blue-400 hover:underline text-xs align-baseline">
                  {p}
                </button>
              );
            }
            return <span key={i}>{p}</span>;
          })}
          {msg.text === "" && <span className="animate-pulse">▍</span>}
        </div>
        {!!msg.capsules?.length && (
          <div className="mt-2 pt-2 border-t border-navy-600/60 text-xs text-gold-400 flex items-center gap-1.5">
            <Icon name="spark" className="w-3.5 h-3.5 shrink-0" />
            Includes expert knowledge from: {msg.capsules.map((c: any) => c.expert).join(", ")}
          </div>
        )}
        {!!msg.related?.length && (
          <div className="mt-2 flex flex-wrap gap-1">
            {msg.related.map((r) => (
              <a key={r} href={`/maintenance?tag=${r}`} className="badge bg-orange-900 text-orange-300 hover:opacity-80">{r}</a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
