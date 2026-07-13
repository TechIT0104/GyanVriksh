import type { ReactNode } from "react";

/** A TVA monitor panel: dark screen, orange frame, corner brackets and an
 *  optional hatched title bar with a case code. The building block of the
 *  whole registry UI. */
export default function TvaPanel({ title, code, children, className = "", bodyClass = "p-3" }: {
  title?: string;
  code?: string;
  children: ReactNode;
  className?: string;
  bodyClass?: string;
}) {
  return (
    <div className={`relative bg-screen-800 border border-amber-400/40 ${className}`}>
      {/* corner brackets */}
      <span className="absolute -top-px -left-px w-3 h-3 border-t-2 border-l-2 border-amber-400 pointer-events-none" />
      <span className="absolute -top-px -right-px w-3 h-3 border-t-2 border-r-2 border-amber-400 pointer-events-none" />
      <span className="absolute -bottom-px -left-px w-3 h-3 border-b-2 border-l-2 border-amber-400 pointer-events-none" />
      <span className="absolute -bottom-px -right-px w-3 h-3 border-b-2 border-r-2 border-amber-400 pointer-events-none" />

      {title && (
        <div className="flex items-center gap-2 px-3 py-1.5 border-b border-amber-400/30">
          <span className="mono text-[11px] uppercase tracking-[0.2em] text-amber-400 whitespace-nowrap">{title}</span>
          <span className="flex-1 h-2 hatch opacity-50" />
          {code && <span className="mono text-[10px] text-amber-400/60 whitespace-nowrap">{code}</span>}
        </div>
      )}
      <div className={bodyClass}>{children}</div>
    </div>
  );
}
