import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { get, post } from "../api/client";
import PageHeader from "../components/shared/PageHeader";

export default function Compliance() {
  const [procedureId, setProcedureId] = useState("SOP-MAINT-047");
  const [selectedRegs, setSelectedRegs] = useState<string[]>([]);
  const { data: regs } = useQuery({ queryKey: ["regs"], queryFn: () => get("/compliance/regulations"), retry: false });
  const { data: dash } = useQuery({ queryKey: ["compliance-dash"], queryFn: () => get("/compliance/dashboard"), retry: false });
  const { data: docs } = useQuery({ queryKey: ["documents"], queryFn: () => get("/documents/"), retry: false });

  const check = useMutation({
    mutationFn: () => post("/compliance/check", { procedure_id: procedureId, regulation_ids: selectedRegs }),
  });
  const report = check.data;

  const sevColor = (s: string) =>
    s === "CRITICAL" ? "bg-red-900 text-red-300" : s === "MODERATE" ? "bg-amber-900 text-amber-300" : "bg-slate-700 text-slate-300";

  return (
    <div className="p-6 space-y-6">
      <PageHeader icon="compliance" kicker="Regulatory Audit"
        title="Compliance Intelligence"
        subtitle="Gap-check procedures against OISD, Factories Act & PESO" />


      <div className="card">
        <h2 className="font-semibold mb-3">Check a Procedure</h2>
        <div className="grid grid-cols-3 gap-3">
          <select className="input" value={procedureId} onChange={(e) => setProcedureId(e.target.value)}>
            {(docs ?? []).filter((d: any) => d.doc_type === "SOP" || d.file_id.startsWith("SOP"))
              .map((d: any) => <option key={d.file_id} value={d.file_id}>{d.file_id}</option>)}
            {!docs?.length && <option>SOP-MAINT-047</option>}
          </select>
          <div className="col-span-2">
            <div className="text-xs text-slate-400 mb-1">Regulations (empty = auto-suggest)</div>
            <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
              {(regs ?? []).map((r: any) => (
                <label key={r.reg_id} className={`badge cursor-pointer ${selectedRegs.includes(r.reg_id) ? "bg-gold-500 text-navy-900" : "bg-navy-700 text-slate-300"}`}>
                  <input type="checkbox" hidden checked={selectedRegs.includes(r.reg_id)}
                    onChange={() => setSelectedRegs((s) =>
                      s.includes(r.reg_id) ? s.filter((x) => x !== r.reg_id) : [...s, r.reg_id])} />
                  {r.reg_id}
                </label>
              ))}
            </div>
          </div>
        </div>
        <button className="btn-gold mt-3" onClick={() => check.mutate()} disabled={check.isPending}>
          {check.isPending ? "Checking requirements..." : "Run Compliance Check"}
        </button>
        {check.isError && <div className="text-red-400 text-sm mt-2">{String(check.error)}</div>}
      </div>

      {report && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Report: {report.procedure_id} vs {report.regulations_checked.join(", ")}</h2>
            <button className="btn-ghost text-sm" onClick={() => {
              const blob = new Blob([report.report_text], { type: "text/plain" });
              const a = document.createElement("a");
              a.href = URL.createObjectURL(blob);
              a.download = `${report.check_id}.txt`;
              a.click();
            }}>Export report</button>
          </div>
          <div className="grid grid-cols-4 gap-3 mb-4 text-center">
            <div className="card !p-3"><div className="text-2xl font-bold">{report.summary.checked}</div><div className="text-xs text-slate-400">Checked</div></div>
            <div className="card !p-3"><div className="text-2xl font-bold text-emerald-400">{report.summary.compliant}</div><div className="text-xs text-slate-400">Compliant</div></div>
            <div className="card !p-3"><div className="text-2xl font-bold text-amber-400">{report.summary.partial}</div><div className="text-xs text-slate-400">Partial</div></div>
            <div className="card !p-3"><div className="text-2xl font-bold text-red-400">{report.summary.non_compliant}</div><div className="text-xs text-slate-400">Non-compliant</div></div>
          </div>
          <div className="space-y-3">
            {report.gaps.map((g: any, i: number) => (
              <div key={i} className="border border-navy-600 rounded-lg p-3">
                <div className="flex gap-2 mb-2">
                  <span className={`badge ${sevColor(g.severity)}`}>{g.severity}</span>
                  <span className="badge bg-navy-700">{g.status}</span>
                  <span className="text-sm text-slate-400">{g.regulation_ref}</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div><div className="text-slate-500 mb-1">Regulation requires</div>{g.regulation_clause}</div>
                  <div><div className="text-slate-500 mb-1">Procedure says</div>{g.procedure_text}</div>
                </div>
                <div className="mt-2 text-xs"><span className="text-red-400">Risk:</span> {g.risk}</div>
                <div className="text-xs"><span className="text-emerald-400">Fix:</span> {g.recommended_action}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2 className="font-semibold mb-3">Plant-Wide Compliance History</h2>
        <table className="w-full text-sm">
          <thead className="text-left text-slate-400 border-b border-navy-600">
            <tr><th className="py-1">Procedure</th><th>Regulations</th><th>Compliant</th><th>Partial</th><th>Gaps</th><th>Checked</th></tr>
          </thead>
          <tbody>
            {(dash?.procedures ?? []).map((p: any) => (
              <tr key={p.check_id} className="border-b border-navy-700">
                <td className="py-1.5">{p.procedure_id}</td>
                <td className="text-slate-400 text-xs">{p.regulations.join(", ")}</td>
                <td className="text-emerald-400">{p.summary.compliant}</td>
                <td className="text-amber-400">{p.summary.partial}</td>
                <td className="text-red-400">{p.summary.non_compliant}</td>
                <td className="text-xs text-slate-500">{new Date(p.checked_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!dash?.procedures?.length && <div className="text-slate-500 text-sm">No checks run yet.</div>}
      </div>
    </div>
  );
}
