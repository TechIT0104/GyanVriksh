import { useMemo } from "react";

/** GyanVriksh / Yggdrasil — a lush, glowing sacred tree. Layered translucent
 *  canopy blobs give a painterly aura; a gnarled trunk glows from a bright core;
 *  roots spread below; timeline sparks pulse in the canopy. Warm TVA-amber with
 *  an ethereal core, echoing the Yggdrasil vision. */
export default function SacredTree({ className = "" }: { className?: string }) {
  // canopy foliage clusters (painterly, blurred, translucent)
  const blobs = useMemo(() => ([
    { x: 200, y: 118, r: 78, c: "#f9861a", o: 0.30 },
    { x: 150, y: 150, r: 58, c: "#ffab4d", o: 0.26 },
    { x: 252, y: 150, r: 60, c: "#ffab4d", o: 0.26 },
    { x: 200, y: 150, r: 46, c: "#ffe0a8", o: 0.5 },
    { x: 120, y: 190, r: 44, c: "#f9861a", o: 0.22 },
    { x: 284, y: 188, r: 46, c: "#f9861a", o: 0.22 },
    { x: 172, y: 108, r: 40, c: "#ffd9a0", o: 0.32 },
    { x: 232, y: 112, r: 38, c: "#ffd9a0", o: 0.30 },
    { x: 108, y: 150, r: 36, c: "#b98cf0", o: 0.12 }, // faint cool Yggdrasil hint
    { x: 296, y: 156, r: 34, c: "#7fd0c8", o: 0.12 },
    { x: 200, y: 92, r: 30, c: "#fff2d6", o: 0.5 },
  ]), []);

  const sparks = useMemo(() => {
    const pts: { x: number; y: number; d: number }[] = [];
    let s = 7;
    const rnd = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
    for (let i = 0; i < 26; i++) {
      const ang = rnd() * Math.PI * 2;
      const rad = 30 + rnd() * 78;
      pts.push({ x: 200 + Math.cos(ang) * rad, y: 145 + Math.sin(ang) * rad * 0.8, d: i });
    }
    return pts;
  }, []);

  return (
    <svg viewBox="0 0 400 430" className={className} aria-hidden="true">
      <defs>
        <radialGradient id="yg-aura">
          <stop offset="0%" stopColor="#ffcf8f" stopOpacity="0.5" />
          <stop offset="40%" stopColor="#f9861a" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#f9861a" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="yg-core">
          <stop offset="0%" stopColor="#fff6e2" />
          <stop offset="55%" stopColor="#ffb84d" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#ffb84d" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="yg-trunk" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ffcf8f" />
          <stop offset="35%" stopColor="#c9761f" />
          <stop offset="100%" stopColor="#3a2410" />
        </linearGradient>
        <radialGradient id="spark-grad">
          <stop offset="0%" stopColor="#fff2d6" />
          <stop offset="60%" stopColor="#f9861a" />
          <stop offset="100%" stopColor="#f9861a" stopOpacity="0" />
        </radialGradient>
        <filter id="yg-blur-lg" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="14" /></filter>
        <filter id="yg-blur-sm" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="4" /></filter>
        <filter id="yg-glow" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="2" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      <g style={{ transformOrigin: "200px 230px", animation: "gv-float 7s ease-in-out infinite" }}>
        {/* background aura */}
        <ellipse cx="200" cy="150" rx="150" ry="140" fill="url(#yg-aura)" />

        {/* roots */}
        <g stroke="url(#yg-trunk)" fill="none" strokeLinecap="round" filter="url(#yg-glow)" opacity="0.9">
          <path d="M196 250 C 170 285, 150 300, 110 330" strokeWidth="7" />
          <path d="M204 250 C 230 285, 255 300, 300 330" strokeWidth="7" />
          <path d="M200 255 C 198 300, 196 330, 190 372" strokeWidth="6" />
          <path d="M188 300 C 170 320, 150 330, 128 356" strokeWidth="3" />
          <path d="M212 300 C 235 320, 255 332, 276 356" strokeWidth="3" />
        </g>

        {/* trunk + main branches */}
        <g stroke="url(#yg-trunk)" fill="none" strokeLinecap="round" filter="url(#yg-glow)">
          <path d="M200 258 C 197 220, 199 195, 200 168" strokeWidth="12" />
          <path d="M200 205 C 176 188, 156 176, 132 150" strokeWidth="7" />
          <path d="M200 205 C 226 188, 248 176, 272 150" strokeWidth="7" />
          <path d="M200 190 C 190 168, 186 150, 182 120" strokeWidth="6" />
          <path d="M200 190 C 212 168, 218 150, 224 122" strokeWidth="6" />
          <path d="M156 168 C 146 156, 138 146, 126 128" strokeWidth="3" />
          <path d="M244 168 C 256 156, 264 146, 276 128" strokeWidth="3" />
        </g>

        {/* glowing core at the heart of the tree */}
        <ellipse cx="200" cy="150" rx="70" ry="66" fill="url(#yg-core)" filter="url(#yg-blur-sm)"
          style={{ animation: "gv-flicker 5s ease-in-out infinite" }} />

        {/* painterly canopy foliage */}
        <g filter="url(#yg-blur-lg)">
          {blobs.map((b, i) => (
            <circle key={i} cx={b.x} cy={b.y} r={b.r} fill={b.c} opacity={b.o} />
          ))}
        </g>

        {/* timeline sparks */}
        <g>
          {sparks.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r={1.8} fill="url(#spark-grad)"
              style={{ animation: "tree-pulse 3s ease-in-out infinite", animationDelay: `${(p.d % 10) * 0.28}s`, opacity: 0 }} />
          ))}
        </g>
      </g>

      <style>{`
        @keyframes tree-pulse { 0%,100% { opacity: 0.15; } 50% { opacity: 1; } }
      `}</style>
    </svg>
  );
}
