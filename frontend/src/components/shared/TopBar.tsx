import { useEffect, useState } from "react";

/** TVA-style registry top bar: temporal coordinate, ticking analog clock and
 *  live status readout. Mid-century bureaucratic-futurism flavour. */
export default function TopBar() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const time = now.toLocaleTimeString("en-GB");
  const date = now.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  const secAngle = now.getSeconds() * 6;

  return (
    <div className="sticky top-0 z-30 h-11 flex items-center justify-between px-4 mono text-xs
                    border-b border-brass-400/30 bg-[#241812]/85 backdrop-blur">
      <div className="flex items-center gap-2 text-brass-300">
        <span className="uppercase tracking-[0.2em] text-cream/90 font-bold">GyanVriksh</span>
        <span className="text-amber-400">//</span>
        <span className="hidden sm:inline uppercase tracking-[0.2em] text-brass-300/80">Bharat Chemicals · Unit-3</span>
      </div>

      <div className="flex items-center gap-3 sm:gap-5">
        <div className="hidden md:flex items-center gap-2">
          <span className="uppercase tracking-widest text-[10px] text-brass-400/70">Date</span>
          <span className="text-cream/90">{date}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="relative inline-block w-4 h-4">
            <span className="absolute inset-0 rounded-full border border-amber-400/70" />
            <span className="absolute left-1/2 top-1/2 w-px h-[6px] bg-amber-400 origin-bottom"
              style={{ transform: `translate(-50%,-100%) rotate(${secAngle}deg)` }} />
          </span>
          <span className="text-amber-400 tracking-wider tabular-nums">{time}</span>
        </div>
        <span className="hidden sm:flex items-center gap-1.5 text-olive-400">
          <span className="w-1.5 h-1.5 rounded-full bg-olive-400 animate-pulse" />
          <span className="uppercase tracking-widest text-[10px]">System Online</span>
        </span>
      </div>
    </div>
  );
}
