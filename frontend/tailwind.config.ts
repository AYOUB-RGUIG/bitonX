import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#f7f8fa",
        ink: "#111827",
        muted: "#64748b",
        line: "#d7dde5",
        panel: "#ffffff",
        accent: "#0f766e",
      },
    },
  },
  plugins: [],
};

export default config;

