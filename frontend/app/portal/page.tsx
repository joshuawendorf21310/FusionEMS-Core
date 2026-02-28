'use client';

import React from 'react';
import Link from 'next/link';

const STAT_CARDS = [
  { label: 'Active Incidents', value: '--', href: '/portal/incidents' },
  { label: 'Pending Claims', value: '--', href: '/portal/billing' },
  { label: 'Unmatched Faxes', value: '--', href: '/portal/fax-inbox' },
  { label: 'Open Support Threads', value: '--', href: '/portal/support' },
  { label: 'Active Patients', value: '--', href: '/portal/patients' },
  { label: 'Pending EDI Batches', value: '--', href: '/portal/edi' },
];

export default function PortalDashboardPage() {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-text-primary">Agency Dashboard</h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-0.5">data loads from API</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {STAT_CARDS.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="group block bg-bg-void border border-border-DEFAULT rounded-sm p-5 hover:border-[rgba(255,107,26,0.35)] transition-colors"
          >
            <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.4)] mb-3 group-hover:text-[rgba(255,107,26,0.7)] transition-colors">
              {card.label}
            </div>
            <div className="text-3xl font-bold text-text-primary">{card.value}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
