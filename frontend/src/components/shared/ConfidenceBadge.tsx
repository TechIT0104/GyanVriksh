export default function ConfidenceBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    HIGH: "bg-emerald-900 text-emerald-300",
    MEDIUM: "bg-amber-900 text-amber-300",
    LOW: "bg-red-900 text-red-300",
  };
  return <span className={`badge ${colors[level] || colors.LOW}`}>{level}</span>;
}
