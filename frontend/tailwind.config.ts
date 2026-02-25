import type { Config } from "tailwindcss";
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0f14",
        panel: "#0f1720",
        panel2: "#121c26",
        border: "rgba(255,255,255,0.08)",
        text: "rgba(255,255,255,0.92)",
        muted: "rgba(255,255,255,0.65)",
        billing: "#22d3ee",
        gated: "#fb923c",
        fire: "#ef4444",
        hems: "#f59e0b",
        fleet: "#3b82f6",
        compliance: "#a855f7",
        cad: "#94a3b8"
      }
    }
  },
  plugins: []
} satisfies Config;
