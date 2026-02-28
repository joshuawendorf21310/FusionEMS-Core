import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],

  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./providers/**/*.{ts,tsx}",
    "./styles/**/*.css",
  ],

  safelist: [
    {
      pattern: /(bg|text|border|status|system|orange|red)-(.*)/,
    },
  ],

  theme: {
    container: {
      center: true,
      padding: "var(--space-4)",
      screens: {
        "2xl": "1400px",
      },
    },

    extend: {
      colors: {
        /* Backgrounds */
        bg: {
          void: "var(--color-bg-void)",
          base: "var(--color-bg-base)",
          panel: "var(--color-bg-panel)",
          raised: "var(--color-bg-panel-raised)",
          overlay: "var(--color-bg-overlay)",
          input: "var(--color-bg-input)",
        },

        /* Borders */
        border: {
          DEFAULT: "var(--color-border-default)",
          subtle: "var(--color-border-subtle)",
          strong: "var(--color-border-strong)",
          focus: "var(--color-border-focus)",
        },

        /* Text */
        text: {
          primary: "var(--color-text-primary)",
          secondary: "var(--color-text-secondary)",
          muted: "var(--color-text-muted)",
          disabled: "var(--color-text-disabled)",
          inverse: "var(--color-text-inverse)",
        },

        /* Brand */
        orange: {
          DEFAULT: "var(--color-brand-orange)",
          bright: "var(--color-brand-orange-bright)",
          dim: "var(--color-brand-orange-dim)",
          ghost: "var(--color-brand-orange-ghost)",
          glow: "var(--color-brand-orange-glow)",
        },

        red: {
          DEFAULT: "var(--color-brand-red)",
          bright: "var(--color-brand-red-bright)",
          dim: "var(--color-brand-red-dim)",
          ghost: "var(--color-brand-red-ghost)",
        },

        /* Status */
        status: {
          active: "var(--color-status-active)",
          warning: "var(--color-status-warning)",
          critical: "var(--color-status-critical)",
          info: "var(--color-status-info)",
          neutral: "var(--color-status-neutral)",
        },

        /* System Lines */
        system: {
          billing: "var(--color-system-billing)",
          fire: "var(--color-system-fire)",
          hems: "var(--color-system-hems)",
          fleet: "var(--color-system-fleet)",
          compliance: "var(--color-system-compliance)",
          cad: "var(--color-system-cad)",
        },
      },

      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
        label: ["var(--font-label)"],
      },

      fontSize: {
        display: [
          "var(--text-display)",
          { lineHeight: "var(--leading-tight)", fontWeight: "900" },
        ],
        h1: [
          "var(--text-h1)",
          { lineHeight: "var(--leading-tight)", fontWeight: "700" },
        ],
        h2: [
          "var(--text-h2)",
          { lineHeight: "var(--leading-snug)", fontWeight: "700" },
        ],
        h3: [
          "var(--text-h3)",
          { lineHeight: "var(--leading-snug)", fontWeight: "600" },
        ],
        "body-lg": [
          "var(--text-body-lg)",
          { lineHeight: "var(--leading-base)" },
        ],
        body: [
          "var(--text-body)",
          { lineHeight: "var(--leading-base)" },
        ],
        label: [
          "var(--text-label)",
          {
            lineHeight: "var(--leading-tight)",
            letterSpacing: "var(--tracking-label)",
            fontWeight: "600",
          },
        ],
        micro: [
          "var(--text-micro)",
          {
            lineHeight: "var(--leading-tight)",
            letterSpacing: "var(--tracking-micro)",
            fontWeight: "500",
          },
        ],
      },

      spacing: {
        "0": "var(--space-0)",
        "1": "var(--space-1)",
        "2": "var(--space-2)",
        "3": "var(--space-3)",
        "4": "var(--space-4)",
        "5": "var(--space-5)",
        "6": "var(--space-6)",
        "7": "var(--space-7)",
        "8": "var(--space-8)",
        "9": "var(--space-9)",
        "10": "var(--space-10)",
        "11": "var(--space-11)",
        "12": "var(--space-12)",
      },

      boxShadow: {
        "elevation-0": "var(--elevation-0)",
        "elevation-1": "var(--elevation-1)",
        "elevation-2": "var(--elevation-2)",
        "elevation-3": "var(--elevation-3)",
        "elevation-4": "var(--elevation-4)",
        critical: "var(--elevation-critical)",
        focus: "var(--focus-ring)",
      },

      transitionDuration: {
        instant: "var(--duration-instant)",
        fast: "var(--duration-fast)",
        base: "var(--duration-base)",
        slow: "var(--duration-slow)",
      },

      transitionTimingFunction: {
        out: "var(--ease-out)",
        "in-out": "var(--ease-in-out)",
        spring: "var(--ease-spring)",
      },

      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in-right": {
          "0%": { opacity: "0", transform: "translateX(12px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "pulse-glow": {
          "0%, 100%": {
            boxShadow: "0 0 0 0 var(--color-brand-orange-glow)",
          },
          "50%": {
            boxShadow:
              "0 0 12px 4px var(--color-brand-orange-glow)",
          },
        },
        "status-pulse": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
      },

      animation: {
        "fade-in":
          "fade-in var(--duration-base) var(--ease-out) both",
        "slide-in-right":
          "slide-in-right var(--duration-base) var(--ease-out) both",
        "pulse-glow":
          "pulse-glow 2s var(--ease-in-out) infinite",
        "status-pulse":
          "status-pulse 1.5s ease-in-out infinite",
      },
    },
  },

  future: {
    hoverOnlyWhenSupported: true,
  },

  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
  ],
};

export default config;
