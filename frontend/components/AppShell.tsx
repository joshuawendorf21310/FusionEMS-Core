"use client";

import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

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

export function ModalContainer({
  open,
  title,
  body,
  onClose,
  ctaLabel,
}: {
  open: boolean;
  title: string;
  body: string;
  onClose: () => void;
  ctaLabel?: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-md rounded border border-[rgba(255,255,255,0.1)] bg-[#111] p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        <p className="mt-3 text-sm text-[rgba(255,255,255,0.6)] leading-relaxed">{body}</p>
        <button
          onClick={onClose}
          className="mt-6 w-full rounded bg-[#FF6B00] px-4 py-2.5 text-sm font-semibold text-black transition-colors hover:bg-[#FF7B10]"
        >
          {ctaLabel || "Close"}
        </button>
      </div>
    </div>
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
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="h-9 w-9 bg-[#FF6B00] flex items-center justify-center font-bold text-black text-sm">
              FQ
            </div>
            <div>
              <div className="text-sm font-semibold uppercase tracking-wider">FusionEMS Quantum</div>
              <div className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wide">Platform Command</div>
            </div>
          </Link>

          <nav className="hidden lg:flex items-center gap-1">
            <NavLink href="/command-center" label="Command" />
            <NavLink href="/billing-command" label="Billing" />
            <NavLink href="/compliance" label="Compliance" />
            <NavLink href="/systems" label="Systems" />
            <NavLink href="/live-status" label="Status" />
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

/* ─── ModalContainer ─────────────────────────────────────────────────────────
   Lightweight gate modal used by certification-gated system pages.
   Renders a backdrop + panel with a title, body text, and a CTA button.
─────────────────────────────────────────────────────────────────────────────── */
export interface ModalContainerProps {
  open: boolean;
  title: string;
  body: string;
  onClose: () => void;
  ctaLabel?: string;
}

export function ModalContainer({ open, title, body, onClose, ctaLabel = "Close" }: ModalContainerProps) {
  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="relative z-10 w-full max-w-lg mx-4 bg-[#111827] border border-[rgba(255,255,255,0.08)] shadow-[0_16px_40px_rgba(0,0,0,0.7)]"
        style={{ clipPath: "polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)" }}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-[rgba(255,255,255,0.08)]">
          <h2
            id="modal-title"
            className="text-xs font-semibold uppercase tracking-[0.08em] text-[#E5E7EB]"
          >
            {title}
          </h2>
          <button
            onClick={onClose}
            className="text-[rgba(255,255,255,0.4)] hover:text-white transition-colors p-1"
            aria-label="Close"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M4 4l8 8M12 4l-8 8" />
            </svg>
          </button>
        </div>
        <div className="p-5 text-sm text-[rgba(255,255,255,0.7)] leading-relaxed">{body}</div>
        <div className="flex justify-end px-5 pb-5">
          <Button variant="primary" size="md" onClick={onClose}>
            {ctaLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
