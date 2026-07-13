import { useQuery } from "@tanstack/react-query";
import { get, post } from "../api/client";
import PageHeader from "../components/shared/PageHeader";

export default function Admin() {
  const { data: stats } = useQuery({ queryKey: ["admin-stats"], queryFn: () => get("/admin/stats"), retry: false });
  const { data: users } = useQuery({ queryKey: ["admin-users"], queryFn: () => get("/admin/users"), retry: false });
  const { data: audit } = useQuery({ queryKey: ["audit"], queryFn: () => get("/admin/audit-log"), retry: false });

  return (
    <div className="p-6 space-y-6">
      <PageHeader icon="admin" kicker="System Control"
        title="Admin Panel"
        subtitle="Platform health, users and audit log" />


      <div className="grid grid-cols-4 gap-3">
        <div className="card text-center">
          <div className="text-3xl font-bold text-gold-400">{stats?.documents?.total ?? "—"}</div>
          <div className="text-xs text-slate-400">Documents ({stats?.documents?.indexed ?? 0} indexed)</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-gold-400">{stats?.neo4j?.total_nodes ?? "—"}</div>
          <div className="text-xs text-slate-400">Graph nodes</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-gold-400">{stats?.neo4j?.total_relationships ?? "—"}</div>
          <div className="text-xs text-slate-400">Relationships</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-gold-400">{stats?.queries_served ?? "—"}</div>
          <div className="text-xs text-slate-400">Copilot queries served</div>
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold mb-2">Qdrant Collections</h2>
        <div className="flex gap-4 text-sm">
          {Object.entries(stats?.qdrant ?? {}).map(([name, count]) => (
            <div key={name}><span className="text-slate-400">{name}:</span> <span className="text-gold-400">{String(count)}</span></div>
          ))}
        </div>
        <button className="btn-ghost mt-3 text-sm" onClick={() => post("/admin/reindex")}>
          Re-index all documents
        </button>
      </div>

      <div className="card">
        <h2 className="font-semibold mb-2">Users</h2>
        <table className="w-full text-sm">
          <thead className="text-left text-slate-400 border-b border-navy-600">
            <tr><th className="py-1">Email</th><th>Name</th><th>Role</th><th>Status</th></tr>
          </thead>
          <tbody>
            {(users ?? []).map((u: any) => (
              <tr key={u.id} className="border-b border-navy-700">
                <td className="py-1.5">{u.email}</td><td>{u.name}</td>
                <td><span className="badge bg-navy-700">{u.role}</span></td>
                <td>{u.is_active ? <span className="text-emerald-400">active</span> : <span className="text-red-400">inactive</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2 className="font-semibold mb-2">Audit Log</h2>
        <div className="max-h-56 overflow-y-auto text-xs space-y-1">
          {(audit ?? []).map((a: any, i: number) => (
            <div key={i} className="text-slate-400">
              <span className="text-slate-500">{new Date(a.at).toLocaleString()}</span> · {a.user} · <span className="text-gold-400">{a.action}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
