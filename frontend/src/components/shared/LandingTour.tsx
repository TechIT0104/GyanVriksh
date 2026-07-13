import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTour } from "../../store/tour";
import ThreeNetwork from "./ThreeNetwork";
import SacredTree from "./SacredTree";
import MissMinutes from "./MissMinutes";

interface Chapter {
  no: string;
  tag: string;
  title: string;
  body: string;
  treeScale: number;
  treeOpacity: number;
}

const CH: Chapter[] = [
  {
    no: "01", tag: "The Problem",
    title: "A knowledge cliff is coming",
    body: "Across India's refineries and chemical plants, the engineers who hold decades of hard-won repair wisdom are retiring. When they walk out, their knowledge walks out with them — undocumented, unrecorded, gone. Manuals never captured it.",
    treeScale: 0.7, treeOpacity: 0.35,
  },
  {
    no: "02", tag: "The Idea",
    title: "One mind you can simply ask",
    body: "GyanVriksh — the tree of knowledge. What if every SOP, every work order, every incident, and every veteran's spoken insight lived in a single intelligence that any worker could ask — in plain English, Hindi, or Hinglish?",
    treeScale: 0.92, treeOpacity: 0.6,
  },
  {
    no: "03", tag: "How We Built It",
    title: "A living timeline of everything",
    body: "A fine-tuned NER model reads industrial documents. A knowledge graph links equipment, people, failures and regulations. Hybrid retrieval finds the truth — then the answer is generated with citations, never guessed.",
    treeScale: 1.05, treeOpacity: 0.8,
  },
  {
    no: "04", tag: "Why It Works",
    title: "Grounded, preserved, private",
    body: "Every claim is sourced to a document and page. Nothing is hallucinated. Retiring experts are recorded before they leave. And it all runs on-premise — your plant's data never touches the cloud.",
    treeScale: 1.15, treeOpacity: 1,
  },
  {
    no: "05", tag: "Begin",
    title: "Explore your plant's Sacred Timeline",
    body: "Decades of knowledge, one question away. Step inside.",
    treeScale: 1.25, treeOpacity: 1,
  },
];

const DURATION = 9000;

export default function LandingTour() {
  const [i, setI] = useState(0);
  const [paused, setPaused] = useState(false);
  const finish = useTour((s) => s.finish);
  const navigate = useNavigate();
  const ch = CH[i];
  const last = i === CH.length - 1;

  function enter() { finish(); navigate("/dashboard"); }

  // auto-advance the story
  useEffect(() => {
    if (paused || last) return;
    const t = setTimeout(() => setI((v) => Math.min(v + 1, CH.length - 1)), DURATION);
    return () => clearTimeout(t);
  }, [i, paused, last]);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-[#040507]"
      onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
      <ThreeNetwork />

      {/* the tree grows across chapters — the sacred timeline motif */}
      <div className="absolute inset-0 flex items-center justify-end pr-[6vw] pointer-events-none">
        <div className="transition-all duration-[1400ms] ease-out"
          style={{ transform: `scale(${ch.treeScale})`, opacity: ch.treeOpacity }}>
          <SacredTree className="w-[min(760px,60vw)]" />
        </div>
      </div>
      <div className="absolute inset-0 pointer-events-none"
        style={{ background: "radial-gradient(120% 90% at 20% 40%, rgba(4,5,7,0.92), rgba(4,5,7,0.55) 45%, rgba(4,5,7,0.2))" }} />
      <div className="absolute inset-0 bg-gradient-to-t from-[#040507] via-transparent to-[#040507]/60 pointer-events-none" />

      {/* Skip */}
      <button onClick={enter}
        className="absolute top-6 right-6 z-20 mono text-xs uppercase tracking-widest text-brass-400/70 hover:text-amber-400 transition-colors">
        Skip intro →
      </button>

      {/* narrator */}
      <div className="absolute top-5 left-6 z-20 flex items-center gap-2">
        <MissMinutes className="w-10 h-10 object-contain" />
        <span className="mono text-[10px] uppercase tracking-widest text-brass-400/60">Narrated by Miss Minutes</span>
      </div>

      {/* chapter content */}
      <div className="relative z-10 h-full flex flex-col justify-center pl-[8vw] max-w-3xl">
        <div key={i} className="animate-fade-up">
          <div className="mono text-sm text-amber-400 tracking-[0.3em] uppercase mb-3">
            Chapter {ch.no} <span className="text-brass-400/40">//</span> {ch.tag}
          </div>
          <h1 className="text-5xl md:text-6xl font-bold leading-[1.05] mb-6 gradient-text max-w-2xl">
            {ch.title}
          </h1>
          <p className="text-lg md:text-xl text-cream/80 leading-relaxed max-w-xl">{ch.body}</p>

          {last && (
            <button onClick={enter}
              className="btn-gold mt-8 px-10 py-3 text-base glow-gold animate-pulse-ring">
              Enter GyanVriksh →
            </button>
          )}
        </div>
      </div>

      {/* sacred-timeline scrubber */}
      <div className="absolute bottom-0 left-0 right-0 z-20 px-[8vw] pb-6">
        <div className="flex items-center gap-4">
          <button onClick={() => setPaused((p) => !p)}
            className="mono text-xs text-amber-400 hover:text-amber-300 w-6">
            {paused ? "▶" : "❚❚"}
          </button>
          <div className="flex-1 relative flex items-center">
            {/* the timeline line */}
            <div className="absolute left-0 right-0 h-px bg-brass-400/25" />
            <div className="absolute left-0 h-px bg-amber-400 transition-all duration-500"
              style={{ width: `${(i / (CH.length - 1)) * 100}%` }} />
            {/* chapter nodes */}
            <div className="relative flex justify-between w-full">
              {CH.map((c, idx) => (
                <button key={idx} onClick={() => setI(idx)}
                  className="flex flex-col items-center gap-2 group"
                  style={{ transform: "translateY(-1px)" }}>
                  <span className={`w-3 h-3 rounded-full border transition-all ${
                    idx <= i ? "bg-amber-400 border-amber-300 shadow-[0_0_10px_rgba(249,134,26,0.7)]"
                             : "bg-[#040507] border-brass-400/40 group-hover:border-amber-400"}`} />
                  <span className={`mono text-[9px] uppercase tracking-wider hidden sm:block ${
                    idx === i ? "text-amber-400" : "text-brass-400/40"}`}>{c.tag}</span>
                </button>
              ))}
            </div>
          </div>
          {/* auto-advance progress bar for current chapter */}
          {!last && (
            <div className="w-24 h-px bg-brass-400/25 relative overflow-hidden">
              <div key={`${i}-${paused}`} className="absolute inset-y-0 left-0 bg-amber-400"
                style={{ animation: paused ? "none" : `chapter-fill ${DURATION}ms linear forwards` }} />
            </div>
          )}
        </div>
      </div>

      <style>{`@keyframes chapter-fill { from { width: 0%; } to { width: 100%; } }`}</style>
    </div>
  );
}
