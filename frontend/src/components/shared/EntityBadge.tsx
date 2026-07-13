const COLORS: Record<string, string> = {
  EQUIPMENT_TAG: "bg-orange-900 text-orange-300",
  REGULATORY_REF: "bg-red-900 text-red-300",
  PERSON: "bg-yellow-900 text-yellow-200",
  DATE: "bg-blue-900 text-blue-300",
  FAILURE_MODE: "bg-purple-900 text-purple-300",
  ACTION_TAKEN: "bg-emerald-900 text-emerald-300",
  PROCEDURE_REF: "bg-teal-900 text-teal-300",
  PROCESS_PARAM: "bg-cyan-900 text-cyan-300",
};

export default function EntityBadge({ text, label }: { text: string; label: string }) {
  return (
    <span className={`badge mr-1 mb-1 inline-block ${COLORS[label] || "bg-slate-700 text-slate-300"}`}
      title={label}>
      {text}
    </span>
  );
}
