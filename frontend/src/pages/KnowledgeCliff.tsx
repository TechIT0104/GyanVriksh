import { useQuery } from "@tanstack/react-query";
import { get } from "../api/client";
import PageHeader from "../components/shared/PageHeader";
import AgentDossier, { type Agent } from "../components/shared/AgentDossier";
import TvaPanel from "../components/shared/TvaPanel";

interface Expert {
  name: string; designation?: string; department?: string; expertise?: string[];
  years?: number; retirement?: string; months_left?: number; retiring: boolean;
  equipment: string[]; workorders: number; capsules: number; status: Agent["status"];
}
interface CliffData {
  summary: { horizon_years: number; experts_retiring: number; total_experts: number; equipment_at_risk: number; knowledge_at_risk_pct: number };
  experts: Expert[];
  equipment_at_risk: { tag: string; type?: string; experts: string[] }[];
}

function Metric({ value, label, danger = false }: { value: string | number; label: string; danger?: boolean }) {
  return (
    <div className="text-center px-4">
      <div className={`text-4xl font-black mono ${danger ? "text-red-500" : "text-amber-400"}`}
        style={{ textShadow: danger ? "0 0 18px rgba(239,68,68,0.5)" : "0 0 18px rgba(249,134,26,0.5)" }}>{value}</div>
      <div className="kicker mt-1 !tracking-[0.16em]">{label}</div>
    </div>
  );
}

export default function KnowledgeCliff() {
  const { data, isLoading } = useQuery<CliffData>({
    queryKey: ["cliff-risk"], queryFn: () => get("/graph/cliff-risk?years=3"), retry: false,
  });

  const s = data?.summary;
  const experts = data?.experts ?? [];
  const atRisk = experts.filter((e) => e.retiring);
  const active = experts.filter((e) => !e.retiring);

  return (
    <div className="p-6">
      <PageHeader icon="preserve" kicker="Workforce Intelligence"
        title="Knowledge Cliff Radar"
        subtitle="Expertise at risk of walking out the door as veterans retire" />

      {/* risk summary */}
      <TvaPanel title="Risk Summary" code={`HORIZON ${s?.horizon_years ?? 3}Y`} className="mb-5 animate-fade-up">
        <div className="flex flex-wrap items-center justify-around gap-4 py-2">
          <Metric value={s?.experts_retiring ?? "—"} label="Experts Retiring ≤3Y" />
          <div className="w-px h-12 bg-amber-400/20" />
          <Metric value={s?.equipment_at_risk ?? "—"} label="Equipment Unpreserved" danger={(s?.equipment_at_risk ?? 0) > 0} />
          <div className="w-px h-12 bg-amber-400/20" />
          <Metric value={s ? `${s.knowledge_at_risk_pct}%` : "—"} label="Work-Order History At Risk" danger={(s?.knowledge_at_risk_pct ?? 0) >= 30} />
          <div className="w-px h-12 bg-amber-400/20" />
          <Metric value={s ? `${s.experts_retiring}/${s.total_experts}` : "—"} label="Of Total Workforce" />
        </div>
        {(s?.knowledge_at_risk_pct ?? 0) >= 30 && (
          <div className="mt-3 flex items-center gap-2 text-red-400 text-sm border-t border-amber-400/20 pt-3">
            <span className="status-pill !bg-red-500 !text-white text-[10px]">ACTION REQUIRED</span>
            {s?.knowledge_at_risk_pct}% of hands-on maintenance history sits with people retiring within 3 years. Prioritise recording their knowledge now.
          </div>
        )}
      </TvaPanel>

      {isLoading && <div className="mono text-amber-400/70">Loading workforce data…</div>}

      {/* at-risk experts as dossiers */}
      {!!atRisk.length && (
        <>
          <div className="kicker mb-2">Priority · Retiring within 3 years</div>
          <div className="space-y-4 mb-6 stagger">
            {atRisk.map((e) => (
              <AgentDossier key={e.name} agent={{
                name: e.name, role: e.designation, department: e.department,
                expertise: e.expertise, years: e.years, retirement: e.retirement,
                status: e.status, capsules: e.capsules,
              }} />
            ))}
          </div>
        </>
      )}

      {/* equipment at risk */}
      {!!data?.equipment_at_risk.length && (
        <TvaPanel title="Unpreserved Equipment" code="NO CAPSULE" className="mb-6">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {data.equipment_at_risk.map((eq) => (
              <div key={eq.tag} className="border border-amber-400/30 p-2 mono text-xs">
                <div className="text-amber-400 font-bold">{eq.tag}</div>
                <div className="text-amber-300/60 text-[10px] uppercase">{eq.type}</div>
                <div className="text-red-400/80 text-[10px] mt-1">depends on: {eq.experts.join(", ")}</div>
              </div>
            ))}
          </div>
        </TvaPanel>
      )}

      {/* active workforce */}
      {!!active.length && (
        <>
          <div className="kicker mb-2">Active workforce</div>
          <div className="space-y-4 stagger">
            {active.map((e) => (
              <AgentDossier key={e.name} agent={{
                name: e.name, role: e.designation, department: e.department,
                expertise: e.expertise, years: e.years, retirement: e.retirement,
                status: e.status, capsules: e.capsules,
              }} compact />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
