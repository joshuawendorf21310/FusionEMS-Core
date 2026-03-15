"use client";

import { useEffect, useState } from "react";

type ServiceStatus = "operational" | "degraded" | "down" | "unknown";

interface ServiceCheck {
  label: string;
  status: ServiceStatus;
  detail: string;
}

const STATUS_COLORS: Record<ServiceStatus, string> = {
  operational: "var(--color-status-active)",
  degraded: "var(--color-status-warning)",
  down: "var(--color-status-critical)",
  unknown: "var(--color-text-muted)",
};

const STATUS_LABELS: Record<ServiceStatus, string> = {
  operational: "Operational",
  degraded: "Degraded",
  down: "Down",
  unknown: "Unknown",
};

function StatusRow({ check }: { check: ServiceCheck }) {
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

function useServiceChecks() {
  const [services, setServices] = useState<ServiceCheck[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function run() {
      const results: ServiceCheck[] = [];

      // Frontend
      results.push({ label: "Frontend Application", status: "operational", detail: "Running" });

      // Backend
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
        const res = await fetch(`${apiUrl}/api/v1/health`, { signal: AbortSignal.timeout(5000) });
        results.push({
          label: "Backend API",
          status: res.ok ? "operational" : "degraded",
          detail: res.ok ? "Healthy" : `Status ${res.status}`,
        });
      } catch {
        results.push({ label: "Backend API", status: "unknown", detail: "Unreachable" });
      }

      // Auth
      const token = localStorage.getItem("fusionems_token") || localStorage.getItem("token");
      results.push({
        label: "Auth — Session",
        status: token ? "operational" : "degraded",
        detail: token ? "Token active" : "No active session",
      });

      // Microsoft Login
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
        const msRes = await fetch(`${apiUrl}/api/v1/auth/microsoft/login`, { method: "HEAD", redirect: "manual" });
        results.push({
          label: "Microsoft Entra Login",
          status: msRes.status === 200 || msRes.status === 302 || msRes.type === "opaqueredirect" ? "operational" : "degraded",
          detail: `Endpoint available`,
        });
      } catch {
        results.push({ label: "Microsoft Entra Login", status: "unknown", detail: "Unreachable" });
      }

      // Communications — Telnyx
      results.push({
        label: "Telnyx Voice — +1-888-365-0144",
        status: "unknown",
        detail: "Requires runtime verification",
      });

      results.push({
        label: "Telnyx Messaging — +1-888-365-0144",
        status: "unknown",
        detail: "Requires runtime verification",
      });

      // Release info
      results.push({
        label: "Release Gate",
        status: "unknown",
        detail: "Pending release_runtime_validation",
      });

      results.push({
        label: "Rollback Readiness",
        status: "unknown",
        detail: "Requires deployment history",
      });

      setServices(results);
      setLoading(false);
    }

    run();
  }, []);

  return { services, loading };
}

export default function LiveStatusPage() {
  const { services, loading } = useServiceChecks();

  const allOperational = services.length > 0 && services.every((s) => s.status === "operational");
  const hasDown = services.some((s) => s.status === "down");
  const hasUnknown = services.some((s) => s.status === "unknown");

  let overallLabel = "All Systems Operational";
  let overallColor = "var(--color-status-active)";

  if (hasDown) {
    overallLabel = "System Incident Detected";
    overallColor = "var(--color-status-critical)";
  } else if (hasUnknown) {
    overallLabel = "Health Checks Incomplete";
    overallColor = "var(--color-text-muted)";
  } else if (!allOperational) {
    overallLabel = "Partial Degradation";
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
              Live Status
            </h1>
          </div>
          <p className="mt-1" style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
            Authenticated operational status — FusionEMS Quantum
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
              Running service checks…
            </span>
          </div>
        ) : (
          <div
            className="chamfer-8 flex items-center gap-3 px-5 py-4 border"
            style={{ borderColor: overallColor, backgroundColor: "var(--color-bg-panel)" }}
          >
            <span className="h-3 w-3 rounded-full" style={{ backgroundColor: overallColor }} />
            <span
              className="label-caps"
              style={{ color: overallColor, fontWeight: 700, fontSize: "var(--text-label)" }}
            >
              {overallLabel}
            </span>
          </div>
        )}

        {/* Service List */}
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
            <span className="label-caps" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-label)" }}>
              Service Health
            </span>
          </div>
          {loading ? (
            <div className="px-5 py-8 text-center" style={{ color: "var(--color-text-muted)" }}>
              Checking services…
            </div>
          ) : (
            services.map((s) => <StatusRow key={s.label} check={s} />)
          )}
        </div>

        {/* Incidents */}
        <div
          className="chamfer-8 border overflow-hidden"
          style={{
            backgroundColor: "var(--color-bg-panel)",
            borderColor: "var(--color-border-default)",
          }}
        >
          <div className="px-5 py-3 border-b" style={{ borderColor: "var(--color-border-default)" }}>
            <span className="label-caps" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-label)" }}>
              Active Incidents
            </span>
          </div>
          <div className="px-5 py-6 text-center" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-body)" }}>
            No active incidents.
          </div>
        </div>

        <div className="text-center pt-2">
          <span style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
            FusionEMS Quantum Live Status — Real-time service and deployment health
          </span>
        </div>
      </div>
    </div>
  );
}
