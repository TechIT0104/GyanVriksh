import Icon from "./Icon";
import TvaPanel from "./TvaPanel";

export interface Agent {
  name: string;
  role?: string;
  department?: string;
  expertise?: string[];
  years?: number;
  retirement?: string;      // ISO date
  status?: "ACTIVE" | "RETIRING SOON" | "KNOWLEDGE AT RISK";
  capsules?: number;        // preserved knowledge capsules
  code?: string;
}

function hashCode(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

function initials(name: string) {
  return name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

const STATUS_STYLE: Record<string, string> = {
  "ACTIVE": "bg-olive-400 text-[#0c0b0a]",
  "RETIRING SOON": "bg-amber-400 text-[#140b03]",
  "KNOWLEDGE AT RISK": "bg-red-500 text-white",
};

const PILL = "mono text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-[2px]";

/** TVA "MISSION INFO" style dossier for a person in the organisation. */
export default function AgentDossier({ agent, compact = false }: { agent: Agent; compact?: boolean }) {
  const h = hashCode(agent.name);
  const caseCode = `EMP-${(h % 8999) + 1000}`;
  const clearance = `LVL ${(h % 4) + 2}`;
  const status = agent.status ?? "ACTIVE";

  return (
    <TvaPanel title="Personnel Record" code={caseCode} bodyClass="p-0">
      <div className="flex">
        {/* icon rail */}
        <div className="flex flex-col gap-1 p-2 border-r border-amber-400/25">
          {(["ask", "graph", "documents", "compliance", "maintenance"] as const).map((n) => (
            <div key={n} className="w-8 h-8 grid place-items-center border border-amber-400/30 text-amber-400/80">
              <Icon name={n} className="w-4 h-4" />
            </div>
          ))}
        </div>

        {/* timeline data column */}
        <div className="p-3 border-r border-amber-400/25 mono text-[10px] leading-relaxed min-w-[120px]">
          <div className="text-amber-400/60 uppercase">Employee ID</div>
          <div className="text-amber-300 mb-2">{caseCode}</div>
          <div className="text-amber-400/60 uppercase">Clearance</div>
          <div className="text-amber-300 mb-2">{clearance}</div>
          <div className="text-amber-400/60 uppercase">Tenure</div>
          <div className="text-amber-300 mb-2">{agent.years != null ? `${agent.years} YRS` : "—"}</div>
          <div className="text-amber-400/60 uppercase">Department</div>
          <div className="text-amber-300">{(agent.department ?? "GENERAL").toUpperCase().slice(0, 16)}</div>
        </div>

        {/* details center */}
        <div className="flex-1 p-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="mono text-[11px] uppercase tracking-widest text-amber-400">Record</span>
            <span className="flex-1 h-2 hatch opacity-40" />
          </div>
          <div className="flex items-center gap-2 mb-3">
            <span className="mono text-xs text-amber-400/70">STATUS:</span>
            <span className={`${PILL} ${STATUS_STYLE[status]}`}>{status}</span>
          </div>
          <div className="space-y-1.5">
            <DataRow label="RETIREMENT" value={agent.retirement ?? "—"} highlight={status !== "ACTIVE"} />
            <DataRow label="KNOWLEDGE CAPSULES" value={String(agent.capsules ?? 0)} highlight={(agent.capsules ?? 0) === 0 && status !== "ACTIVE"} />
            {!compact && (agent.expertise ?? []).slice(0, 3).map((e) => (
              <DataRow key={e} label="EXPERTISE" value={e} />
            ))}
          </div>
        </div>

        {/* halftone mugshot */}
        <div className="p-3 border-l border-amber-400/25 grid place-items-center">
          <div className="relative w-24 h-28 border border-amber-400/50 overflow-hidden bg-[#0b0908]">
            <div className="absolute inset-0 grid place-items-center text-4xl font-black text-amber-400/90 mono"
              style={{ textShadow: "0 0 14px rgba(245,124,0,0.6)" }}>
              {initials(agent.name)}
            </div>
            {/* dither scanlines over the portrait */}
            <div className="absolute inset-0 pointer-events-none"
              style={{ background: "repeating-linear-gradient(to bottom, rgba(0,0,0,0.35) 0 1px, transparent 1px 2px)" }} />
            <div className="absolute inset-0 pointer-events-none"
              style={{ background: "radial-gradient(circle at 50% 30%, rgba(245,124,0,0.25), transparent 70%)" }} />
          </div>
          <div className="mono text-[10px] text-center text-amber-300 mt-1.5 uppercase max-w-24 truncate">{agent.name}</div>
          <div className="mono text-[9px] text-center text-amber-400/50 uppercase">{agent.role ?? "Analyst"}</div>
        </div>
      </div>
    </TvaPanel>
  );
}

function DataRow({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`flex items-center justify-between gap-3 px-2 py-1 border mono text-[11px] ${
      highlight ? "bg-amber-400 border-amber-300 text-[#140b03] font-bold" : "border-amber-400/30 text-amber-300"}`}>
      <span className={highlight ? "opacity-80" : "text-amber-400/60"}>{label}</span>
      <span className="truncate max-w-[55%] text-right">{value}</span>
    </div>
  );
}
