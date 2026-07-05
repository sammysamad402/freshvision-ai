/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brand palette — deep slate base, electric green accent, amber alert
        surface: { DEFAULT: "#0f1117", 1: "#181c27", 2: "#1e2336", 3: "#252b40" },
        brand: { DEFAULT: "#22c55e", dim: "#16a34a", glow: "#4ade80" },
        alert: { DEFAULT: "#f59e0b", red: "#ef4444", blue: "#3b82f6" },
        muted: "#64748b",
      },
      fontFamily: {
        sans: ["'Inter'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
    },
  },
  plugins: [],
};
