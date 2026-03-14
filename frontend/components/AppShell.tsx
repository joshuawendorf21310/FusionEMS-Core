"use client";

import React from "react";
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
    <span className="inline-flex items-center gap-2 rounded border px-3 py-1 text-xs border-[rgba(255,255,255,0.12)]">
      <span className="h-2 w-2 rounded-full" style={{ background: accent }} />
      <span className="text-[rgba(255,255,255,0.78)]">{status.replaceAll("_", " ")}</span>
    </span>
  );
}

function NavLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="px-3 py-2 text-sm text-[rgba(255,255,255,0.6)] hover:text-white transition-colors">
      {label}
    </Link>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-black text-white">
      <header className="border-b border-[rgba(255,255,255,0.08)] bg-black/95 backdrop-blur">
        <div className="mx-auto max-w-7xl px-5 py-4 flex items-center justify-between">
          <Link href="/founder" className="flex items-center gap-3">
            <div className="h-9 w-9 bg-[#FF6B00] flex items-center justify-center font-bold text-black text-sm">
              FQ
            </div>
            <div>
              <div className="text-sm font-semibold uppercase tracking-wider">FusionEMS Quantum</div>
              <div className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wide">Founder Command</div>
            </div>
          </Link>

          <nav className="hidden lg:flex items-center gap-1">
            <NavLink href="/founder" label="Command" />
            <NavLink href="/billing-command" label="Billing" />
            <NavLink href="/compliance" label="Compliance" />
            <NavLink href="/systems" label="Systems" />
            <NavLink href="/mobile-ops" label="Ops" />
          </nav>

          <Link href="/login" className="px-4 py-2 bg-[#FF6B00] text-black text-sm font-semibold hover:bg-[#FF7B10] transition-colors">
            Logout
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-8">
        {children}
      </main>
    </div>
  );
}
