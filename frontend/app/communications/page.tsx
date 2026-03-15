"use client";

import { useEffect, useState } from "react";

type ReadinessStatus = "ready" | "warning" | "failed" | "unknown";

interface ReadinessCheck {
  label: string;
  status: ReadinessStatus;
  detail: string;
}

const STATUS_COLORS: Record<ReadinessStatus, string> = {
  ready: "var(--color-status-active)",
  warning: "var(--color-status-warning)",
  failed: "var(--color-status-critical)",
  unknown: "var(--color-text-muted)",
};

const STATUS_LABELS: Record<ReadinessStatus, string> = {
  ready: "Ready",
  warning: "Warning",
  failed: "Failed",
  unknown: "Unknown",
};

function CheckRow({ check }: { check: ReadinessCheck }) {
  return (
    <div
      className="flex items-center justify-between px-5 py-3.5 border-b"
      style={{ borderColor: "var(--color-border-subtle)" }}
    >
      <div className="flex items-center gap-3">
        <span
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: STATUS_COLORS[check.status] }}
        />
        <span style={{ color: "var(--color-text-primary)", fontSize: "var(--text-body)" }}>
          {check.label}
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span
          className="label-caps"
          style={{ color: STATUS_COLORS[check.status], fontSize: "var(--text-micro)" }}
        >
          {STATUS_LABELS[check.status]}
        </span>
        <span style={{ color: "var(--color-text-muted)", fontSize: "var(--text-micro)" }}>
          {check.detail}
        </span>
      </div>
    </div>
  );
}

function useTelnyxReadiness() {
  const [checks, setChecks] = useState<ReadinessCheck[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function run() {
      const results: ReadinessCheck[] = [];
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";

      // Voice binding
      try {
        const res = await fetch(`${apiUrl}/api/v1/communications/telnyx/voice-status`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("fusionems_token") || localStorage.getItem("token") || ""}`,
          },
          signal: AbortSignal.timeout(5000),
        });
        if (res.ok) {
          const data = await res.json();
          results.push({
            label: "Voice Binding — +1-888-365-0144",
            status: data.bound ? "ready" : "warning",
            detail: data.bound ? "Active and bound" : "Not bound",
          });
        } else {
          results.push({ label: "Voice Binding — +1-888-365-0144", status: "unknown", detail: "API unavailable" });
        }
      } catch {
        results.push({ label: "Voice Binding — +1-888-365-0144", status: "unknown", detail: "Requires runtime verification" });
      }

      // Messaging profile
      try {
        const res = await fetch(`${apiUrl}/api/v1/communications/telnyx/messaging-status`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("fusionems_token") || localStorage.getItem("token") || ""}`,
          },
          signal: AbortSignal.timeout(5000),
        });
        if (res.ok) {
          const data = await res.json();
          results.push({
            label: "Messaging Profile — +1-888-365-0144",
            status: data.active ? "ready" : "warning",
            detail: data.active ? "Profile active" : "Profile inactive",
          });
        } else {
          results.push({ label: "Messaging Profile — +1-888-365-0144", status: "unknown", detail: "API unavailable" });
        }
      } catch {
        results.push({ label: "Messaging Profile — +1-888-365-0144", status: "unknown", detail: "Requires runtime verification" });
      }

      // Webhook reachability
      try {
        const res = await fetch(`${apiUrl}/api/v1/communications/telnyx/webhook-status`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("fusionems_token") || localStorage.getItem("token") || ""}`,
          },
          signal: AbortSignal.timeout(5000),
        });
        if (res.ok) {
          const data = await res.json();
          results.push({
            label: "Webhook Reachability",
            status: data.reachable ? "ready" : "failed",
            detail: data.reachable ? "Webhook endpoint verified" : "Webhook unreachable",
          });
        } else {
          results.push({ label: "Webhook Reachability", status: "unknown", detail: "API unavailable" });
        }
      } catch {
        results.push({ label: "Webhook Reachability", status: "unknown", detail: "Requires runtime verification" });
      }

      // Number active
      results.push({
        label: "Number Active — +1-888-365-0144",
        status: "unknown",
        detail: "Requires Telnyx API validation",
      });

      // Stale binding detection
      results.push({
        label: "Stale Binding Detection",
        status: "unknown",
        detail: "Requires runtime check",
      });

      setChecks(results);
      setLoading(false);
    }

    run();
  }, []);

  return { checks, loading };
}

export default function CommunicationsPage() {
  const { checks, loading } = useTelnyxReadiness();

  const allReady = checks.length > 0 && checks.every((c) => c.status === "ready");
  const hasFailed = checks.some((c) => c.status === "failed");
  const hasUnknown = checks.some((c) => c.status === "unknown");

  let overallLabel = "Communications Fully Operational";
  let overallColor = "var(--color-status-active)";
  let blocksRelease = false;

  if (hasFailed) {
    overallLabel = "Communications Failure Detected — Release Blocked";
    overallColor = "var(--color-status-critical)";
    blocksRelease = true;
  } else if (hasUnknown) {
    overallLabel = "Communications Readiness Incomplete";
    overallColor = "var(--color-text-muted)";
    blocksRelease = true;
  } else if (!allReady) {
    overallLabel = "Communications Partially Degraded";
    overallColor = "var(--color-status-warning)";
  }

  return (
    <div
      className="min-h-screen px-6 py-8"
      style={{ backgroundColor: "var(--color-bg-void)" }}
    >
      <div className="mx-auto max-w-4xl space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-3">
            <div
              className="chamfer-4 flex h-8 w-8 items-center justify-center"
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
                fontSize: "var(--text-h2)",
                fontWeight: 700,
                color: "var(--color-text-primary)",
                letterSpacing: "0.02em",
              }}
            >
              Communications Readiness
            </h1>
          </div>
          <p className="mt-1" style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
            Telnyx operational readiness console — +1-888-365-0144
          </p>
        </div>

        {/* Overall */}
        {loading ? (
          <div
            className="chamfer-8 flex items-center gap-3 px-5 py-4 border animate-pulse"
            style={{
              borderColor: "var(--color-border-default)",
              backgroundColor: "var(--color-bg-panel)",
            }}
          >
            <span className="h-3 w-3 rounded-full" style={{ backgroundColor: "var(--color-text-muted)" }} />
            <span className="label-caps" style={{ color: "var(--color-text-muted)" }}>
              Checking communications readiness…
            </span>
          </div>
        ) : (
          <div
            className="chamfer-8 flex items-center justify-between px-5 py-4 border"
            style={{ borderColor: overallColor, backgroundColor: "var(--color-bg-panel)" }}
          >
            <div className="flex items-center gap-3">
              <span className="h-3 w-3 rounded-full" style={{ backgroundColor: overallColor }} />
              <span className="label-caps" style={{ color: overallColor, fontWeight: 700, fontSize: "var(--text-label)" }}>
                {overallLabel}
              </span>
            </div>
            {blocksRelease && (
              <span
                className="label-caps px-2 py-1 chamfer-4"
                style={{
                  backgroundColor: "rgba(255,45,45,0.1)",
                  color: "var(--color-brand-red)",
                  fontSize: "var(--text-micro)",
                  border: "1px solid var(--color-brand-red)",
                }}
              >
                Release Blocker
              </span>
            )}
          </div>
        )}

        {/* Checks */}
        <div
          className="chamfer-8 border overflow-hidden"
          style={{
            backgroundColor: "var(--color-bg-panel)",
            borderColor: "var(--color-border-default)",
          }}
        >
          <div className="px-5 py-3 border-b" style={{ borderColor: "var(--color-border-default)" }}>
            <span className="label-caps" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-label)" }}>
              Telnyx Readiness Checks
            </span>
          </div>
          {loading ? (
            <div className="px-5 py-8 text-center" style={{ color: "var(--color-text-muted)" }}>
              Running communications checks…
            </div>
          ) : (
            checks.map((c) => <CheckRow key={c.label} check={c} />)
          )}
        </div>

        {/* Production Number */}
        <div
          className="chamfer-8 border px-5 py-4"
          style={{
            backgroundColor: "var(--color-bg-panel)",
            borderColor: "var(--color-border-default)",
          }}
        >
          <span className="label-caps" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-label)" }}>
            Production Number
          </span>
          <div
            className="mt-2"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--text-h3)",
              color: "var(--color-brand-orange)",
              fontWeight: 700,
            }}
          >
            +1-888-365-0144
          </div>
          <p className="mt-1" style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
            Primary Telnyx number for voice and SMS operations
          </p>
        </div>

        <div className="text-center pt-2">
          <span style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
            FusionEMS Quantum Communications — Operator-grade readiness verification
          </span>
        </div>
      </div>
    </div>
  );
}
