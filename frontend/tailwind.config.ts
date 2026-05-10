import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      colors: {
        ink: {
          50: "#f7f8f9",
          100: "#eef0f2",
          200: "#dde1e5",
          300: "#b9bfc6",
          400: "#8b929a",
          500: "#606870",
          600: "#3e4650",
          700: "#2a313a",
          800: "#1a1f26",
          900: "#0f1217",
        },
        accent: {
          50: "#eef6ff",
          100: "#d9eaff",
          200: "#b9d4ff",
          300: "#8cb6ff",
          400: "#5c93ff",
          500: "#2c6fff",
          600: "#1d54d6",
          700: "#1a46b0",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
