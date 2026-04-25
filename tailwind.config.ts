import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#dbe6ff",
          200: "#b7ceff",
          300: "#8ba7ff",
          400: "#5e7fff",
          500: "#3f5eef",
          600: "#2f4ac9",
          700: "#253b9b",
          800: "#1e3076",
          900: "#172957",
        },
      },
      boxShadow: {
        soft: "0 18px 50px rgba(16, 24, 40, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
