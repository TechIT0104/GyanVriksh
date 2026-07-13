import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { get, post } from "../api/client";
import { useAuth } from "../store/auth";
import PageHeader from "../components/shared/PageHeader";

export default function PreservationStudio() {
  const qc = useQueryClient();
  const { name } = useAuth();
  const [expert, setExpert] = useState("Ramesh Kumar");
  const [equipment, setEquipment] = useState("P-101");
  const [session, setSession] = useState<any>(null);
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [levels, setLevels] = useState<number[]>(Array(32).fill(4));
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<any>(null);
  const analyserRef = useRef<any>(null);

  const { data: capsules } = useQuery({ queryKey: ["capsules"], queryFn: () => get("/preserve/capsules/"), retry: false });
  const { data: status } = useQuery({
    queryKey: ["ps-status", session?.session_id],
    queryFn: () => get(`/preserve/session/${session.session_id}/status`),
    enabled: !!session && !recording,
    refetchInterval: (q) => (["VERIFYING", "PUBLISHED", "ERROR"].includes((q.state.data as any)?.status) ? false : 4000),
    retry: false,
  });
  const { data: verify } = useQuery({
    queryKey: ["ps-verify", session?.session_id],
    queryFn: () => get(`/preserve/session/${session.session_id}/verify`),
    enabled: status?.status === "VERIFYING",
    retry: false,
  });

  const startSession = useMutation({
    mutationFn: () => post("/preserve/session/start", { expert_name: expert, equipment_focus: equipment }),
    onSuccess: (data) => setSession(data),
  });

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const rec = new MediaRecorder(stream);
    chunksRef.current = [];
    rec.ondataavailable = (e) => chunksRef.current.push(e.data);
    rec.start();
    mediaRef.current = rec;
    setRecording(true);
    setElapsed(0);
    timerRef.current = setInterval(() => setElapsed((t) => t + 1), 1000);

    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 64;
    ctx.createMediaStreamSource(stream).connect(analyser);
    analyserRef.current = setInterval(() => {
      const arr = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(arr);
      setLevels(Array.from(arr).map((v) => 4 + (v / 255) * 40));
    }, 80);
  }

  async function stopRecording() {
    const rec = mediaRef.current;
    if (!rec) return;
    clearInterval(timerRef.current);
    clearInterval(analyserRef.current);
    setRecording(false);
    await new Promise<void>((resolve) => {
      rec.onstop = () => resolve();
      rec.stop();
      rec.stream.getTracks().forEach((t) => t.stop());
    });
    const blob = new Blob(chunksRef.current, { type: "audio/webm" });
    const form = new FormData();
    form.append("file", blob, "recording.webm");
    await post(`/preserve/session/${session.session_id}/upload?duration_seconds=${elapsed}`, form);
    qc.invalidateQueries({ queryKey: ["ps-status", session.session_id] });
  }

  const [decisions, setDecisions] = useState<Record<number, string>>({});
  const approve = useMutation({
    mutationFn: () => post(`/preserve/session/${session.session_id}/approve`, {
      verified_by: name,
      decisions: (verify?.insights ?? []).map((_: any, i: number) => ({
        insight_index: i, action: decisions[i] || "approve",
      })),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["capsules"] });
      qc.invalidateQueries({ queryKey: ["ps-status", session.session_id] });
    },
  });

  const fmt = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  return (
    <div className="p-6 grid grid-cols-3 gap-4 min-h-screen">
      <div className="col-span-3">
        <PageHeader icon="preserve" kicker="Knowledge Capture"
          title="Preservation Studio"
          subtitle="Record, transcribe and preserve retiring experts' knowledge" />
      </div>
      <div className="card h-fit">
        <h2 className="font-semibold text-gold-400 mb-3">Session Setup</h2>
        <label className="text-xs text-slate-400">Expert</label>
        <input className="input mb-3" value={expert} onChange={(e) => setExpert(e.target.value)} />
        <label className="text-xs text-slate-400">Equipment focus</label>
        <input className="input mb-3" value={equipment} onChange={(e) => setEquipment(e.target.value)} />
        <button className="btn-gold w-full" onClick={() => startSession.mutate()} disabled={!!session}>
          {session ? `Session ${session.session_id}` : "Start Session"}
        </button>
        {!!session?.suggested_prompts?.length && (
          <div className="mt-4">
            <h3 className="text-xs font-semibold text-slate-400 mb-2">SUGGESTED INTERVIEW PROMPTS</h3>
            <ul className="space-y-1.5 text-xs text-slate-300">
              {session.suggested_prompts.map((p: string, i: number) => (
                <li key={i} className="border-l-2 border-gold-500 pl-2">{p}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="card text-center h-fit">
        <h2 className="font-semibold text-gold-400 mb-4">Recording Studio</h2>
        <div className="flex items-end justify-center gap-0.5 h-12 mb-4">
          {levels.map((l, i) => (
            <div key={i} className={`w-1.5 rounded-t ${recording ? "bg-gold-400" : "bg-navy-600"}`}
              style={{ height: `${recording ? l : 4}px`, transition: "height 80ms" }} />
          ))}
        </div>
        <div className="text-3xl font-mono mb-4">{fmt(elapsed)}</div>
        {!recording ? (
          <button className="btn-gold text-lg !px-8 !py-3" disabled={!session}
            onClick={startRecording}>● START RECORDING</button>
        ) : (
          <button className="btn !px-8 !py-3 bg-red-600 text-white hover:bg-red-500"
            onClick={stopRecording}>■ STOP & TRANSCRIBE</button>
        )}
        {status && (
          <div className="mt-4 text-sm">
            <span className="badge bg-navy-700">{status.status}</span>
            {status.status === "TRANSCRIBING" && <div className="text-xs text-slate-400 mt-2 animate-pulse">Whisper large-v3 transcribing...</div>}
          </div>
        )}
        {status?.transcript && (
          <div className="mt-4 text-left text-xs text-slate-300 max-h-48 overflow-y-auto bg-navy-900 rounded p-3 whitespace-pre-wrap">
            {status.transcript}
          </div>
        )}
      </div>

      <div className="card h-fit">
        <h2 className="font-semibold text-gold-400 mb-3">Verification</h2>
        {status?.status !== "VERIFYING" && !verify && (
          <div className="text-slate-500 text-sm">Insight cards appear here after transcription.</div>
        )}
        {(verify?.insights ?? []).map((ins: any, i: number) => (
          <div key={i} className={`card !p-3 mb-2 ${decisions[i] === "reject" ? "opacity-40" : ""}`}>
            <div className="text-xs text-slate-400 mb-1">"{ins.quote}"</div>
            <div className="text-sm mb-2">{ins.insight_text}</div>
            <div className="flex gap-1 flex-wrap mb-2">
              <span className="badge bg-gold-500/20 text-gold-400">{ins.category}</span>
              {(ins.linked_equipment ?? []).map((t: string) => (
                <span key={t} className="badge bg-orange-900 text-orange-300">{t}</span>
              ))}
              <span className="badge bg-navy-700">{ins.confidence}</span>
            </div>
            <div className="flex gap-2 text-xs">
              <button onClick={() => setDecisions((d) => ({ ...d, [i]: "approve" }))}
                className={`btn-ghost !py-1 ${decisions[i] !== "reject" ? "!border-emerald-500 text-emerald-400" : ""}`}>✓ Approve</button>
              <button onClick={() => setDecisions((d) => ({ ...d, [i]: "reject" }))}
                className={`btn-ghost !py-1 ${decisions[i] === "reject" ? "!border-red-500 text-red-400" : ""}`}>✗ Reject</button>
            </div>
          </div>
        ))}
        {!!verify?.insights?.length && (
          <button className="btn-gold w-full mt-2" onClick={() => approve.mutate()} disabled={approve.isPending}>
            {approve.isPending ? "Publishing..." : "Publish Approved to Knowledge Graph"}
          </button>
        )}

        <h3 className="text-xs font-semibold text-slate-400 mt-6 mb-2">PUBLISHED CAPSULES</h3>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {(capsules ?? []).map((k: any) => (
            <div key={k.capsule_id} className="text-xs border border-navy-600 rounded p-2">
              <span className="text-gold-400">★ {k.capsule_id}</span> · {k.expert} · {(k.equipment ?? []).join(", ")}
              <div className="text-slate-400 mt-1 line-clamp-2">{k.insight_text}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
