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
          bg: "#0B0C1F",
          canvas: "#070814",
          surface: "#12132A",
          surfaceHover: "#1A1C3B",
          card: "rgba(18, 19, 42, 0.75)",
          border: "rgba(139, 92, 246, 0.2)",
          borderBright: "rgba(167, 139, 250, 0.4)",
          lime: "#C6F432",
          limeHover: "#D4F855",
          violet: "#8B5CF6",
          violetDark: "#4C1D95",
          amber: "#f59e0b",
          red: "#ef4444",
          cyan: "#06b6d4",
          emerald: "#10b981",
          blue: "#3b82f6",
          text: "#F1F5F9",
          muted: "#94A3B8",
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
