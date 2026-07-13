import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { get } from "../api/client";

const TABS = ["Timeline", "Patterns & RCA", "Procedures", "Who Knows This", "Knowledge Capsules"];

export default function Maintenance() {
  const [params, setParams] = useSearchParams();
  const tag = params.get("tag") || "";
  const [tab, setTab] = useState(0);

  const { data: queue } = useQuery({ queryKey: ["health-queue"], queryFn: () => get("/maintenance/health-queue"), retry: false });
  const { data: view } = useQuery({
    queryKey: ["equip360", tag], queryFn: () => get(`/maintenance/${tag}/360`),
    enabled: !!tag, retry: false,
  });
  const { data: rca, isLoading: rcaLoading } = useQuery({
    queryKey: ["rca", tag], queryFn: () => get(`/maintenance/${tag}/rca`),
    enabled: !!tag && tab === 1, retry: false, staleTime: Infinity,
  });

  const eq = view?.equipment;
  const score = view?.health_score ?? 0;
  const scoreColor = score < 40 ? "text-red-400" : score < 70 ? "text-amber-400" : "text-emerald-400";

  return (
    <div className="flex h-screen">
      <aside className="w-72 border-r border-navy-600 overflow-y-auto p-3 shrink-0">
        <h2 className="text-sm font-semibold text-gold-400 mb-2">Predictive Maintenance Queue</h2>
        <div className="text-xs text-slate-500 mb-3">Sorted worst-first by health score</div>
        {(queue ?? []).map((e: any) => (
          <button key={e.tag_id} onClick={() => setParams({ tag: e.tag_id })}
            className={`w-full text-left card !p-2.5 mb-2 hover:border-gold-500 ${tag === e.tag_id ? "!border-gold-500" : ""}`}>
            <div className="flex justify-between">
              <span className="font-semibold">{e.tag_id}</span>
              <span className={e.health_score < 40 ? "text-red-400" : e.health_score < 70 ? "text-amber-400" : "text-emerald-400"}>
                {e.health_score}
              </span>
            </div>
            <div className="text-xs text-slate-400">{e.name}</div>
            {e.overdue_days > 0 && <div className="text-xs text-red-400">Overdue {e.overdue_days} days</div>}
          </button>
        ))}
      </aside>

      <div className="flex-1 overflow-y-auto p-6">
        {!tag && <div className="text-slate-500 mt-20 text-center">Select equipment from the queue or search the graph.</div>}
        {tag && view && (
          <>
            <div className="flex items-center gap-4 mb-4">
              <div>
                <h1 className="text-2xl font-bold text-gold-400">{eq?.tag_id}</h1>
                <div className="text-slate-400">{eq?.name} · {eq?.unit} · {eq?.location}</div>
              </div>
              <span className={`badge ${eq?.criticality === "HIGH" ? "bg-red-900 text-red-300" : "bg-amber-900 text-amber-300"}`}>
                {eq?.criticality}
              </span>
              <div className="ml-auto text-right">
                <div className={`text-4xl font-bold ${scoreColor}`}>{score}</div>
                <div className="text-xs text-slate-500">health score{view.mtbf_days ? ` · MTBF ${view.mtbf_days}d` : ""}</div>
              </div>
            </div>

            <div className="flex gap-1 border-b border-navy-600 mb-4">
              {TABS.map((t, i) => (
                <button key={t} onClick={() => setTab(i)}
                  className={`px-4 py-2 text-sm ${tab === i ? "text-gold-400 border-b-2 border-gold-400" : "text-slate-400"}`}>
                  {t}
                </button>
              ))}
            </div>

            {tab === 0 && (
              <div className="space-y-2">
                {[...(view.workorders ?? []).map((w: any) => ({ ...w, _kind: "wo" })),
                  ...(view.incidents ?? []).map((i: any) => ({ ...i, _kind: "inc" }))]
                  .sort((a, b) => String(b.date).localeCompare(String(a.date)))
                  .map((e: any) => (
                    <div key={e.wo_id || e.incident_id} className={`card !p-3 border-l-4 ${
                      e._kind === "inc" ? "!border-l-red-500" : e.type === "CORRECTIVE" ? "!border-l-amber-500" : "!border-l-emerald-500"}`}>
                      <div className="flex gap-3 text-sm">
                        <span className="text-slate-500 w-24 shrink-0">{String(e.date)}</span>
                        <span className="badge bg-navy-700 shrink-0">{e.wo_id || e.incident_id}</span>
                        <span>{e.description}</span>
                      </div>
                      {e.findings && <div className="text-xs text-slate-400 mt-1 ml-27">Findings: {e.findings}</div>}
                      {e.root_cause && <div className="text-xs text-red-300 mt-1">Root cause: {e.root_cause}</div>}
                    </div>
                  ))}
              </div>
            )}

            {tab === 1 && (
              <div className="card whitespace-pre-wrap text-sm leading-relaxed">
                {rcaLoading ? "Generating AI failure pattern analysis and RCA..." : rca?.report}
              </div>
            )}

            {tab === 2 && (
              <div className="space-y-2">
                {(view.procedures ?? []).map((p: any) => (
                  <div key={p.proc_id} className="card !p-3">
                    <div className="font-semibold">{p.proc_id}</div>
                    <div className="text-sm text-slate-400">{p.title}</div>
                  </div>
                ))}
                {(view.regulations ?? []).map((r: any) => (
                  <div key={r.reg_id} className="card !p-3 !border-red-900">
                    <span className="badge bg-red-900 text-red-300 mr-2">{r.reg_id}</span>
                    <span className="text-sm">{r.title}</span>
                  </div>
                ))}
              </div>
            )}

            {tab === 3 && (
              <div className="grid grid-cols-2 gap-3">
                {(view.technicians ?? []).map((t: any) => (
                  <div key={t.person_id} className="card">
                    <div className="font-semibold text-gold-400">{t.name}</div>
                    <div className="text-sm text-slate-400">{t.designation} · {t.department}</div>
                    {t.years_experience && <div className="text-xs mt-1">{t.years_experience} years experience</div>}
                    {t.retirement_date && (
                      <div className="text-xs text-amber-400 mt-1">Retires: {String(t.retirement_date)}</div>
                    )}
                    {t.expertise && <div className="text-xs text-slate-500 mt-1">{[].concat(t.expertise).join(" · ")}</div>}
                  </div>
                ))}
                {!view.technicians?.length && <div className="text-slate-500">No linked personnel.</div>}
              </div>
            )}

            {tab === 4 && (
              <div className="space-y-3">
                {(view.capsules ?? []).map((k: any) => (
                  <div key={k.capsule_id} className="card !border-gold-500/50">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-gold-400">★</span>
                      <span className="font-semibold">{k.expert}</span>
                      <span className="badge bg-gold-500/20 text-gold-400">{k.category}</span>
                      <span className="text-xs text-slate-500 ml-auto">{k.recorded_date} · verified by {k.verified_by}</span>
                    </div>
                    <p className="text-sm">{k.insight_text}</p>
                    {k.transcript && (
                      <details className="mt-2 text-xs text-slate-400">
                        <summary className="cursor-pointer text-gold-400">Full transcript</summary>
                        <div className="whitespace-pre-wrap mt-2">{k.transcript}</div>
                      </details>
                    )}
                  </div>
                ))}
                {!view.capsules?.length && (
                  <div className="text-slate-500">
                    No knowledge capsules for this equipment yet. <a href="/preserve" className="text-gold-400">Record one →</a>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
