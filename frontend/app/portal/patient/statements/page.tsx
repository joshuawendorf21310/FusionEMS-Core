'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

type StatementStatus = 'paid' | 'pending' | 'overdue' | 'in_review';

interface Statement {
  id: string;
  date: string;
  serviceType: string;
  totalBilled: number;
  insurancePaid: number;
  balance: number;
  status: StatementStatus;
}

const MOCK_STATEMENTS: Statement[] = [
  {
    id: 'STM-2026-0041',
    date: 'Jan 15, 2026',
    serviceType: 'Emergency Transport — ALS Level 1',
    totalBilled: 1240.0,
    insurancePaid: 1065.0,
    balance: 175.0,
    status: 'pending',
  },
  {
    id: 'STM-2025-1187',
    date: 'Nov 3, 2025',
    serviceType: 'Emergency Transport — BLS Non-Emergency',
    totalBilled: 680.0,
    insurancePaid: 680.0,
    balance: 0.0,
    status: 'paid',
  },
  {
    id: 'STM-2025-0904',
    date: 'Sep 18, 2025',
    serviceType: 'Critical Care Transport — CCT',
    totalBilled: 2850.0,
    insurancePaid: 1890.0,
    balance: 960.0,
    status: 'overdue',
  },
  {
    id: 'STM-2025-0712',
    date: 'Jul 9, 2025',
    serviceType: 'Emergency Transport — ALS Level 2',
    totalBilled: 1560.0,
    insurancePaid: 1345.0,
    balance: 215.0,
    status: 'in_review',
  },
];

const STATUS_CONFIG: Record<
  StatementStatus,
  { label: string; bg: string; border: string; color: string }
> = {
  paid: {
    label: 'PAID',
    bg: 'rgba(76, 175, 80, 0.10)',
    border: 'rgba(76, 175, 80, 0.35)',
    color: 'var(--color-status-active)',
  },
  pending: {
    label: 'PENDING',
    bg: 'rgba(255, 152, 0, 0.10)',
    border: 'rgba(255, 152, 0, 0.35)',
    color: 'var(--color-status-warning)',
  },
  overdue: {
    label: 'OVERDUE',
    bg: 'rgba(229, 57, 53, 0.10)',
    border: 'rgba(229, 57, 53, 0.35)',
    color: 'var(--color-brand-red)',
  },
  in_review: {
    label: 'IN REVIEW',
    bg: 'rgba(41, 182, 246, 0.10)',
    border: 'rgba(41, 182, 246, 0.35)',
    color: 'var(--color-status-info)',
  },
};

function StatusChip({ status }: { status: StatementStatus }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
        padding: '3px 8px',
        fontFamily: 'var(--font-label)',
        fontSize: 'var(--text-micro)',
        fontWeight: 700,
        letterSpacing: 'var(--tracking-micro)',
        color: cfg.color,
        whiteSpace: 'nowrap',
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: '50%',
          background: cfg.color,
          flexShrink: 0,
        }}
      />
      {cfg.label}
    </span>
  );
}

export default function PatientStatementsPage() {
  const [statements, setStatements] = useState<Statement[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch('/api/v1/patient/statements');
        if (!res.ok) throw new Error('Not OK');
        const data = await res.json();
        setStatements(data);
      } catch (e: unknown) {
        console.warn('[statements load error]', e);
        setFetchError(true);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const totalDue = statements.reduce(
    (sum, s) => (s.status !== 'paid' ? sum + s.balance : sum),
    0
  );

  if (fetchError) return (
    <div style={{ minHeight: '100vh', background: 'var(--color-bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center', color: 'var(--color-text-muted)' }}>Unable to load statements. Please try again later.</div>
    </div>
  );

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--color-bg-base)',
        padding: '40px 16px',
      }}
    >
      <div style={{ width: '100%', maxWidth: 760, margin: '0 auto' }}>
        {/* Header */}
        <div
          className="hud-rail"
          style={{
            paddingBottom: 16,
            marginBottom: 24,
            borderBottom: '1px solid var(--color-border-default)',
          }}
        >
          <div
            style={{
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-micro)',
              fontWeight: 600,
              letterSpacing: 'var(--tracking-micro)',
              textTransform: 'uppercase',
              color: 'var(--color-brand-orange)',
              marginBottom: 6,
            }}
          >
            Patient Portal
          </div>
          <h1
            style={{
              fontSize: 'var(--text-h2)',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              lineHeight: 'var(--leading-tight)',
            }}
          >
            Your Statements
          </h1>
        </div>

        {/* Total balance banner */}
        {totalDue > 0 && (
          <div
            style={{
              background: 'var(--color-bg-panel)',
              border: '1px solid var(--color-border-default)',
              borderLeft: '3px solid var(--color-brand-orange)',
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
              padding: '14px 20px',
              marginBottom: 20,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: 'var(--font-label)',
                  fontSize: 'var(--text-label)',
                  fontWeight: 600,
                  letterSpacing: 'var(--tracking-label)',
                  textTransform: 'uppercase',
                  color: 'var(--color-text-muted)',
                  marginBottom: 3,
                }}
              >
                Total Balance Due
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--text-h2)',
                  fontWeight: 700,
                  color: 'var(--color-brand-orange)',
                }}
              >
                ${totalDue.toFixed(2)}
              </div>
            </div>
            <Link
              href="/portal/patient/pay"
              style={{
                background: 'var(--color-brand-orange)',
                color: '#000',
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-label)',
                fontWeight: 700,
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
                padding: '10px 20px',
                clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
                textDecoration: 'none',
                flexShrink: 0,
              }}
            >
              Pay Now
            </Link>
          </div>
        )}

        {/* Statements list */}
        {loading ? (
          <div
            style={{
              textAlign: 'center',
              padding: '60px 0',
              fontSize: 'var(--text-body)',
              color: 'var(--color-text-muted)',
            }}
          >
            Loading statements...
          </div>
        ) : statements.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: '60px 0',
              fontSize: 'var(--text-body)',
              color: 'var(--color-text-muted)',
            }}
          >
            No statements on file.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {statements.map((stmt) => (
              <div
                key={stmt.id}
                style={{
                  background: 'var(--color-bg-panel)',
                  border: '1px solid var(--color-border-default)',
                  clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
                  padding: '16px 20px',
                }}
              >
                {/* Top row: date, service, status */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: 12,
                    marginBottom: 12,
                    flexWrap: 'wrap',
                  }}
                >
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 10,
                        color: 'var(--color-text-muted)',
                        marginBottom: 3,
                        letterSpacing: '0.05em',
                      }}
                    >
                      {stmt.id}
                    </div>
                    <div
                      style={{
                        fontSize: 'var(--text-body)',
                        fontWeight: 600,
                        color: 'var(--color-text-primary)',
                        marginBottom: 2,
                      }}
                    >
                      {stmt.serviceType}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: 'var(--color-text-muted)',
                      }}
                    >
                      Date of Service: {stmt.date}
                    </div>
                  </div>
                  <StatusChip status={stmt.status} />
                </div>

                {/* Billing row */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: 12,
                    marginBottom: 14,
                    paddingTop: 12,
                    borderTop: '1px solid var(--color-border-subtle)',
                  }}
                >
                  {[
                    { label: 'Total Billed', value: `$${stmt.totalBilled.toFixed(2)}`, color: 'var(--color-text-secondary)' },
                    { label: 'Insurance Paid', value: `$${stmt.insurancePaid.toFixed(2)}`, color: 'var(--color-status-active)' },
                    {
                      label: 'Balance Due',
                      value: `$${stmt.balance.toFixed(2)}`,
                      color: stmt.balance > 0 ? 'var(--color-brand-orange)' : 'var(--color-text-muted)',
                    },
                  ].map((col) => (
                    <div key={col.label}>
                      <div
                        style={{
                          fontFamily: 'var(--font-label)',
                          fontSize: 'var(--text-micro)',
                          fontWeight: 600,
                          letterSpacing: 'var(--tracking-micro)',
                          textTransform: 'uppercase',
                          color: 'var(--color-text-muted)',
                          marginBottom: 3,
                        }}
                      >
                        {col.label}
                      </div>
                      <div
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: 'var(--text-body-lg)',
                          fontWeight: 700,
                          color: col.color,
                        }}
                      >
                        {col.value}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: 8 }}>
                  <Link
                    href={`/portal/patient/statements/${stmt.id}`}
                    style={{
                      background: 'var(--color-bg-overlay)',
                      border: '1px solid var(--color-border-strong)',
                      color: 'var(--color-text-secondary)',
                      fontFamily: 'var(--font-label)',
                      fontSize: 'var(--text-micro)',
                      fontWeight: 600,
                      letterSpacing: 'var(--tracking-micro)',
                      textTransform: 'uppercase',
                      padding: '6px 14px',
                      clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)',
                      textDecoration: 'none',
                    }}
                  >
                    View
                  </Link>
                  {stmt.status !== 'paid' && (
                    <Link
                      href="/portal/patient/pay"
                      style={{
                        background: 'var(--color-brand-orange)',
                        color: '#000',
                        fontFamily: 'var(--font-label)',
                        fontSize: 'var(--text-micro)',
                        fontWeight: 700,
                        letterSpacing: 'var(--tracking-micro)',
                        textTransform: 'uppercase',
                        padding: '6px 14px',
                        clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)',
                        textDecoration: 'none',
                      }}
                    >
                      Pay
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            marginTop: 32,
            paddingTop: 20,
            borderTop: '1px solid var(--color-border-subtle)',
            textAlign: 'center',
          }}
        >
          <p style={{ fontSize: 'var(--text-body)', color: 'var(--color-text-muted)' }}>
            Need help?{' '}
            <a
              href="mailto:billing@fusionems.com"
              style={{
                color: 'var(--color-brand-orange)',
                textDecoration: 'none',
              }}
            >
              Contact our billing team
            </a>
            {' '}or call{' '}
            <a
              href="tel:18005551234"
              style={{
                color: 'var(--color-text-secondary)',
                textDecoration: 'none',
              }}
            >
              1-800-555-1234
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
