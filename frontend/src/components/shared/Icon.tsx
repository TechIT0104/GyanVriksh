/** Lightweight line-icon set (feather-style, stroke = currentColor).
 *  Replaces childish emoji throughout the app with clean, professional icons. */
type IconName =
  | "dashboard" | "ask" | "documents" | "graph" | "compliance"
  | "maintenance" | "preserve" | "lessons" | "admin" | "mic"
  | "spark" | "tree" | "shield" | "arrow" | "back" | "check" | "risk"
  | "speaker" | "stop" | "qr";

const PATHS: Record<IconName, JSX.Element> = {
  dashboard: (<><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /></>),
  ask: (<><path d="M12 3l1.9 4.6L18.5 9l-4.6 1.9L12 15.5 10.1 10.9 5.5 9l4.6-1.4z" /><circle cx="18.5" cy="17.5" r="1.6" /></>),
  documents: (<><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M9 13h6M9 17h6" /></>),
  graph: (<><circle cx="6" cy="6" r="2.4" /><circle cx="18" cy="7" r="2.4" /><circle cx="12" cy="18" r="2.4" /><path d="M8 7.4l7.7 0M7.3 8l3.7 8M16.8 9l-3.6 7" /></>),
  compliance: (<><path d="M12 3l7 3v6c0 4.4-3 7.6-7 9-4-1.4-7-4.6-7-9V6z" /><path d="M9 12l2 2 4-4.5" /></>),
  maintenance: (<><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" /></>),
  preserve: (<><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M6 11a6 6 0 0 0 12 0M12 17v4M9 21h6" /></>),
  lessons: (<><path d="M9 18h6M10 21h4" /><path d="M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.2 1 2.5h6c0-1.3.3-1.8 1-2.5A6 6 0 0 0 12 3z" /></>),
  admin: (<><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="9" cy="6" r="1.8" /><circle cx="15" cy="12" r="1.8" /><circle cx="8" cy="18" r="1.8" /></>),
  mic: (<><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M6 11a6 6 0 0 0 12 0M12 17v4M9 21h6" /></>),
  spark: (<><path d="M12 3l1.9 4.6L18.5 9l-4.6 1.9L12 15.5 10.1 10.9 5.5 9l4.6-1.4z" /></>),
  tree: (<><circle cx="12" cy="5" r="2.4" /><circle cx="6" cy="14" r="2.4" /><circle cx="18" cy="14" r="2.4" /><path d="M12 7.4V20M12 12l-4.3 1M12 12l4.3 1M8 20h8" /></>),
  shield: (<><path d="M12 3l7 3v6c0 4.4-3 7.6-7 9-4-1.4-7-4.6-7-9V6z" /><path d="M9 12l2 2 4-4.5" /></>),
  arrow: (<path d="M5 12h14M13 6l6 6-6 6" />),
  back: (<path d="M19 12H5M11 6l-6 6 6 6" />),
  check: (<path d="M4 12l5 5L20 6" />),
  risk: (<><path d="M12 3l9 16H3z" /><path d="M12 10v4M12 17h.01" /></>),
  speaker: (<><path d="M4 9v6h4l5 4V5L8 9H4z" /><path d="M16 8.5a4 4 0 0 1 0 7M18.5 6a7 7 0 0 1 0 12" /></>),
  stop: (<rect x="6" y="6" width="12" height="12" rx="1" />),
  qr: (<><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><path d="M14 14h3v3M20 14v.01M14 20h.01M17 20h4v-3" /></>),
};

export default function Icon({ name, className = "w-5 h-5", strokeWidth = 1.8 }:
  { name: IconName; className?: string; strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      {PATHS[name]}
    </svg>
  );
}
