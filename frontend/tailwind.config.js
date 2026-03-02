/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],

  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
    "./hooks/**/*.{js,ts,jsx,tsx}",
    "./providers/**/*.{js,ts,jsx,tsx}",
    "./styles/**/*.css"
  ],

  safelist: [
    {
      pattern: /(bg|text|border|ring|status|system|orange|red)-(.*)/
    }
  ],

  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: {
        "2xl": "1400px"
      }
    },

    extend: {
      /* ============================= */
      /* COLOR SYSTEM (Token Driven)   */
      /* ============================= */

      colors: {
        /* Core shadcn compatibility */
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",

        /* Semantic backgrounds */
        bg: {
          void: "var(--color-bg-void)",
          base: "var(--color-bg-base)",
          panel: "var(--color-bg-panel)",
          raised: "var(--color-bg-panel-raised)",
          overlay: "var(--color-bg-overlay)",
          input: "var(--color-bg-input)"
        },

        /* Text system */
        text: {
          primary: "var(--color-text-primary)",
          secondary: "var(--color-text-secondary)",
          muted: "var(--color-text-muted)",
          disabled: "var(--color-text-disabled)",
          inverse: "var(--color-text-inverse)"
        },

        /* Brand */
        orange: {
          DEFAULT: "var(--color-brand-orange)",
          bright: "var(--color-brand-orange-bright)",
          dim: "var(--color-brand-orange-dim)",
          ghost: "var(--color-brand-orange-ghost)",
          glow: "var(--color-brand-orange-glow)"
        },

        red: {
          DEFAULT: "var(--color-brand-red)",
          bright: "var(--color-brand-red-bright)",
          dim: "var(--color-brand-red-dim)",
          ghost: "var(--color-brand-red-ghost)"
        },

        /* Status */
        status: {
          active: "var(--color-status-active)",
          warning: "var(--color-status-warning)",
          critical: "var(--color-status-critical)",
          info: "var(--color-status-info)",
          neutral: "var(--color-status-neutral)"
        },

        /* System domains */
        system: {
          billing: "var(--color-system-billing)",
          fire: "var(--color-system-fire)",
          hems: "var(--color-system-hems)",
          fleet: "var(--color-system-fleet)",
          compliance: "var(--color-system-compliance)",
          cad: "var(--color-system-cad)"
        }
      },

      /* ============================= */
      /* TYPOGRAPHY SYSTEM             */
      /* ============================= */

      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
        label: ["var(--font-label)"]
      },

      fontSize: {
        display: ["var(--text-display)", { lineHeight: "var(--leading-tight)", fontWeight: "900" }],
        h1: ["var(--text-h1)", { lineHeight: "var(--leading-tight)", fontWeight: "700" }],
        h2: ["var(--text-h2)", { lineHeight: "var(--leading-snug)", fontWeight: "700" }],
        h3: ["var(--text-h3)", { lineHeight: "var(--leading-snug)", fontWeight: "600" }],
        body: ["var(--text-body)", { lineHeight: "var(--leading-base)" }],
        label: ["var(--text-label)", { lineHeight: "var(--leading-tight)", fontWeight: "600" }]
      },

      /* ============================= */
      /* SPACING SYSTEM                */
      /* ============================= */

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
        "12": "var(--space-12)"
      },

      /* ============================= */
      /* RADIUS + ELEVATION            */
      /* ============================= */

      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)"
      },

      boxShadow: {
        "elevation-0": "var(--elevation-0)",
        "elevation-1": "var(--elevation-1)",
        "elevation-2": "var(--elevation-2)",
        "elevation-3": "var(--elevation-3)",
        "elevation-4": "var(--elevation-4)",
        focus: "var(--focus-ring)",
        critical: "var(--elevation-critical)"
      },

      /* ============================= */
      /* MOTION SYSTEM                 */
      /* ============================= */

      transitionDuration: {
        instant: "var(--duration-instant)",
        fast: "var(--duration-fast)",
        base: "var(--duration-base)",
        slow: "var(--duration-slow)"
      },

      transitionTimingFunction: {
        out: "var(--ease-out)",
        "in-out": "var(--ease-in-out)",
        spring: "var(--ease-spring)"
      },

      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" }
        },
        "slide-in-right": {
          "0%": { opacity: "0", transform: "translateX(12px)" },
          "100%": { opacity: "1", transform: "translateX(0)" }
        },
        "pulse-glow": {
          "0%,100%": { boxShadow: "0 0 0 0 var(--color-brand-orange-glow)" },
          "50%": { boxShadow: "0 0 12px 4px var(--color-brand-orange-glow)" }
        }
      },

      animation: {
        "fade-in": "fade-in var(--duration-base) var(--ease-out) both",
        "slide-in-right": "slide-in-right var(--duration-base) var(--ease-out) both",
        "pulse-glow": "pulse-glow 2s var(--ease-in-out) infinite"
      }
    }
  },

  future: {
    hoverOnlyWhenSupported: true
  },

  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography")
  ]
};
