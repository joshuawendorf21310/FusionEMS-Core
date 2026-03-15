"use client";

import { useState, useMemo } from "react";

interface Module {
  id: string;
  name: string;
  monthlyFee: number;
  description: string;
  perUnit?: { label: string; fee: number };
}

const MODULES: Module[] = [
  {
    id: "core",
    name: "Quantum Core",
    monthlyFee: 499,
    description: "Platform access, users, dashboard, command center, live status, core reporting, settings & admin.",
  },
  {
    id: "billing",
    name: "Billing Module",
    monthlyFee: 500,
    description: "Billing workflows, claims processing support, transport-based pricing logic, and reporting.",
    perUnit: { label: "per billed transport", fee: 2.0 },
  },
  {
    id: "communications",
    name: "Communications Module",
    monthlyFee: 299,
    description: "Telnyx voice & SMS operations, phone system, broadcast, and operator-grade communications.",
  },
  {
    id: "compliance",
    name: "Compliance / NEMSIS Module",
    monthlyFee: 399,
    description: "NEMSIS-ready documentation, schema validation, export workflows, and compliance logging.",
  },
  {
    id: "fleet",
    name: "Fleet Module",
    monthlyFee: 299,
    description: "Fleet visibility, vehicle tracking, maintenance scheduling, and operational dispatch support.",
  },
  {
    id: "reporting",
    name: "Reporting / Executive Analytics",
    monthlyFee: 399,
    description: "Executive dashboards, advanced analytics, custom reports, and operational intelligence.",
  },
];

function PricingCard({
  mod,
  enabled,
  onToggle,
  isCore,
}: {
  mod: Module;
  enabled: boolean;
  onToggle: () => void;
  isCore: boolean;
}) {
  return (
    <div
      className="chamfer-8 border p-5 flex flex-col gap-3 transition-all"
      style={{
        backgroundColor: enabled ? "var(--color-bg-panel)" : "var(--color-bg-base)",
        borderColor: enabled ? "var(--color-brand-orange)" : "var(--color-border-default)",
        opacity: enabled ? 1 : 0.7,
      }}
    >
      <div className="flex items-center justify-between">
        <span
          style={{
            fontFamily: "var(--font-label)",
            fontSize: "var(--text-body)",
            fontWeight: 700,
            color: "var(--color-text-primary)",
          }}
        >
          {mod.name}
        </span>
        {isCore ? (
          <span
            className="label-caps px-2 py-0.5 chamfer-4"
            style={{
              fontSize: "var(--text-micro)",
              color: "var(--color-brand-orange)",
              backgroundColor: "rgba(255,106,0,0.08)",
              border: "1px solid rgba(255,106,0,0.2)",
            }}
          >
            Required
          </span>
        ) : (
          <button
            onClick={onToggle}
            className="chamfer-4 px-3 py-1 text-xs font-semibold transition-colors"
            style={{
              backgroundColor: enabled ? "var(--color-brand-orange)" : "transparent",
              color: enabled ? "var(--color-text-inverse)" : "var(--color-text-muted)",
              border: enabled ? "none" : "1px solid var(--color-border-default)",
            }}
          >
            {enabled ? "Enabled" : "Add"}
          </button>
        )}
      </div>

      <p style={{ fontSize: "var(--text-body)", color: "var(--color-text-muted)", lineHeight: 1.5 }}>
        {mod.description}
      </p>

      <div className="mt-auto pt-2">
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-h3)",
            fontWeight: 700,
            color: "var(--color-text-primary)",
          }}
        >
          ${mod.monthlyFee}
        </span>
        <span style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
          /month
        </span>
        {mod.perUnit && (
          <div style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)", marginTop: 2 }}>
            + ${mod.perUnit.fee.toFixed(2)} {mod.perUnit.label}
          </div>
        )}
      </div>
    </div>
  );
}

export default function PricingPage() {
  const [enabled, setEnabled] = useState<Set<string>>(new Set(["core"]));
  const [transports, setTransports] = useState(200);

  function toggleModule(id: string) {
    if (id === "core") return;
    setEnabled((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const monthlyTotal = useMemo(() => {
    let total = 0;
    for (const mod of MODULES) {
      if (enabled.has(mod.id)) {
        total += mod.monthlyFee;
        if (mod.perUnit && mod.id === "billing") {
          total += transports * mod.perUnit.fee;
        }
      }
    }
    return total;
  }, [enabled, transports]);

  return (
    <div className="min-h-screen px-6 py-8" style={{ backgroundColor: "var(--color-bg-void)" }}>
      <div className="mx-auto max-w-5xl space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-3 mb-2">
            <div
              className="chamfer-4 flex h-9 w-9 items-center justify-center"
              style={{
                backgroundColor: "var(--color-brand-orange)",
                color: "var(--color-text-inverse)",
                fontWeight: 700,
                fontSize: "var(--text-label)",
              }}
            >
              FQ
            </div>
            <h1
              style={{
                fontFamily: "var(--font-label)",
                fontSize: "var(--text-h1)",
                fontWeight: 700,
                color: "var(--color-text-primary)",
                letterSpacing: "0.02em",
              }}
            >
              Quantum Pricing
            </h1>
          </div>
          <p style={{ fontSize: "var(--text-body)", color: "var(--color-text-muted)", maxWidth: 500, margin: "0 auto" }}>
            Simple flat monthly pricing. No revenue share. No collection percentage. Modular, predictable, and profitable.
          </p>
        </div>

        {/* Value props */}
        <div className="flex flex-wrap justify-center gap-4">
          {["No Revenue Share", "Flat Monthly Pricing", "Self-Service Onboarding", "Modular Upsell"].map((prop) => (
            <span
              key={prop}
              className="chamfer-4 px-3 py-1.5 border"
              style={{
                fontSize: "var(--text-micro)",
                color: "var(--color-text-primary)",
                borderColor: "var(--color-border-subtle)",
                letterSpacing: "0.04em",
              }}
            >
              {prop}
            </span>
          ))}
        </div>

        {/* Module Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {MODULES.map((mod) => (
            <PricingCard
              key={mod.id}
              mod={mod}
              enabled={enabled.has(mod.id)}
              onToggle={() => toggleModule(mod.id)}
              isCore={mod.id === "core"}
            />
          ))}
        </div>

        {/* Transport slider (if billing enabled) */}
        {enabled.has("billing") && (
          <div
            className="chamfer-8 border p-5"
            style={{
              backgroundColor: "var(--color-bg-panel)",
              borderColor: "var(--color-border-default)",
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="label-caps" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-label)" }}>
                Monthly Billed Transports
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--text-body)",
                  fontWeight: 700,
                  color: "var(--color-brand-orange)",
                }}
              >
                {transports}
              </span>
            </div>
            <input
              type="range"
              min={50}
              max={2000}
              step={50}
              value={transports}
              onChange={(e) => setTransports(Number(e.target.value))}
              className="w-full accent-[#FF6A00]"
            />
            <div className="flex justify-between mt-1" style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
              <span>50</span>
              <span>2,000</span>
            </div>
          </div>
        )}

        {/* Cost Summary */}
        <div
          className="chamfer-8 border p-6"
          style={{
            backgroundColor: "var(--color-bg-panel)",
            borderColor: "var(--color-brand-orange)",
          }}
        >
          <span className="label-caps" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-label)" }}>
            Monthly Cost Summary
          </span>

          <div className="mt-4 space-y-2">
            {MODULES.filter((m) => enabled.has(m.id)).map((mod) => (
              <div key={mod.id} className="flex items-center justify-between">
                <span style={{ fontSize: "var(--text-body)", color: "var(--color-text-primary)" }}>
                  {mod.name}
                </span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-body)", color: "var(--color-text-primary)" }}>
                  ${mod.monthlyFee.toLocaleString()}
                  {mod.perUnit && mod.id === "billing" && (
                    <span style={{ color: "var(--color-text-muted)" }}>
                      {" "}+ ${(transports * mod.perUnit.fee).toLocaleString()} usage
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>

          <div
            className="mt-4 pt-4 flex items-center justify-between border-t"
            style={{ borderColor: "var(--color-border-default)" }}
          >
            <span style={{ fontSize: "var(--text-body)", fontWeight: 700, color: "var(--color-text-primary)" }}>
              Total Monthly
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "var(--text-h2)",
                fontWeight: 700,
                color: "var(--color-brand-orange)",
              }}
            >
              ${monthlyTotal.toLocaleString()}
            </span>
          </div>

          <p className="mt-3" style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
            Billed via Stripe. Self-service module activation. No mandatory onboarding fee.
          </p>
        </div>

        {/* Wisconsin launch */}
        <div
          className="chamfer-8 border p-5 text-center"
          style={{
            backgroundColor: "var(--color-bg-panel)",
            borderColor: "var(--color-border-default)",
          }}
        >
          <span className="label-caps" style={{ color: "var(--color-brand-orange)", fontSize: "var(--text-label)" }}>
            Wisconsin-First Launch
          </span>
          <p className="mt-2" style={{ fontSize: "var(--text-body)", color: "var(--color-text-muted)", maxWidth: 500, margin: "8px auto 0" }}>
            FusionEMS Quantum launches in Wisconsin as an all-in-one EMS billing, compliance, communications, and operations platform with self-service setup and premium platform economics.
          </p>
        </div>

        <div className="text-center pt-2">
          <span style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
            FusionEMS Quantum — Modular pricing for modern EMS operations
          </span>
        </div>
      </div>
    </div>
  );
}
