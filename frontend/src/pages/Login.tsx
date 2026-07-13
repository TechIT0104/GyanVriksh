import { useState } from "react";
import { post } from "../api/client";
import { useAuth } from "../store/auth";
import ThreeNetwork from "../components/shared/ThreeNetwork";
import SacredTree from "../components/shared/SacredTree";

export default function Login() {
  const login = useAuth((s) => s.login);
  const [email, setEmail] = useState("engineer@bharatchem.in");
  const [password, setPassword] = useState("gyanvriksh");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await post("/auth/login", { email, password });
      login(res.access_token, res.role, res.name);
      window.location.href = res.role === "field_technician" ? "/mobile" : "/dashboard";
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-[#0c0b0a]">
      <ThreeNetwork />
      <SacredTree className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-[54%] w-[620px] max-w-none opacity-50 pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-b from-[#0c0b0a]/40 via-[#0c0b0a]/10 to-[#0c0b0a]/80 pointer-events-none" />
      <div className="w-full max-w-sm relative z-10 animate-fade-up">
        <div className="text-center mb-8">
          <img src="/logo.png" className="w-28 h-28 mx-auto mb-3 animate-float rounded-full ring-1 ring-brass-400/40" alt="GyanVriksh" />
          <h1 className="text-4xl font-bold gradient-text">GyanVriksh</h1>
          <div className="kicker mt-2">Industrial Knowledge Intelligence</div>
          <p className="text-brass-300/80 text-sm mt-2 italic">
            Har dastaavez ka gyan. Har sawaal ka jawaab.
          </p>
        </div>
        <form onSubmit={submit} className="card space-y-4">
          <input className="input" type="email" placeholder="Email" value={email}
            onChange={(e) => setEmail(e.target.value)} />
          <input className="input" type="password" placeholder="Password" value={password}
            onChange={(e) => setPassword(e.target.value)} />
          {error && <div className="text-red-400 text-sm">{error}</div>}
          <button className="btn-gold w-full" disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
          <div className="text-xs text-slate-500 pt-2 border-t border-navy-600/60">
            Demo accounts (password: gyanvriksh):<br />
            manager@ · engineer@ · tech@ · auditor@ · admin@bharatchem.in
            <div className="mt-2 text-[10px] text-brass-400/50 mono uppercase tracking-wider">
              Demo build · synthetic data · full security implemented
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
