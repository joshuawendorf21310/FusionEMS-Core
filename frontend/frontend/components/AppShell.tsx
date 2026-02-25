"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";

export type SystemStatus =
  | "ACTIVE"
  | "CERTIFICATION_ACTIVATION_REQUIRED"
  | "ARCHITECTURE_COMPLETE"
  | "ACTIVE_CORE_LAYER"
  | "IN_DEVELOPMENT"
  | "INFRASTRUCTURE_LAYER";

export function StatusBadge({ status, accent }: { status: SystemStatus; accent: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs"
      style={{ borderColor: "rgba(255,255,255,0.12)" }}>
      <span className="h-2 w-2 rounded-full" style={{ background: accent }} />
      <span className="text-[rgba(255,255,255,0.78)]">{status.replaceAll("_", " ")}</span>
    </span>
  );
}

export function ModalContainer({
  open, title, body, onClose, ctaLabel
}: {
  open: boolean; title: string; body: string; onClose: () => void; ctaLabel?: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(0,0,0,0.65)] p-4">
      <div className="w-full max-w-xl rounded-2xl border border-border bg-panel shadow-2xl">
        <div className="border-b border-border p-5">
          <div className="text-lg font-semibold">{title}</div>
        </div>
        <div className="p-5 text-sm text-muted whitespace-pre-wrap">{body}</div>
        <div className="flex justify-end gap-3 border-t border-border p-4">
          <button onClick={onClose} className="rounded-xl border border-border px-4 py-2 text-sm">
            {ctaLabel ?? "Return"}
          </button>
        </div>
      </div>
    </div>
  );
}

function NavLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="rounded-lg px-3 py-2 text-sm text-muted hover:text-text hover:bg-[rgba(255,255,255,0.06)]">
      {label}
    </Link>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-border bg-[rgba(11,15,20,0.9)] backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl border border-border bg-panel2 flex items-center justify-center font-bold">
              FQ
            </div>
            <div>
              <div className="text-sm font-semibold leading-4">FusionEMS Quantum</div>
              <div className="text-xs text-muted">Billing-first infrastructure OS</div>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-1">
            <NavLink href="/" label="Platform" />
            <NavLink href="/billing" label="Billing" />
            <NavLink href="/systems" label="Systems" />
            <NavLink href="/compliance" label="Compliance" />
            <NavLink href="/architecture" label="Architecture" />
            <NavLink href="/founder" label="Founder Command" />
          </nav>

          <div className="flex items-center gap-2">
            <Link href="/portal/patient" className="rounded-xl border border-border px-3 py-2 text-sm text-muted hover:text-text">
              Pay My Bill
            </Link>
            <Link href="/billing/login" className="rounded-xl border border-border px-3 py-2 text-sm text-muted hover:text-text">
              Billing Login
            </Link>
            <button
              onClick={() => setCmdPaletteOpen(true)}
              className="rounded-xl bg-billing px-4 py-2 text-sm font-semibold text-black hover:opacity-90"
            >
              Command
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-6">
        {children}
      </main>

      <footer className="border-t border-border bg-[rgba(11,15,20,0.8)]">
        <div className="mx-auto max-w-7xl px-5 py-5 text-xs text-muted flex flex-wrap items-center justify-between gap-3">
          <div>Billing Engine: Active · Compliance Layer: Monitoring · System Status: Operational</div>
          <div>Quantum v1.0</div>
        </div>
      </footer>

      <ModalContainer
        open={cmdPaletteOpen}
        title="Founder Command Shortcuts"
        body={"This is a minimal command surface. Use Founder Command Center for full control."}
        onClose={() => setCmdPaletteOpen(false)}
        ctaLabel="Close"
      />
    </div>
  );
}
