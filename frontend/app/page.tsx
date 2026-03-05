import Link from "next/link";
import { api } from "../components/api";
import { StatusBadge, SystemStatus } from "../components/AppShell";

type SystemRow = {
  system_key: string;
  name: string;
  description: string;
  status: SystemStatus;
  accent: string;
};

function accentFor(key: string): string {
  const m: Record<string,string> = {
    fusionbilling: "var(--color-status-info)",
    fusionems: "var(--color-brand-orange-bright)",
    fusionfire: "var(--color-brand-red)",
    fusionhems: "var(--color-status-warning)",
    fusionfleet: "var(--color-system-fleet)",
    fusioncompliance: "var(--color-system-compliance)",
    fusionai: "var(--color-text-primary)",
    fusioncad: "var(--color-text-muted)"
  };
  return m[key] ?? "var(--color-text-muted)";
}

export default async function Page() {
  let systems: SystemRow[] = [];
  let systemsUnavailable = false;
  const isProd = process.env.NODE_ENV === "production";
  try {
    systems = await api<SystemRow[]>("/api/v1/systems");
  } catch {
    systemsUnavailable = true;
  }

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-border bg-panel p-8">
        <div className="text-3xl font-semibold leading-tight">
          FusionEMS Quantum — Unified Public Safety Operating System
        </div>
        <div className="mt-3 max-w-3xl text-sm text-muted">
          Revenue. Operations. Compliance. Intelligence. Built as Infrastructure. Activated by Certification.
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/billing/dashboard" className="rounded-xl bg-billing px-5 py-3 text-sm font-semibold text-text-inverse">
            Enter Billing Command
          </Link>
          <Link href="/architecture" className="rounded-xl border border-border px-5 py-3 text-sm text-muted hover:text-text">
            View System Architecture
          </Link>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-border bg-panel p-6">
          <div className="text-sm font-semibold">Patient Access</div>
          <div className="mt-2 text-xs text-muted">Secure, minimal, bank-grade patient actions.</div>
          <div className="mt-4 grid gap-2">
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/portal/patient/pay">Pay My Bill</Link>
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/portal/patient/lookup">Look Up My Bill</Link>
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/portal/patient/plan">Start a Payment Plan</Link>
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/portal/patient/receipt">Download Receipt</Link>
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/portal/patient/insurance">Update Insurance</Link>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-panel p-6">
          <div className="text-sm font-semibold">Authorized Representative Portal</div>
          <div className="mt-2 text-xs text-muted">
            Guardians, POA, insurance reps, executors. MFA required. Strictly scoped access.
          </div>
          <div className="mt-4 grid gap-2">
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/portal/rep/login">Rep Login</Link>
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/portal/rep/register">Register</Link>
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/portal/rep/verify">Verify Authorization</Link>
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/portal/rep/upload">Upload Authorization Doc</Link>
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/portal/rep/sign">Sign Billing Documents</Link>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-panel p-6">
          <div className="text-sm font-semibold">Agency / Billing Staff Access</div>
          <div className="mt-2 text-xs text-muted">Operational authority. Billing-first deployment.</div>
          <div className="mt-4 grid gap-2">
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/billing/login">Billing Staff Login</Link>
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/billing/dashboard">Claims Dashboard</Link>
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/billing/reports">Revenue Analytics</Link>
            <Link className="rounded-xl border border-border px-4 py-2 text-sm" href="/billing/documents">Upload PCS Forms</Link>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-panel p-6">
        <div className="flex items-end justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">System Architecture Matrix</div>
            <div className="mt-1 text-xs text-muted">Rendered from the system registry (database-driven).</div>
          </div>
          <Link href="/systems" className="text-xs text-muted hover:text-text">Open full matrix →</Link>
        </div>

        {systemsUnavailable && (
          <div className="mt-4 rounded-xl border border-[rgba(229,57,53,0.35)] bg-[rgba(229,57,53,0.08)] p-4 text-sm text-text">
            <div className="font-semibold">System registry unavailable</div>
            <div className="mt-1 text-xs text-muted">
              The UI is running, but the backend registry endpoint could not be reached. Check API routing and service health.
            </div>
          </div>
        )}

        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {systems.map(s => (
            <Link key={s.system_key} href={`/systems/${s.system_key}`} className="rounded-2xl border border-border bg-panel2 p-4 hover:bg-[rgba(255,255,255,0.04)]">
              <div className="text-sm font-semibold">{s.name}</div>
              <div className="mt-1 text-xs text-muted min-h-[34px]">{s.description}</div>
              <div className="mt-3"><StatusBadge status={s.status} accent={s.accent || accentFor(s.system_key)} /></div>
            </Link>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-panel p-6">
        <div className="text-sm font-semibold">Enterprise Security &amp; Compliance</div>
        <div className="mt-3 text-sm text-muted">
          Built with FedRAMP-aligned controls (NIST 800-53 patterns): zero static cloud credentials, centralized secrets, hardened CI/CD, WAF protection, encrypted data, and continuous vulnerability scanning.
        </div>
        <div className="mt-2 text-xs text-muted italic">
          FedRAMP authorization not currently claimed.
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-panel p-6">
        <div className="text-sm font-semibold">Activation Roadmap</div>
        <div className="mt-3 grid gap-2 text-sm text-muted">
          <div>Phase I — Revenue Infrastructure (Active)</div>
          <div>Phase II — Clinical Documentation Activation</div>
          <div>Phase III — Fire Reporting Activation</div>
          <div>Phase IV — Unified Multi-Agency Deployment</div>
        </div>
      </section>
    </div>
  );
}
