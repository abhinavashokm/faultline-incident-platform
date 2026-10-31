import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "var(--canvas)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        border: {
          DEFAULT: "var(--border)",
          hover: "var(--border-hover)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          hover: "var(--primary-hover)",
          tint: "var(--primary-tint)",
          subdued: "var(--primary-subdued)",
          foreground: "var(--primary-foreground)",
        },
        error: {
          DEFAULT: "var(--error)",
          foreground: "var(--error-foreground)",
          container: "var(--error-container)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
          container: "var(--destructive-container)",
        },
        warning: {
          DEFAULT: "var(--warning)",
          foreground: "var(--warning-foreground)",
          container: "var(--warning-container)",
        },
        success: {
          DEFAULT: "var(--success)",
          foreground: "var(--success-foreground)",
          container: "var(--success-container)",
        },
        info: {
          DEFAULT: "var(--info)",
          foreground: "var(--info-foreground)",
          container: "var(--info-container)",
        },
        ai: {
          DEFAULT: "var(--ai)",
          foreground: "var(--ai-foreground)",
          container: "var(--ai-container)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        foreground: {
          DEFAULT: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--text-muted)",
        },
        ring: "var(--ring)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "JetBrains Mono", "monospace"],
      },
      fontSize: {
        "display-lg": ["32px", { lineHeight: "40px", letterSpacing: "-0.02em", fontWeight: "600" }],
        "display-lg-mobile": ["24px", { lineHeight: "32px", letterSpacing: "-0.01em", fontWeight: "600" }],
        "headline-md": ["24px", { lineHeight: "32px", letterSpacing: "-0.015em", fontWeight: "600" }],
        "headline-sm": ["18px", { lineHeight: "26px", letterSpacing: "-0.01em", fontWeight: "600" }],
        "title-md": ["15px", { lineHeight: "22px", fontWeight: "600" }],
        "body-md": ["14px", { lineHeight: "20px", fontWeight: "400" }],
        "body-sm": ["13px", { lineHeight: "18px", fontWeight: "400" }],
        "label-md": ["12px", { lineHeight: "16px", fontWeight: "500" }],
        "label-sm": ["11px", { lineHeight: "14px", fontWeight: "500", letterSpacing: "0.02em" }],
        "code-lg": ["14px", { lineHeight: "22px", fontWeight: "500" }],
        "code-md": ["12px", { lineHeight: "18px", fontWeight: "400" }],
        "code-sm": ["11px", { lineHeight: "16px", fontWeight: "400" }],
      },
      borderRadius: {
        sm: "0.25rem", // 4px
        DEFAULT: "0.5rem", // 8px
        md: "0.375rem", // 6px
        control: "0.4375rem", // 7px (6-8px inputs/buttons)
        lg: "0.75rem", // 12px
        xl: "1rem", // 16px
        full: "9999px",
      },
      boxShadow: {
        "level-0": "none",
        "level-1": "0 1px 2px 0 rgba(15, 23, 42, 0.04)",
        "level-2": "0 4px 6px -1px rgba(15, 23, 42, 0.06), 0 2px 4px -2px rgba(15, 23, 42, 0.04)",
        "level-3": "0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.03)",
      },
      spacing: {
        "space-xs": "0.25rem",
        "space-sm": "0.5rem",
        "space-md": "0.75rem",
        "space-lg": "1rem",
        "space-xl": "1.5rem",
        gutter: "1rem",
        "gutter-lg": "1.5rem",
        margin: "1rem",
        "margin-md": "1.5rem",
        "margin-lg": "2rem",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
