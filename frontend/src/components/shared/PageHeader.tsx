import type { ReactNode } from "react";
import Icon from "./Icon";

/** Consistent modern page header: icon chip + TVA-style kicker + gradient
 *  title, with an optional right-aligned action slot. */
export default function PageHeader({ icon, kicker, title, subtitle, right }: {
  icon?: any;
  kicker?: string;
  title: string;
  subtitle?: string;
  right?: ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-4 mb-6 animate-fade-up">
      <div className="flex items-center gap-3">
        {icon && (
          <div className="w-11 h-11 rounded-xl grid place-items-center glass text-loki-400 shrink-0">
            <Icon name={icon} className="w-6 h-6" />
          </div>
        )}
        <div>
          {kicker && <div className="kicker mb-1">{kicker}</div>}
          <h1 className="page-title gradient-text leading-tight">{title}</h1>
          {subtitle && <p className="text-sm text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}
