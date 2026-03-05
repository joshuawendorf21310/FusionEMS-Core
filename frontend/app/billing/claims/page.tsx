'use client';

import React, { useState, useEffect } from 'react';
import AppShell from '@/components/AppShell';
import { ClaimStatusChip } from '@/components/ui/StatusChip';
import { QuantumEmptyState, QuantumCardSkeleton } from '@/components/ui';

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

const STATUS_FILTERS: StatusFilter[] = ['All', 'Clean', 'Pending', 'Denied', 'Appealed'];
const PAYER_FILTERS: PayerFilter[] = ['All', 'Medicare', 'Medicaid', 'Commercial'];

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

const API = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || '';

export default function ClaimsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('All');
  const [payerFilter, setPayerFilter] = useState<PayerFilter>('All');
  
  const [claims, setClaims] = useState<Claim[]>([]);
  const [stats, setStats] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    fetch(`${API}/api/v1/billing/claims?status=${statusFilter}&payer=${payerFilter}`)
      .then(res => res.json())
      .then(data => {
        if(data.claims) setClaims(data.claims);
        if(data.stats) setStats(data.stats);
      })
      .catch(e => console.warn('[fetch error]', e))
      .finally(() => setIsLoading(false));
  }, [statusFilter, payerFilter]);

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
          {isLoading && stats.length === 0 ? (
             Array.from({length: 4}).map((_, i) => <QuantumCardSkeleton key={i} />)
          ) : stats.length > 0 ? (
            stats.map((s) => (
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
                    color: s.color || 'var(--color-text-primary)',
                    lineHeight: 1.1,
                  }}
                >
                  {s.value}
                </div>
              </div>
            ))
          ) : (
             <QuantumEmptyState title="No metrics" description="API didn't return aggregations" icon="billing" />
          )}
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
              Real-time filter active
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
          {isLoading ? (
            <div className="p-8">
              <QuantumCardSkeleton title="Loading Claims..." />
            </div>
          ) : claims.length === 0 ? (
            <QuantumEmptyState title="No Claims Found" description="No claims matching these filters or API disconnected." icon="billing" />
          ) : (
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
                {claims.map((claim, i) => (
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
          )}
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
          {claims.length ? `Showing 1–${claims.length} of ${claims.length} claims` : ''}
        </div>
      </div>
    </AppShell>
  );
}
