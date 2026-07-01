import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        input: "var(--input)",
        ring: "var(--ring)",
        background: "var(--background)",
        foreground: "var(--foreground)",
        surface: "var(--surface)",
        subtle: "var(--subtle)",
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        // Semantic clearance/state — reserved for meaning; never decoration.
        public: {
          DEFAULT: "var(--public-bg)",
          foreground: "var(--public-fg)",
          border: "var(--public-border)",
        },
        restricted: {
          DEFAULT: "var(--restricted-bg)",
          foreground: "var(--restricted-fg)",
          border: "var(--restricted-border)",
        },
        secret: {
          DEFAULT: "var(--secret-bg)",
          foreground: "var(--secret-fg)",
          border: "var(--secret-border)",
        },
        "top-secret": {
          DEFAULT: "var(--top-secret-bg)",
          foreground: "var(--top-secret-fg)",
          border: "var(--top-secret-border)",
        },
        conflict: {
          DEFAULT: "var(--conflict-bg)",
          foreground: "var(--conflict-fg)",
          border: "var(--conflict-border)",
        },
      },
      borderRadius: {
        // Phase E radius scale (--r-sm/md/lg on top of legacy --radius).
        sm: "var(--r-sm)",
        md: "var(--r-md)",
        lg: "var(--r-lg)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans, var(--font-sans))"],
        mono: ["var(--font-geist-mono)"],
      },
    },
  },
  plugins: [],
};
export default config;
