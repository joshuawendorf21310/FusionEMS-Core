"use client";

import { useEffect, useState } from "react";

type CheckStatus = "operational" | "degraded" | "down" | "unknown";

interface HealthCheck {
  label: string;
  status: CheckStatus;
  detail: string;
  lastChecked: string | null;
}

const STATUS_COLORS: Record<CheckStatus, string> = {
  operational: "var(--color-status-active)",
  degraded: "var(--color-status-warning)",
  down: "var(--color-status-critical)",
  unknown: "var(--color-text-muted)",
};

const STATUS_LABELS: Record<CheckStatus, string> = {
  operational: "Operational",
  degraded: "Degraded",
  down: "Down",
  unknown: "Unknown",
};

function StatusDot({ status }: { status: CheckStatus }) {
  return (
    <span
      className="inline-block h-2.5 w-2.5 rounded-full"
      style={{ backgroundColor: STATUS_COLORS[status] }}
    />
  );
}

function OverallBanner({ checks }: { checks: HealthCheck[] }) {
  const allOperational = checks.length > 0 && checks.every((c) => c.status === "operational");
  const hasDown = checks.some((c) => c.status === "down");
  const hasUnknown = checks.some((c) => c.status === "unknown");

  let message = "All Systems Operational";
  let color = "var(--color-status-active)";

  if (hasDown) {
    message = "System Incident Detected";
    color = "var(--color-status-critical)";
  } else if (hasUnknown) {
    message = "Health Status Pending — Checks Incomplete";
    color = "var(--color-text-muted)";
  } else if (!allOperational) {
    message = "Partial Degradation Detected";
    color = "var(--color-status-warning)";
  }

  return (
    <div
      className="chamfer-8 flex items-center gap-3 px-5 py-4 border"
      style={{
        borderColor: color,
        backgroundColor: "var(--color-bg-panel)",
      }}
    >
      <span className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
      <span
        className="label-caps"
        style={{ color, fontWeight: 700, fontSize: "var(--text-label)" }}
      >
        {message}
      </span>
    </div>
  );
}

function CheckRow({ check }: { check: HealthCheck }) {
  return (
    <div
      className="flex items-center justify-between px-5 py-3 border-b"
      style={{ borderColor: "var(--color-border-subtle)" }}
    >
      <div className="flex items-center gap-3">
        <StatusDot status={check.status} />
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

function SectionPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      className="chamfer-8 border overflow-hidden"
      style={{
        backgroundColor: "var(--color-bg-panel)",
        borderColor: "var(--color-border-default)",
      }}
    >
      <div
        className="px-5 py-3 border-b"
        style={{ borderColor: "var(--color-border-default)" }}
      >
        <span
          className="label-caps"
          style={{ color: "var(--color-text-muted)", fontSize: "var(--text-label)" }}
        >
          {title}
        </span>
      </div>
      <div>{children}</div>
    </div>
  );
}

function useHealthChecks() {
  const [checks, setChecks] = useState<HealthCheck[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function runChecks() {
      const results: HealthCheck[] = [];
      const now = new Date().toISOString();

      // Auth Health
      try {
        const token = localStorage.getItem("fusionems_token") || localStorage.getItem("token");
        results.push({
          label: "Auth — Session Token",
          status: token ? "operational" : "degraded",
          detail: token ? "Token present" : "No active session",
          lastChecked: now,
        });
      } catch {
        results.push({ label: "Auth — Session Token", status: "unknown", detail: "Check failed", lastChecked: now });
      }

      // Microsoft Login Health
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
        const msRes = await fetch(`${apiUrl}/api/v1/auth/microsoft/login`, { method: "HEAD", redirect: "manual" });
        results.push({
          label: "Microsoft Entra Login",
          status: msRes.status === 200 || msRes.status === 302 || msRes.type === "opaqueredirect" ? "operational" : "degraded",
          detail: `Endpoint responded (${msRes.status || "redirect"})`,
          lastChecked: now,
        });
      } catch {
        results.push({ label: "Microsoft Entra Login", status: "unknown", detail: "Endpoint unreachable", lastChecked: now });
      }

      // Backend Health
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
        const healthRes = await fetch(`${apiUrl}/api/v1/health`, { signal: AbortSignal.timeout(5000) });
        results.push({
          label: "Backend API",
          status: healthRes.ok ? "operational" : "degraded",
          detail: healthRes.ok ? "Healthy" : `Status ${healthRes.status}`,
          lastChecked: now,
        });
      } catch {
        results.push({ label: "Backend API", status: "unknown", detail: "Unreachable", lastChecked: now });
      }

      // Frontend Health
      results.push({
        label: "Frontend Application",
        status: "operational",
        detail: "Running",
        lastChecked: now,
      });

      // Communications — Telnyx
      results.push({
        label: "Communications — Telnyx (+1-888-365-0144)",
        status: "unknown",
        detail: "Requires runtime verification",
        lastChecked: now,
      });

      // NEMSIS Readiness
      results.push({
        label: "NEMSIS Compliance Engine",
        status: "unknown",
        detail: "Requires runtime verification",
        lastChecked: now,
      });

      // Release State
      results.push({
        label: "Release Gate",
        status: "unknown",
        detail: "Requires release_runtime_validation",
        lastChecked: now,
      });

      setChecks(results);
      setLoading(false);
    }

    runChecks();
  }, []);

  return { checks, loading };
}

export default function CommandCenterPage() {
  const { checks, loading } = useHealthChecks();

  const platformChecks = checks.filter((c) =>
    ["Auth — Session Token", "Microsoft Entra Login", "Backend API", "Frontend Application"].includes(c.label)
  );
  const operationalChecks = checks.filter((c) =>
    ["Communications — Telnyx (+1-888-365-0144)", "NEMSIS Compliance Engine", "Release Gate"].includes(c.label)
  );

  return (
    <div
      className="min-h-screen px-6 py-8"
      style={{ backgroundColor: "var(--color-bg-void)" }}
    >
      <div className="mx-auto max-w-5xl space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-2">
          <div
            className="chamfer-4 flex h-9 w-9 items-center justify-center"
            style={{
              backgroundColor: "var(--color-brand-orange)",
              color: "var(--color-text-inverse)",
              fontWeight: 700,
              fontSize: "var(--text-label)",
              letterSpacing: "var(--tracking-label)",
            }}
          >
            FQ
          </div>
          <div>
            <h1
              style={{
                fontFamily: "var(--font-label)",
                fontSize: "var(--text-h2)",
                fontWeight: 700,
                color: "var(--color-text-primary)",
                letterSpacing: "0.02em",
              }}
            >
              Command Center
            </h1>
            <p style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
              FusionEMS Quantum — Platform Readiness &amp; Operational Overview
            </p>
          </div>
        </div>

        {/* Overall Status */}
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
              Running health checks…
            </span>
          </div>
        ) : (
          <OverallBanner checks={checks} />
        )}

        {/* Platform Health */}
        <SectionPanel title="Platform Health">
          {loading ? (
            <div className="px-5 py-6 text-center" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-body)" }}>
              Checking platform health…
            </div>
          ) : (
            platformChecks.map((c) => <CheckRow key={c.label} check={c} />)
          )}
        </SectionPanel>

        {/* Operational Readiness */}
        <SectionPanel title="Operational Readiness">
          {loading ? (
            <div className="px-5 py-6 text-center" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-body)" }}>
              Checking operational readiness…
            </div>
          ) : (
            operationalChecks.map((c) => <CheckRow key={c.label} check={c} />)
          )}
        </SectionPanel>

        {/* Incidents & Blockers */}
        <SectionPanel title="Incidents & Blockers">
          <div className="px-5 py-6 text-center" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-body)" }}>
            No active incidents or blockers.
          </div>
        </SectionPanel>

        {/* Footer */}
        <div className="text-center pt-2">
          <span style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
            FusionEMS Quantum Command Center — Real-time platform health and operational readiness
          </span>
        </div>
      </div>
    </div>
  );
}
