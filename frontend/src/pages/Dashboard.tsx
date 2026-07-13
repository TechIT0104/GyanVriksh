import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { get } from "../api/client";
import PageHeader from "../components/shared/PageHeader";
import AgentDossier, { type Agent } from "../components/shared/AgentDossier";
import { useAuth } from "../store/auth";

// Known personnel (matches the demo graph) so the logged-in agent's dossier is rich.
const AGENTS: Record<string, Partial<Agent>> = {
  "Arjun Mehta": { department: "Mechanical Maintenance", expertise: ["Heat Exchangers", "Planning"], years: 8, retirement: "2044-05-31", status: "ACTIVE", capsules: 0 },
  "Sunil Yadav": { department: "Mechanical Maintenance", expertise: ["Pumps", "Valves"], years: 5, retirement: "2048-01-31", status: "ACTIVE", capsules: 0 },
  "Kavita Rao": { department: "Safety", expertise: ["PTW Systems", "Confined Space Entry", "Gas Testing"], years: 14, retirement: "2038-11-30", status: "ACTIVE", capsules: 0 },
  "Priya Deshmukh": { department: "Production", expertise: ["Plant Operations", "Planning"], years: 20, retirement: "2030-03-31", status: "RETIRING SOON", capsules: 0 },
};

export default function Dashboard() {
  const { data: queue } = useQuery({ queryKey: ["health-queue"], queryFn: () => get("/maintenance/health-queue"), retry: false });
  const { data: compliance } = useQuery({ queryKey: ["compliance-dash"], queryFn: () => get("/compliance/dashboard"), retry: false });
  const { data: docs } = useQuery({ queryKey: ["documents"], queryFn: () => get("/documents/"), retry: false });
  const { data: alerts } = useQuery({ queryKey: ["alerts"], queryFn: () => get("/maintenance/alerts"), retry: false });
  const { data: cliff } = useQuery({ queryKey: ["cliff"], queryFn: () => get("/graph/cliff-risk?years=3"), retry: false });
  const { data: bench } = useQuery({ queryKey: ["bench"], queryFn: () => get("/copilot/benchmark"), retry: false });

  const indexed = docs?.filter((d: any) => d.status === "INDEXED").length ?? 0;
  const coverage = docs?.length ? Math.round((indexed / docs.length) * 100) : 0;

  const compTotals = (compliance?.procedures ?? []).reduce(
    (acc: any, p: any) => ({
      compliant: acc.compliant + (p.summary?.compliant ?? 0),
      partial: acc.partial + (p.summary?.partial ?? 0),
      non: acc.non + (p.summary?.non_compliant ?? 0),
    }), { compliant: 0, partial: 0, non: 0 });
  const pieData = [
    { name: "Compliant", value: compTotals.compliant, color: "#10b981" },
    { name: "Partial", value: compTotals.partial, color: "#f59e0b" },
    { name: "Non-compliant", value: compTotals.non, color: "#ef4444" },
  ].filter((d) => d.value > 0);

  const healthColor = (s: number) => (s < 40 ? "bg-red-600" : s < 70 ? "bg-amber-500" : "bg-emerald-600");

  const { name, role } = useAuth();
  const agent: Agent = { name: name || "Analyst", role: role || undefined, ...(AGENTS[name || ""] || {}) };

  return (
    <div className="p-6">
      <PageHeader icon="dashboard" kicker="Bharat Chemicals · Unit 3"
        title="Command Dashboard" subtitle="Plant knowledge health at a glance" />
      <div className="mb-4 animate-fade-up">
        <AgentDossier agent={agent} />
      </div>
      <div className="grid grid-cols-2 gap-4 stagger">
      <div className="card">
        <h2 className="font-semibold mb-3 text-gold-400">Knowledge Coverage Score</h2>
        <div className="flex items-center gap-6">
          <div className="relative w-32 h-32">
            <svg viewBox="0 0 36 36" className="w-32 h-32 -rotate-90">
              <circle cx="18" cy="18" r="15.9" fill="none" stroke="#16304D" strokeWidth="3.8" />
              <circle cx="18" cy="18" r="15.9" fill="none" stroke="#F5C542" strokeWidth="3.8"
                strokeDasharray={`${coverage}, 100`} strokeLinecap="round" />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center text-2xl font-bold text-gold-400">
              {coverage}
            </div>
          </div>
          <div className="text-sm text-slate-400">
            <div>{docs?.length ?? 0} documents uploaded</div>
            <div>{indexed} fully indexed</div>
            <Link to="/documents" className="text-gold-400 hover:underline">Manage documents →</Link>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold mb-3 text-gold-400">Recent Activity</h2>
        <ul className="space-y-2 text-sm max-h-40 overflow-y-auto">
          {(alerts ?? []).slice(0, 6).map((a: any) => (
            <li key={a.id} className="flex gap-2">
              <span className={`badge shrink-0 ${a.severity === "HIGH" ? "bg-red-900 text-red-300" : "bg-amber-900 text-amber-300"}`}>
                {a.alert_type}
              </span>
              <span className="text-slate-300">{a.message}</span>
            </li>
          ))}
          {!alerts?.length && <li className="text-slate-500">No active alerts</li>}
        </ul>
      </div>

      <div className="card">
        <h2 className="font-semibold mb-3 text-gold-400">Equipment Health Heatmap</h2>
        <div className="grid grid-cols-5 gap-2">
          {(queue ?? []).map((e: any) => (
            <Link key={e.tag_id} to={`/maintenance?tag=${e.tag_id}`}
              className={`${healthColor(e.health_score)} rounded-lg p-2 text-center hover:opacity-80`}
              title={`Health ${e.health_score} · last maintained ${e.last_maintained}`}>
              <div className="font-bold text-white text-sm">{e.tag_id}</div>
              <div className="text-xs text-white/80">{e.health_score}</div>
            </Link>
          ))}
          {!queue?.length && <div className="text-slate-500 text-sm col-span-5">Load demo data to see equipment</div>}
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold mb-3 text-gold-400">Compliance Status</h2>
        {pieData.length ? (
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={pieData} dataKey="value" innerRadius={50} outerRadius={75} paddingAngle={3}>
                {pieData.map((d) => <Cell key={d.name} fill={d.color} />)}
              </Pie>
              <Tooltip contentStyle={{ background: "#0F2137", border: "1px solid #1E3F63" }} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-slate-500 text-sm">
            No compliance checks yet. <Link to="/compliance" className="text-gold-400 hover:underline">Run one →</Link>
          </div>
        )}
      </div>

      <Link to="/cliff" className="card block hover:border-amber-400">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gold-400">Knowledge Cliff Risk</h2>
          <span className="kicker">≤ 3 Years</span>
        </div>
        {cliff?.summary ? (
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className={`text-4xl font-black mono ${cliff.summary.knowledge_at_risk_pct >= 30 ? "text-red-500" : "text-amber-400"}`}
                style={{ textShadow: "0 0 18px rgba(249,134,26,0.4)" }}>{cliff.summary.knowledge_at_risk_pct}%</div>
              <div className="kicker mt-1 !tracking-[0.14em]">History At Risk</div>
            </div>
            <div className="text-sm text-amber-300/80 space-y-1 mono">
              <div>{cliff.summary.experts_retiring} experts retiring soon</div>
              <div>{cliff.summary.equipment_at_risk} equipment unpreserved</div>
              <div className="text-amber-400/60">Open radar →</div>
            </div>
          </div>
        ) : (
          <div className="text-slate-500 text-sm">Load demo data to compute workforce risk</div>
        )}
      </Link>

      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gold-400">Benchmark</h2>
          <span className="kicker">100 Questions</span>
        </div>
        {bench?.available ? (
          <div className="grid grid-cols-3 gap-2 text-center">
            <div><div className="text-3xl font-black mono text-amber-400">{bench.summary.accuracy_pct}%</div><div className="kicker mt-1 !tracking-[0.12em]">Accuracy</div></div>
            <div><div className="text-3xl font-black mono text-amber-400">{bench.summary.answers_with_citations_pct}%</div><div className="kicker mt-1 !tracking-[0.12em]">Cited</div></div>
            <div><div className="text-3xl font-black mono text-amber-400">{bench.summary.median_response_s}s</div><div className="kicker mt-1 !tracking-[0.12em]">Median</div></div>
          </div>
        ) : (
          <div className="text-slate-500 text-sm mono">
            Not run yet. Execute:<br />
            <span className="text-amber-400/80">python scripts\run_benchmark.py 20</span>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
