/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // TVA / Temporal Registry palette (per the GyanVriksh logo):
        // deep walnut + bronze panels, warm cream text, electric amber-orange
        // energy accents, muted military-green secondary. Existing tokens are
        // remapped so every page recolors at once.
        navy: { 900: "#040507", 800: "#0E0F12", 700: "#171A1F", 600: "#26262A" },
        screen: { 900: "#040507", 800: "#0E0F12", 700: "#171A1F" },
        gold: { 400: "#F9861A", 500: "#B86517" },       // authentic TVA orange
        brass: { 300: "#FFA23E", 400: "#F9861A", 500: "#B86517" },
        amber: { 300: "#FFA23E", 400: "#F9861A", 500: "#B86517" }, // bright TVA orange
        loki: { 300: "#FFA23E", 400: "#F9861A", 500: "#B86517" },  // alias -> orange
        olive: { 400: "#8A9A5B", 500: "#61703C" },      // muted status green
        teal: { 400: "#8A9A5B" },                        // alias -> olive
        grape: { 400: "#F57C00" },
        rust: { 400: "#B5651C" },
        paper: { DEFAULT: "#EFE7D7", 200: "#E3D7C1", 300: "#D2C1A2" },
        cream: "#EFE7D7",
        // Override Tailwind's stock hues with warm, TVA-harmonious tones so the
        // categorical badges (entity types, pipeline status) stay distinct but
        // no longer clash with the amber/walnut theme.
        emerald: { 300: "#B8C48F", 400: "#8A9A5B", 500: "#61703C", 900: "#26301A" },
        blue: { 300: "#9FBAB8", 400: "#6E8F92", 500: "#4E6E70", 900: "#182A2B" },
        purple: { 300: "#CBA98C", 400: "#B0805C", 500: "#8A6444", 900: "#2C2016" },
        cyan: { 300: "#E0BE84", 400: "#C79A5B", 500: "#A9702F", 900: "#2E2510" },
      },
      fontFamily: {
        sans: ["Space Grotesk", "Inter", "system-ui", "sans-serif"],
        display: ["Space Grotesk", "Inter", "system-ui", "sans-serif"],
        mono: ["Space Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 26px rgba(255,115,0,0.4)",
        "glow-gold": "0 0 26px rgba(232,162,74,0.35)",
      },
      backgroundImage: {
        "gold-grad": "linear-gradient(135deg,#FF9A4D,#E65C00)",
        "brass-grad": "linear-gradient(135deg,#DDB878,#A9702F)",
        "aurora": "radial-gradient(60% 55% at 50% 0%, rgba(255,115,0,0.16), transparent 60%)",
      },
      animation: {
        "fade-up": "gv-fade-up 0.6s cubic-bezier(0.22,1,0.36,1) both",
        "fade-in": "gv-fade 0.7s ease both",
        float: "gv-float 4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
