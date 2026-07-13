import { useQuery } from "@tanstack/react-query";
import { get } from "../api/client";
import PageHeader from "../components/shared/PageHeader";

export default function LessonsLearned() {
  const { data: patterns, isLoading } = useQuery({
    queryKey: ["patterns"], queryFn: () => get("/admin/lessons/patterns"),
    retry: false, staleTime: 5 * 60 * 1000,
  });
  const { data: cliff } = useQuery({
    queryKey: ["cliff"], queryFn: () => get("/admin/lessons/knowledge-cliff"), retry: false,
  });

  return (
    <div className="p-6 space-y-6">
      <PageHeader icon="lessons" kicker="Failure Intelligence"
        title="Lessons Learned"
        subtitle="AI-clustered incident patterns and preventive recommendations" />


      <div>
        <h2 className="font-semibold mb-3">Detected Incident Patterns (AI clustering)</h2>
        {isLoading && <div className="text-slate-400 text-sm animate-pulse">Clustering incident embeddings and labeling patterns...</div>}
        <div className="space-y-3">
          {(patterns ?? []).map((p: any) => (
            <details key={p.pattern_id} className="card">
              <summary className="cursor-pointer flex items-center gap-3">
                <span className={`badge ${p.severity === "HIGH" ? "bg-red-900 text-red-300" : "bg-amber-900 text-amber-300"}`}>
                  {p.severity}
                </span>
                <span className="font-semibold">PATTERN #{p.pattern_id} — {p.pattern_name}</span>
                <span className="text-slate-400 text-sm">({p.incident_count} incidents)</span>
              </summary>
              <div className="mt-3 text-sm space-y-2">
                <div><span className="text-slate-500">Common thread:</span> {p.common_thread}</div>
                {p.time_pattern && <div><span className="text-slate-500">Time pattern:</span> {p.time_pattern}</div>}
                <div><span className="text-emerald-400">Preventive recommendation:</span> {p.preventive_recommendation}</div>
                <div className="space-y-1 mt-2">
                  {p.incidents.map((i: any) => (
                    <div key={i.id} className="text-xs border border-navy-600 rounded p-2">
                      <span className="badge bg-purple-900 text-purple-300 mr-2">{i.id}</span>
                      <span className="text-slate-400">{i.date} · {(i.equipment ?? []).join(", ")}</span>
                      <div className="mt-1">{i.description}</div>
                    </div>
                  ))}
                </div>
              </div>
            </details>
          ))}
          {!isLoading && !patterns?.length && (
            <div className="text-slate-500 text-sm">Not enough incident history for clustering (need 2+ similar incidents).</div>
          )}
        </div>
      </div>

      <div>
        <h2 className="font-semibold mb-3">Knowledge Cliff — Experts Retiring Within 3 Years</h2>
        <div className="grid grid-cols-3 gap-3">
          {(cliff ?? []).map((p: any) => (
            <div key={p.name} className="card">
              <div className="font-semibold text-gold-400">{p.name}</div>
              <div className="text-xs text-amber-400 mb-2">Retires {p.retirement_date} · {p.years_experience} yrs experience</div>
              <div className="text-xs text-slate-400">Expertise: {(p.expertise ?? []).join(", ") || "—"}</div>
              <div className="text-xs mt-1">
                <span className="text-emerald-400">Captured:</span> {(p.captured ?? []).join(", ") || "none"}
              </div>
              {!!p.uncaptured?.length && (
                <div className="text-xs mt-1">
                  <span className="text-red-400">At risk:</span> {p.uncaptured.join(", ")}
                  <a href="/preserve" className="text-gold-400 block mt-1 hover:underline">Schedule recording session →</a>
                </div>
              )}
            </div>
          ))}
          {!cliff?.length && <div className="text-slate-500 text-sm col-span-3">No retirement data loaded.</div>}
        </div>
      </div>
    </div>
  );
}
