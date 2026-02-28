'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_LINKS = [
  { href: '/portal', label: 'Dashboard' },
  { href: '/portal/incidents', label: 'Incidents' },
  { href: '/portal/patients', label: 'Patients' },
  { href: '/portal/billing', label: 'Billing' },
  { href: '/portal/fax-inbox', label: 'Fax Inbox' },
  { href: '/portal/edi', label: 'EDI' },
  { href: '/portal/support', label: 'Support' },
  { href: '/portal/documents', label: 'Documents' },
  { href: '/portal/neris-onboarding', label: 'NERIS Onboarding' },
  { href: '/portal/incidents/fire', label: 'Fire Incidents' },
  { href: '/portal/cases', label: 'Cases' },
  { href: '/portal/hems', label: 'HEMS Pilot' },
  { href: '/portal/fleet', label: 'Fleet Intelligence' },
  { href: '/portal/scheduling', label: 'Scheduling' },
  { href: '/portal/billing-ops', label: 'Billing Ops' },
  { href: '/portal/trip', label: 'TRIP (WI)' },
  { href: '/portal/kitlink', label: 'KitLink AR' },
];

function TopBar() {
  return (
    <header className="flex-shrink-0 flex items-center justify-between px-5 h-12 border-b border-border-DEFAULT bg-bg-void">
      <Link href="/portal" className="flex items-center gap-2">
        <div
          className="w-7 h-7 bg-orange flex items-center justify-center text-[10px] font-black text-text-inverse"
          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
        >
          FQ
        </div>
        <span className="text-xs font-semibold text-[rgba(255,255,255,0.9)]">Agency Portal</span>
      </Link>

      <div className="flex items-center gap-3">
        <button
          className="relative w-8 h-8 flex items-center justify-center text-[rgba(255,255,255,0.5)] hover:text-text-primary transition-colors"
          aria-label="Notifications"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-orange" />
        </button>
        <button className="h-7 px-3 bg-[rgba(255,255,255,0.06)] border border-border-DEFAULT text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.7)] hover:text-text-primary hover:bg-[rgba(255,255,255,0.1)] transition-colors rounded-sm">
          Logout
        </button>
      </div>
    </header>
  );
}

function Sidebar({ currentPath }: { currentPath: string }) {
  return (
    <aside className="w-48 flex-shrink-0 border-r border-border-subtle bg-bg-void flex flex-col overflow-y-auto">
      <nav className="px-2 py-4 space-y-0.5">
        {NAV_LINKS.map((link) => {
          const active = currentPath === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`block px-3 py-2 text-xs rounded-sm transition-colors ${
                active
                  ? 'text-text-primary bg-orange-ghost border-l-2 border-orange pl-2'
                  : 'text-[rgba(255,255,255,0.5)] hover:text-text-primary hover:bg-[rgba(255,255,255,0.05)]'
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-screen bg-bg-void text-text-primary overflow-hidden">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar currentPath={pathname} />
        <main className="flex-1 overflow-y-auto bg-bg-base">
          {children}
        </main>
      </div>
    </div>
  );
}
