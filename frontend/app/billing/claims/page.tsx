'use client';

import React, { useState } from 'react';
import AppShell from '@/components/AppShell';
import { ClaimStatusChip } from '@/components/ui/StatusChip';

type ClaimStatus = 'clean' | 'pending' | 'denied' | 'appealed';
type PayerFilter = 'All' | 'Medicare' | 'Medicaid' | 'Commercial';
type StatusFilter = 'All' | 'Clean' | 'Pending' | 'Denied' | 'Appealed';

interface Claim {
  id: string;
  patient: string;
  dos: string;
  payer: string;
  amount: string;
  status: ClaimStatus;
}

const CLAIMS: Claim[] = [
  { id: 'CLM-2026-00841', patient: 'P-3821', dos: '02/14/2026', payer: 'Medicare', amount: '$1,842.00', status: 'clean' },
  { id: 'CLM-2026-00840', patient: 'P-0194', dos: '02/14/2026', payer: 'Medicaid', amount: '$934.50', status: 'pending' },
  { id: 'CLM-2026-00839', patient: 'P-7742', dos: '02/13/2026', payer: 'BCBS', amount: '$2,210.00', status: 'denied' },
  { id: 'CLM-2026-00838', patient: 'P-5503', dos: '02/13/2026', payer: 'UHC', amount: '$1,650.75', status: 'appealed' },
  { id: 'CLM-2026-00837', patient: 'P-9918', dos: '02/12/2026', payer: 'Medicare', amount: '$1,720.00', status: 'clean' },
  { id: 'CLM-2026-00836', patient: 'P-2267', dos: '02/12/2026', payer: 'Aetna', amount: '$2,080.00', status: 'pending' },
  { id: 'CLM-2026-00835', patient: 'P-6641', dos: '02/11/2026', payer: 'Medicaid', amount: '$780.25', status: 'denied' },
  { id: 'CLM-2026-00834', patient: 'P-1130', dos: '02/11/2026', payer: 'Medicare', amount: '$1,960.00', status: 'clean' },
  { id: 'CLM-2026-00833', patient: 'P-4487', dos: '02/10/2026', payer: 'BCBS', amount: '$2,340.50', status: 'appealed' },
  { id: 'CLM-2026-00832', patient: 'P-8826', dos: '02/10/2026', payer: 'UHC', amount: '$1,580.00', status: 'clean' },
];

const STATUS_FILTERS: StatusFilter[] = ['All', 'Clean', 'Pending', 'Denied', 'Appealed'];
const PAYER_FILTERS: PayerFilter[] = ['All', 'Medicare', 'Medicaid', 'Commercial'];

const STAT_COUNTS = [
  { label: 'Total Claims', value: '847', color: 'var(--color-text-primary)' },
  { label: 'Clean', value: '712', color: 'var(--color-status-active)' },
  { label: 'Pending', value: '94', color: 'var(--color-status-warning)' },
  { label: 'Denied', value: '41', color: 'var(--color-brand-red)' },
];

const TH: React.CSSProperties = {
  padding: '10px 12px',
  textAlign: 'left',
  fontFamily: 'var(--font-label)',
  fontSize: 'var(--text-label)',
  fontWeight: 600,
  letterSpacing: 'var(--tracking-label)',
  textTransform: 'uppercase' as const,
  color: 'var(--color-text-muted)',
  background: 'var(--color-bg-panel-raised)',
  whiteSpace: 'nowrap' as const,
};

const TD: React.CSSProperties = {
  padding: '10px 12px',
  fontSize: 'var(--text-body)',
  color: 'var(--color-text-secondary)',
  borderTop: '1px solid var(--color-border-subtle)',
  verticalAlign: 'middle',
};

export default function ClaimsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('All');
  const [payerFilter, setPayerFilter] = useState<PayerFilter>('All');

  const filterBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: '6px 14px',
    background: active ? 'var(--color-brand-orange)' : 'var(--color-bg-panel-raised)',
    clipPath: 'var(--chamfer-4)',
    border: active ? 'none' : '1px solid var(--color-border-default)',
    color: active ? 'rgba(0,0,0,0.92)' : 'var(--color-text-secondary)',
    fontFamily: 'var(--font-label)',
    fontSize: 'var(--text-label)',
    fontWeight: 600,
    letterSpacing: 'var(--tracking-label)',
    textTransform: 'uppercase',
    cursor: 'pointer',
    transition: 'all var(--duration-fast)',
  });

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
            Claims Management
          </h1>
        </div>

        {/* Stats Strip */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 mb-6">
          {STAT_COUNTS.map((s) => (
            <div
              key={s.label}
              style={{
                background: 'var(--color-bg-panel)',
                clipPath: 'var(--chamfer-8)',
                padding: '16px 20px',
                boxShadow: 'var(--elevation-1)',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              <div className="micro-caps" style={{ color: 'var(--color-text-muted)' }}>
                {s.label}
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--text-h2)',
                  fontWeight: 700,
                  color: s.color,
                  lineHeight: 1.1,
                }}
              >
                {s.value}
              </div>
            </div>
          ))}
        </div>

        {/* Filter Bar */}
        <div
          style={{
            background: 'var(--color-bg-panel)',
            clipPath: 'var(--chamfer-8)',
            padding: '16px 20px',
            marginBottom: '16px',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '16px',
            alignItems: 'center',
          }}
        >
          {/* Status Filter */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div className="micro-caps" style={{ color: 'var(--color-text-muted)' }}>
              Status
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {STATUS_FILTERS.map((f) => (
                <button key={f} style={filterBtnStyle(statusFilter === f)} onClick={() => setStatusFilter(f)}>
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Payer Filter */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div className="micro-caps" style={{ color: 'var(--color-text-muted)' }}>
              Payer
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {PAYER_FILTERS.map((f) => (
                <button key={f} style={filterBtnStyle(payerFilter === f)} onClick={() => setPayerFilter(f)}>
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Date Range Label */}
          <div
            style={{
              marginLeft: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
              alignItems: 'flex-end',
            }}
          >
            <div className="micro-caps" style={{ color: 'var(--color-text-muted)' }}>
              Date Range
            </div>
            <div
              style={{
                fontSize: 'var(--text-body)',
                color: 'var(--color-text-secondary)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              02/01/2026 – 02/28/2026
            </div>
          </div>
        </div>

        {/* Claims Table */}
        <div
          style={{
            background: 'var(--color-bg-panel)',
            clipPath: 'var(--chamfer-8)',
            overflow: 'hidden',
            boxShadow: 'var(--elevation-1)',
            marginBottom: '12px',
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={TH}>Claim ID</th>
                <th style={TH}>Patient</th>
                <th style={TH}>DOS</th>
                <th style={TH}>Payer</th>
                <th style={{ ...TH, textAlign: 'right' }}>Amount</th>
                <th style={{ ...TH, textAlign: 'center' }}>Status</th>
                <th style={{ ...TH, textAlign: 'center' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {CLAIMS.map((claim, i) => (
                <tr
                  key={claim.id}
                  style={{
                    background:
                      i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                  }}
                >
                  <td
                    style={{
                      ...TD,
                      fontFamily: 'var(--font-mono)',
                      fontSize: 'var(--text-body)',
                      color: 'var(--color-system-billing)',
                    }}
                  >
                    {claim.id}
                  </td>
                  <td
                    style={{
                      ...TD,
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    {claim.patient}
                  </td>
                  <td style={TD}>{claim.dos}</td>
                  <td style={{ ...TD, color: 'var(--color-text-primary)' }}>{claim.payer}</td>
                  <td
                    style={{
                      ...TD,
                      fontFamily: 'var(--font-mono)',
                      textAlign: 'right',
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    {claim.amount}
                  </td>
                  <td style={{ ...TD, textAlign: 'center' }}>
                    <ClaimStatusChip claimStatus={claim.status} size="sm" />
                  </td>
                  <td style={{ ...TD, textAlign: 'center' }}>
                    <button
                      style={{
                        padding: '4px 12px',
                        background: 'transparent',
                        border: '1px solid var(--color-border-default)',
                        clipPath: 'var(--chamfer-4)',
                        color: 'var(--color-text-secondary)',
                        fontFamily: 'var(--font-label)',
                        fontSize: 'var(--text-label)',
                        fontWeight: 600,
                        letterSpacing: 'var(--tracking-label)',
                        textTransform: 'uppercase',
                        cursor: 'pointer',
                        transition: 'color var(--duration-fast)',
                      }}
                      onMouseEnter={(e) =>
                        ((e.currentTarget as HTMLButtonElement).style.color =
                          'var(--color-text-primary)')
                      }
                      onMouseLeave={(e) =>
                        ((e.currentTarget as HTMLButtonElement).style.color =
                          'var(--color-text-secondary)')
                      }
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div
          style={{
            fontSize: 'var(--text-body)',
            color: 'var(--color-text-muted)',
            textAlign: 'right',
            padding: '4px 0',
          }}
        >
          Showing 1–10 of 847 claims
        </div>
      </div>
    </AppShell>
  );
}
