import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { get } from "../../api/client";
import { useAuth } from "../../store/auth";
import { useTour } from "../../store/tour";
import Icon from "./Icon";
import TopBar from "./TopBar";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { to: "/ask", label: "Ask GyanVriksh", icon: "ask" },
  { to: "/documents", label: "Documents", icon: "documents" },
  { to: "/graph", label: "Knowledge Graph", icon: "graph" },
  { to: "/cliff", label: "Knowledge Cliff", icon: "risk" },
  { to: "/qr", label: "Equipment QR", icon: "qr" },
  { to: "/compliance", label: "Compliance", icon: "compliance" },
  { to: "/maintenance", label: "Maintenance Intel", icon: "maintenance" },
  { to: "/preserve", label: "Preservation Studio", icon: "preserve" },
  { to: "/lessons", label: "Lessons Learned", icon: "lessons" },
  { to: "/admin", label: "Admin", icon: "admin" },
] as const;

export default function Layout() {
  const { name, role, logout } = useAuth();
  const replayTour = useTour((s) => s.replay);
  const navigate = useNavigate();
  const { data: stats } = useQuery({
    queryKey: ["graph-stats"],
    queryFn: () => get("/graph/stats"),
    refetchInterval: 30000,
    retry: false,
  });

  return (
    <div className="flex h-screen">
      <aside className="w-60 glass border-r border-navy-600/60 flex flex-col shrink-0">
        <div className="p-4 flex items-center gap-3 border-b border-brass-400/25">
          <img src="/logo.png" className="w-11 h-11 rounded-full ring-1 ring-brass-400/40" alt="GyanVriksh" />
          <div>
            <div className="font-bold gradient-text text-lg leading-none">GyanVriksh</div>
            <div className="kicker mt-1 !text-[9px] !tracking-[0.22em]">Knowledge Intelligence</div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm transition-all ${
                  isActive
                    ? "text-gold-400 bg-gold-500/10 border-r-2 border-gold-400"
                    : "text-slate-300 hover:bg-navy-700/60 hover:text-slate-100"}`}>
              <Icon name={n.icon} className="w-4 h-4 shrink-0" /> {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-brass-400/25 text-xs space-y-2">
          <div className="terminal p-2 space-y-0.5 text-[11px]">
            <div className="flex justify-between"><span className="text-brass-400/70">NODES</span><span className="text-amber-400 font-bold">{stats?.total_nodes ?? "—"}</span></div>
            <div className="flex justify-between"><span className="text-brass-400/70">RELATIONS</span><span className="text-amber-400 font-bold">{stats?.total_relationships ?? "—"}</span></div>
          </div>
          <div className="paper p-2.5">
            <div className="kicker !text-[8px] !tracking-[0.2em] !text-[#a9702f]">Signed in</div>
            <div className="font-bold text-[#2a1e17] leading-tight">{name}</div>
            <div className="mono text-[10px] uppercase text-[#6b4a2e]">{(role || "").replace(/_/g, " ")}</div>
            <div className="flex items-center gap-1.5 mt-1 text-[10px] text-[#5c6b4a]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#5c6b4a] animate-pulse" /> Active
            </div>
          </div>
          <button className="text-loki-400 hover:underline flex items-center gap-1" onClick={replayTour}>
            <Icon name="spark" className="w-3.5 h-3.5" /> Replay tour
          </button>
          <button className="text-red-400 hover:underline block" onClick={() => { logout(); navigate("/"); }}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <div className="flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
