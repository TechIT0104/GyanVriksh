/** Miss Minutes — the TVA mascot, reused as GyanVriksh's AI assistant character. */
export default function MissMinutes({ className = "w-32", variant = "wave" }:
  { className?: string; variant?: "wave" | "point" | "angry" }) {
  const src = variant === "point" ? "/tva/missminutes.gif"
    : variant === "angry" ? "/tva/loki-miss.gif"
    : "/tva/missminutes2.gif";
  return (
    <img src={src} alt="Miss Minutes" className={className}
      style={{ filter: "drop-shadow(0 0 18px rgba(249,134,26,0.45))" }} />
  );
}
