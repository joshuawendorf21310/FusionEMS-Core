'use client';

import React from 'react';
import Link from 'next/link';
import AppShell from '@/components/AppShell';

const NAV_CARDS = [
  {
    href: '/billing/dashboard',
    title: 'Dashboard',
    description: 'KPIs, AR aging, collection metrics',
    accent: '#22d3ee',
  },
  {
    href: '/billing/claims',
    title: 'Claims',
    description: 'Active, pending, denied claim management',
    accent: '#22d3ee',
  },
  {
    href: '/billing/documents',
    title: 'Documents',
    description: 'PCRs, ABNs, authorizations, attachments',
    accent: '#22d3ee',
  },
  {
    href: '/billing/reports',
    title: 'Reports',
    description: 'Payer mix, denial analysis, productivity',
    accent: '#22d3ee',
  },
  {
    href: '/billing-command',
    title: 'Command Center',
    description: 'Full billing intelligence dashboard',
    accent: '#ff6b1a',
  },
  {
    href: '/compliance',
    title: 'Compliance',
    description: 'HIPAA, billing compliance monitoring',
    accent: '#a855f7',
  },
];

const QUICK_STATS = [
  { label: 'Monthly Revenue', value: '$2,847,391', unit: 'USD', accent: '#22d3ee' },
  { label: 'Clean Claim Rate', value: '94.2', unit: '%', accent: '#4caf50' },
  { label: 'Days in AR', value: '28.4', unit: 'days', accent: '#ff9800' },
  { label: 'Denial Rate', value: '3.8', unit: '%', accent: '#e53935' },
];

export default function BillingPage() {
  return (
    <AppShell>
      <div
        className="min-h-screen"
        style={{ background: 'var(--color-bg-base)', color: 'var(--color-text-primary)' }}
      >
        {/* Page Header */}
        <div
          className="hud-rail mb-8 pb-4"
          style={{ borderBottom: '1px solid var(--color-border-default)' }}
        >
          <div className="micro-caps mb-1" style={{ color: 'var(--color-system-billing)' }}>
            Revenue Cycle Management
          </div>
          <h1
            className="label-caps"
            style={{
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-h1)',
              fontWeight: 700,
              letterSpacing: 'var(--tracking-label)',
              textTransform: 'uppercase',
              color: 'var(--color-text-primary)',
              marginBottom: '4px',
            }}
          >
            Billing Command
          </h1>
          <p style={{ fontSize: 'var(--text-body)', color: 'var(--color-text-secondary)' }}>
            End-to-end revenue cycle management
          </p>
        </div>

        {/* Nav Cards Grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-10">
          {NAV_CARDS.map((card) => (
            <Link key={card.href} href={card.href} style={{ textDecoration: 'none' }}>
              <div
                style={{
                  background: 'var(--color-bg-panel)',
                  clipPath: 'var(--chamfer-8)',
                  borderLeft: `3px solid ${card.accent}`,
                  padding: '20px 24px',
                  cursor: 'pointer',
                  transition: 'background var(--duration-fast) var(--ease-out)',
                  boxShadow: 'var(--elevation-1)',
                  position: 'relative',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLDivElement).style.background =
                    'var(--color-bg-panel-raised)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLDivElement).style.background = 'var(--color-bg-panel)';
                }}
              >
                <div className="flex items-start justify-between mb-2">
                  <span
                    style={{
                      fontFamily: 'var(--font-label)',
                      fontSize: 'var(--text-body-lg)',
                      fontWeight: 700,
                      letterSpacing: 'var(--tracking-label)',
                      textTransform: 'uppercase',
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    {card.title}
                  </span>
                  <span
                    style={{
                      color: card.accent,
                      fontSize: '18px',
                      lineHeight: 1,
                      opacity: 0.8,
                    }}
                    aria-hidden="true"
                  >
                    &#x2192;
                  </span>
                </div>
                <p
                  style={{
                    fontSize: 'var(--text-body)',
                    color: 'var(--color-text-secondary)',
                    margin: 0,
                  }}
                >
                  {card.description}
                </p>
              </div>
            </Link>
          ))}
        </div>

        {/* Quick Stats */}
        <div className="mb-2">
          <div
            className="label-caps mb-4"
            style={{ color: 'var(--color-text-muted)', letterSpacing: 'var(--tracking-label)' }}
          >
            Quick Stats
          </div>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {QUICK_STATS.map((stat) => (
              <div
                key={stat.label}
                style={{
                  background: 'var(--color-bg-panel)',
                  clipPath: 'var(--chamfer-8)',
                  padding: '20px',
                  borderTop: `2px solid ${stat.accent}`,
                  boxShadow: 'var(--elevation-1)',
                }}
              >
                <div
                  className="micro-caps mb-2"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  {stat.label}
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 'var(--text-h2)',
                    fontWeight: 700,
                    color: stat.accent,
                    lineHeight: 1.1,
                  }}
                >
                  {stat.value}
                </div>
                <div
                  style={{
                    fontSize: 'var(--text-micro)',
                    color: 'var(--color-text-muted)',
                    marginTop: '4px',
                    textTransform: 'uppercase',
                    letterSpacing: 'var(--tracking-micro)',
                  }}
                >
                  {stat.unit}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
