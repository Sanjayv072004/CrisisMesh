import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ops: {
          bg: "#0a0d14",
          surface: "#111622",
          surfaceHover: "#182030",
          border: "#1e293b",
          borderBright: "#334155",
          amber: "#f59e0b",
          red: "#ef4444",
          cyan: "#06b6d4",
          emerald: "#10b981",
          blue: "#3b82f6",
          text: "#f8fafc",
          muted: "#94a3b8",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
