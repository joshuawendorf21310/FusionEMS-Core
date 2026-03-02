'use client';

import React from 'react';
import AppShell from '@/components/AppShell';

const KPI_CARDS = [
  { label: 'MRR', value: '$2,847,391', sub: 'Monthly Recurring Revenue', accent: 'var(--color-status-info)' },
  { label: 'YTD Revenue', value: '$31,204,770', sub: 'Year-to-date collected', accent: 'var(--color-status-info)' },
  { label: 'Clean Claim Rate', value: '94.2%', sub: 'First-pass acceptance', accent: 'var(--color-status-active)' },
  { label: 'Avg Days in AR', value: '28.4', sub: 'Days outstanding', accent: 'var(--color-status-warning)' },
  { label: 'Denial Rate', value: '3.8%', sub: 'Claims denied by payer', accent: 'var(--color-brand-red)' },
  { label: 'Collection Rate', value: '91.7%', sub: 'Net collection efficiency', accent: 'var(--color-status-info)' },
];

const AR_AGING = [
  { bucket: '0 – 30 Days', count: 1842, amount: '$1,204,388', pct: '42.3%' },
  { bucket: '31 – 60 Days', count: 934, amount: '$689,241', pct: '24.2%' },
  { bucket: '61 – 90 Days', count: 521, amount: '$398,112', pct: '14.0%' },
  { bucket: '91 – 120 Days', count: 318, amount: '$261,804', pct: '9.2%' },
  { bucket: '120+ Days', count: 294, amount: '$293,477', pct: '10.3%' },
];

const PAYER_PERF = [
  { payer: 'Medicare', submitted: '$1,182,440', paid: '$1,049,822', denial: '2.1%', avgDays: 21 },
  { payer: 'Medicaid', submitted: '$634,200', paid: '$521,410', denial: '5.8%', avgDays: 34 },
  { payer: 'BCBS', submitted: '$488,760', paid: '$441,200', denial: '3.4%', avgDays: 27 },
  { payer: 'UHC', submitted: '$374,100', paid: '$330,480', denial: '4.2%', avgDays: 31 },
  { payer: 'Aetna', submitted: '$298,880', paid: '$266,014', denial: '3.9%', avgDays: 29 },
  { payer: 'Self-Pay', submitted: '$187,340', paid: '$94,210', denial: '0.0%', avgDays: 62 },
];

const TH_STYLE: React.CSSProperties = {
  padding: '10px 12px',
  textAlign: 'left',
  fontFamily: 'var(--font-label)',
  fontSize: 'var(--text-label)',
  fontWeight: 600,
  letterSpacing: 'var(--tracking-label)',
  textTransform: 'uppercase',
  color: 'var(--color-text-muted)',
  background: 'var(--color-bg-panel-raised)',
  whiteSpace: 'nowrap',
};

const TD_STYLE: React.CSSProperties = {
  padding: '10px 12px',
  fontSize: 'var(--text-body)',
  color: 'var(--color-text-secondary)',
  borderTop: '1px solid var(--color-border-subtle)',
};

const TD_MONO: React.CSSProperties = {
  ...TD_STYLE,
  fontFamily: 'var(--font-mono)',
  color: 'var(--color-text-primary)',
};

export default function BillingDashboardPage() {
  return (
    <AppShell>
      <div style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-sans)' }}>
        {/* Header */}
        <div
          className="hud-rail mb-8 pb-4"
          style={{ borderBottom: '1px solid var(--color-border-default)' }}
        >
          <div className="micro-caps mb-1" style={{ color: 'var(--color-system-billing)' }}>
            Revenue Cycle
          </div>
          <h1
            style={{
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-h1)',
              fontWeight: 700,
              letterSpacing: 'var(--tracking-label)',
              textTransform: 'uppercase',
              color: 'var(--color-text-primary)',
              margin: 0,
            }}
          >
            Billing Dashboard
          </h1>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 mb-10">
          {KPI_CARDS.map((kpi) => (
            <div
              key={kpi.label}
              style={{
                background: 'var(--color-bg-panel)',
                clipPath: 'var(--chamfer-8)',
                borderLeft: `3px solid ${kpi.accent}`,
                padding: '20px',
                boxShadow: 'var(--elevation-1)',
              }}
            >
              <div className="micro-caps mb-1" style={{ color: 'var(--color-text-muted)' }}>
                {kpi.label}
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--text-h2)',
                  fontWeight: 700,
                  color: kpi.accent,
                  lineHeight: 1.1,
                  marginBottom: '4px',
                }}
              >
                {kpi.value}
              </div>
              <div
                style={{
                  fontSize: 'var(--text-body)',
                  color: 'var(--color-text-muted)',
                }}
              >
                {kpi.sub}
              </div>
            </div>
          ))}
        </div>

        {/* AR Aging */}
        <div className="mb-8">
          <div className="label-caps mb-4" style={{ color: 'var(--color-text-muted)', letterSpacing: 'var(--tracking-label)' }}>
            AR Aging
          </div>
          <div
            style={{
              background: 'var(--color-bg-panel)',
              clipPath: 'var(--chamfer-8)',
              overflow: 'hidden',
              boxShadow: 'var(--elevation-1)',
            }}
          >
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={TH_STYLE}>Age Bucket</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Count</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Amount</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>% of Total</th>
                </tr>
              </thead>
              <tbody>
                {AR_AGING.map((row, i) => (
                  <tr
                    key={row.bucket}
                    style={{
                      background:
                        i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                    }}
                  >
                    <td style={TD_STYLE}>{row.bucket}</td>
                    <td style={{ ...TD_MONO, textAlign: 'right' }}>{row.count.toLocaleString()}</td>
                    <td style={{ ...TD_MONO, textAlign: 'right', color: 'var(--color-system-billing)' }}>{row.amount}</td>
                    <td style={{ ...TD_STYLE, textAlign: 'right' }}>{row.pct}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Payer Performance */}
        <div className="mb-8">
          <div className="label-caps mb-4" style={{ color: 'var(--color-text-muted)', letterSpacing: 'var(--tracking-label)' }}>
            Payer Performance
          </div>
          <div
            style={{
              background: 'var(--color-bg-panel)',
              clipPath: 'var(--chamfer-8)',
              overflow: 'hidden',
              boxShadow: 'var(--elevation-1)',
            }}
          >
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={TH_STYLE}>Payer Name</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Submitted</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Paid</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Denial Rate</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Avg Days</th>
                </tr>
              </thead>
              <tbody>
                {PAYER_PERF.map((row, i) => {
                  const denialNum = parseFloat(row.denial);
                  const denialColor =
                    denialNum > 5
                      ? 'var(--color-brand-red)'
                      : denialNum > 3
                      ? 'var(--color-status-warning)'
                      : 'var(--color-status-active)';
                  return (
                    <tr
                      key={row.payer}
                      style={{
                        background:
                          i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                      }}
                    >
                      <td
                        style={{
                          ...TD_STYLE,
                          fontWeight: 600,
                          color: 'var(--color-text-primary)',
                        }}
                      >
                        {row.payer}
                      </td>
                      <td style={{ ...TD_MONO, textAlign: 'right' }}>{row.submitted}</td>
                      <td style={{ ...TD_MONO, textAlign: 'right', color: 'var(--color-status-active)' }}>
                        {row.paid}
                      </td>
                      <td
                        style={{
                          ...TD_MONO,
                          textAlign: 'right',
                          color: denialColor,
                        }}
                      >
                        {row.denial}
                      </td>
                      <td style={{ ...TD_MONO, textAlign: 'right' }}>{row.avgDays}d</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
