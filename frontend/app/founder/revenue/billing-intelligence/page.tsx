'use client';

import { PlateCard } from '@/components/ui/PlateCard';

/* ─── Data ─────────────────────────────────────────────────────────── */

const REVENUE_METRICS = [
  { label: 'MoM Growth', value: '+8.4%', color: 'var(--color-status-active)', dir: '▲' },
  { label: 'QoQ Growth', value: '+22.1%', color: 'var(--color-status-active)', dir: '▲' },
  { label: 'YoY Growth', value: '+41.7%', color: 'var(--color-status-active)', dir: '▲' },
  { label: 'Run Rate (ARR)', value: '$2.84M', color: 'var(--color-brand-orange)', dir: '' },
];

const DENIAL_REASONS = [
  { reason: 'Missing Prior Auth', count: 87, pct: 24 },
  { reason: 'Duplicate Claim', count: 63, pct: 18 },
  { reason: 'Patient Not Eligible', count: 58, pct: 16 },
  { reason: 'Coding Error (CPT)', count: 44, pct: 12 },
  { reason: 'Service Not Covered', count: 36, pct: 10 },
];

const PAYERS = [
  { name: 'Medicare', volume: 412, avgDays: 18, denialRate: '6.2%', netCollection: '94.1%' },
  { name: 'Medicaid', volume: 298, avgDays: 24, denialRate: '11.8%', netCollection: '88.4%' },
  { name: 'BCBS', volume: 187, avgDays: 14, denialRate: '4.9%', netCollection: '97.2%' },
  { name: 'United Health', volume: 143, avgDays: 16, denialRate: '7.3%', netCollection: '92.8%' },
  { name: 'Aetna', volume: 96, avgDays: 13, denialRate: '3.6%', netCollection: '98.1%' },
  { name: 'Self Pay', volume: 74, avgDays: 42, denialRate: '—', netCollection: '61.3%' },
];

const AR_AGING = [
  { bucket: '0–30 days', amount: 284500, pct: 52, color: 'var(--color-status-active)' },
  { bucket: '31–60 days', amount: 118200, pct: 22, color: '#a3e635' },
  { bucket: '61–90 days', amount: 76400, pct: 14, color: 'var(--color-status-warning)' },
  { bucket: '91–120 days', amount: 43800, pct: 8, color: '#f97316' },
  { bucket: '120+ days', amount: 21600, pct: 4, color: 'var(--color-brand-red)' },
];

const PROC_CODES = [
  { code: 'A0427', desc: 'ALS Level 1 — Emergency', volume: 318, accuracy: 96.2, error: 3.8 },
  { code: 'A0429', desc: 'BLS — Emergency', volume: 241, accuracy: 98.1, error: 1.9 },
  { code: 'A0433', desc: 'ALS Level 2', volume: 89, accuracy: 93.4, error: 6.6 },
  { code: 'A0436', desc: 'Rotary Wing Transport', volume: 34, accuracy: 97.1, error: 2.9 },
  { code: 'A0428', desc: 'BLS — Non-Emergency', volume: 178, accuracy: 99.4, error: 0.6 },
];

const PRODUCTIVITY = [
  { label: 'Claims / Day', value: '47.3', sub: 'avg last 30d', color: 'var(--color-system-billing)' },
  { label: 'Clean Claim %', value: '91.8%', sub: '+2.1% vs last mo', color: 'var(--color-status-active)' },
  { label: 'Resubmission Rate', value: '8.2%', sub: '-1.4% vs last mo', color: 'var(--color-status-warning)' },
  { label: 'Coder Productivity', value: '94.1%', sub: 'above baseline', color: 'var(--color-status-active)' },
];

/* ─── Sub-components ────────────────────────────────────────────────── */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontFamily: 'var(--font-label)',
        fontSize: 'var(--text-label)',
        fontWeight: 600,
        letterSpacing: 'var(--tracking-label)',
        textTransform: 'uppercase',
        color: 'var(--color-text-muted)',
        marginBottom: 14,
      }}
    >
      {children}
    </div>
  );
}

function MetricRow({
  label,
  value,
  color,
  dir,
}: {
  label: string;
  value: string;
  color: string;
  dir: string;
}) {
  return (
    <div
      style={{
        background: 'var(--color-bg-panel-raised)',
        border: '1px solid var(--color-border-subtle)',
        clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)',
        padding: '12px 14px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <span
        style={{
          fontFamily: 'var(--font-label)',
          fontSize: 'var(--text-label)',
          fontWeight: 600,
          letterSpacing: 'var(--tracking-label)',
          textTransform: 'uppercase',
          color: 'var(--color-text-muted)',
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--text-body-lg)',
          fontWeight: 700,
          color,
        }}
      >
        {dir && (
          <span style={{ fontSize: 10, marginRight: 4, opacity: 0.8 }}>{dir}</span>
        )}
        {value}
      </span>
    </div>
  );
}

/* ─── Page ──────────────────────────────────────────────────────────── */

export default function BillingIntelligencePage() {
  return (
    <div style={{ padding: '20px 24px', minHeight: '100%' }}>
      {/* Page header */}
      <div
        className="hud-rail"
        style={{
          paddingBottom: 14,
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
            color: 'rgba(34, 211, 238, 0.7)',
            marginBottom: 4,
          }}
        >
          2 · Revenue
        </div>
        <h1
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 'var(--text-h1)',
            fontWeight: 900,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            color: 'var(--color-text-primary)',
            lineHeight: 'var(--leading-tight)',
          }}
        >
          Billing Intelligence
        </h1>
        <p
          style={{
            fontSize: 'var(--text-body)',
            color: 'var(--color-text-muted)',
            marginTop: 4,
          }}
        >
          Tenant profitability · Module revenue breakdown · Revenue leakage detection
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* ── 1. Revenue Velocity ──────────────────────────────────────── */}
        <PlateCard
          accent="billing"
          header="Revenue Velocity"
          headerRight={
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 10,
                color: 'var(--color-status-active)',
                letterSpacing: '0.05em',
              }}
            >
              ▲ TRENDING UP
            </span>
          }
        >
          {/* Chart placeholder */}
          <div
            style={{
              height: 120,
              background: 'var(--color-bg-overlay)',
              border: '1px solid var(--color-border-subtle)',
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 16,
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {/* Fake sparkline bars */}
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'flex-end',
                gap: 3,
                padding: '12px 16px 0',
                opacity: 0.35,
              }}
            >
              {[55, 62, 58, 70, 68, 75, 80, 78, 85, 88, 92, 100].map((h, i) => (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    height: `${h}%`,
                    background: 'var(--color-system-billing)',
                    clipPath: 'polygon(0 0, calc(100% - 2px) 0, 100% 2px, 100% 100%, 0 100%)',
                  }}
                />
              ))}
            </div>
            <span
              style={{
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-micro)',
                fontWeight: 600,
                letterSpacing: 'var(--tracking-micro)',
                textTransform: 'uppercase',
                color: 'var(--color-text-muted)',
                zIndex: 1,
              }}
            >
              Revenue Trend — Last 12 Months
            </span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: 8,
            }}
          >
            {REVENUE_METRICS.map((m) => (
              <MetricRow key={m.label} {...m} />
            ))}
          </div>
        </PlateCard>

        {/* ── 2. Denial Intelligence ───────────────────────────────────── */}
        <PlateCard
          accent="red"
          header="Denial Intelligence"
          headerRight={
            <div style={{ display: 'flex', gap: 16 }}>
              <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                Denial Rate:{' '}
                <span style={{ color: 'var(--color-brand-red)', fontWeight: 700 }}>9.6%</span>
              </span>
              <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                Appeal Win:{' '}
                <span style={{ color: 'var(--color-status-active)', fontWeight: 700 }}>71.3%</span>
              </span>
            </div>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {DENIAL_REASONS.map((d) => (
              <div key={d.reason}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: 4,
                  }}
                >
                  <span
                    style={{
                      fontSize: 'var(--text-body)',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    {d.reason}
                  </span>
                  <div style={{ display: 'flex', gap: 10 }}>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        color: 'var(--color-text-muted)',
                      }}
                    >
                      {d.count} claims
                    </span>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        fontWeight: 700,
                        color: 'var(--color-brand-red)',
                        minWidth: 32,
                        textAlign: 'right',
                      }}
                    >
                      {d.pct}%
                    </span>
                  </div>
                </div>
                <div
                  style={{
                    height: 6,
                    background: 'var(--color-bg-overlay)',
                    clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${d.pct}%`,
                      background: `linear-gradient(90deg, var(--color-brand-red-dim), var(--color-brand-red))`,
                      transition: 'width 0.4s ease',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </PlateCard>

        {/* ── 3. Payer Intelligence ────────────────────────────────────── */}
        <PlateCard
          accent="billing"
          header="Payer Intelligence"
          headerRight={
            <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
              {PAYERS.reduce((s, p) => s + p.volume, 0).toLocaleString()} total claims
            </span>
          }
        >
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: 'var(--text-body)',
              }}
            >
              <thead>
                <tr>
                  {['Payer', 'Volume', 'Avg Days', 'Denial Rate', 'Net Collection'].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: '8px 10px',
                        textAlign: h === 'Payer' ? 'left' : 'right',
                        fontFamily: 'var(--font-label)',
                        fontSize: 'var(--text-micro)',
                        fontWeight: 600,
                        letterSpacing: 'var(--tracking-micro)',
                        textTransform: 'uppercase',
                        color: 'var(--color-text-muted)',
                        borderBottom: '1px solid var(--color-border-default)',
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {PAYERS.map((p, i) => (
                  <tr
                    key={p.name}
                    style={{
                      background:
                        i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                      borderBottom: '1px solid var(--color-border-subtle)',
                    }}
                  >
                    <td
                      style={{
                        padding: '9px 10px',
                        fontWeight: 600,
                        color: 'var(--color-text-primary)',
                      }}
                    >
                      {p.name}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      {p.volume.toLocaleString()}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        color:
                          p.avgDays > 30
                            ? 'var(--color-status-warning)'
                            : 'var(--color-text-secondary)',
                      }}
                    >
                      {p.avgDays}d
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        color:
                          p.denialRate === '—'
                            ? 'var(--color-text-muted)'
                            : parseFloat(p.denialRate) > 10
                            ? 'var(--color-brand-red)'
                            : parseFloat(p.denialRate) > 6
                            ? 'var(--color-status-warning)'
                            : 'var(--color-status-active)',
                        fontWeight: 700,
                      }}
                    >
                      {p.denialRate}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        color:
                          parseFloat(p.netCollection) >= 95
                            ? 'var(--color-status-active)'
                            : parseFloat(p.netCollection) >= 85
                            ? 'var(--color-system-billing)'
                            : 'var(--color-status-warning)',
                        fontWeight: 700,
                      }}
                    >
                      {p.netCollection}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlateCard>

        {/* ── 4. AR Risk Analysis ──────────────────────────────────────── */}
        <PlateCard
          accent="warning"
          header="AR Risk Analysis"
          headerRight={
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--color-text-muted)',
              }}
            >
              Total AR:{' '}
              <span style={{ color: 'var(--color-text-primary)', fontWeight: 700 }}>
                ${(544500).toLocaleString()}
              </span>
            </span>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {AR_AGING.map((bucket) => (
              <div key={bucket.bucket}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: 5,
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'var(--font-label)',
                      fontSize: 'var(--text-label)',
                      fontWeight: 600,
                      letterSpacing: 'var(--tracking-label)',
                      textTransform: 'uppercase',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    {bucket.bucket}
                  </span>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        color: 'var(--color-text-muted)',
                      }}
                    >
                      ${bucket.amount.toLocaleString()}
                    </span>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        fontWeight: 700,
                        color: bucket.color,
                        minWidth: 32,
                        textAlign: 'right',
                      }}
                    >
                      {bucket.pct}%
                    </span>
                  </div>
                </div>
                <div
                  style={{
                    height: 8,
                    background: 'var(--color-bg-overlay)',
                    clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${bucket.pct}%`,
                      background: bucket.color,
                      opacity: 0.85,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </PlateCard>

        {/* ── 5. Coding Accuracy ───────────────────────────────────────── */}
        <PlateCard
          accent="compliance"
          header="Coding Accuracy"
          headerRight={
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--color-status-active)',
              }}
            >
              Overall: 96.8% accurate
            </span>
          }
        >
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: 'var(--text-body)',
              }}
            >
              <thead>
                <tr>
                  {['Code', 'Description', 'Volume', 'Accuracy', 'Error Rate'].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: '8px 10px',
                        textAlign: h === 'Code' || h === 'Description' ? 'left' : 'right',
                        fontFamily: 'var(--font-label)',
                        fontSize: 'var(--text-micro)',
                        fontWeight: 600,
                        letterSpacing: 'var(--tracking-micro)',
                        textTransform: 'uppercase',
                        color: 'var(--color-text-muted)',
                        borderBottom: '1px solid var(--color-border-default)',
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {PROC_CODES.map((row, i) => (
                  <tr
                    key={row.code}
                    style={{
                      background:
                        i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                      borderBottom: '1px solid var(--color-border-subtle)',
                    }}
                  >
                    <td
                      style={{
                        padding: '9px 10px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 12,
                        fontWeight: 700,
                        color: 'var(--color-system-compliance)',
                      }}
                    >
                      {row.code}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        color: 'var(--color-text-secondary)',
                        fontSize: 12,
                      }}
                    >
                      {row.desc}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      {row.volume}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 700,
                        color:
                          row.accuracy >= 97
                            ? 'var(--color-status-active)'
                            : row.accuracy >= 94
                            ? 'var(--color-status-warning)'
                            : 'var(--color-brand-red)',
                      }}
                    >
                      {row.accuracy}%
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 700,
                        color:
                          row.error < 3
                            ? 'var(--color-text-muted)'
                            : row.error < 6
                            ? 'var(--color-status-warning)'
                            : 'var(--color-brand-red)',
                      }}
                    >
                      {row.error}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlateCard>

        {/* ── 6. Productivity Metrics ──────────────────────────────────── */}
        <PlateCard
          accent="orange"
          header="Productivity Metrics"
          headerRight={
            <span
              style={{
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-micro)',
                fontWeight: 600,
                letterSpacing: 'var(--tracking-micro)',
                textTransform: 'uppercase',
                color: 'var(--color-text-muted)',
              }}
            >
              30-Day Rolling
            </span>
          }
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: 10,
            }}
          >
            {PRODUCTIVITY.map((m) => (
              <div
                key={m.label}
                style={{
                  background: 'var(--color-bg-panel-raised)',
                  border: '1px solid var(--color-border-subtle)',
                  borderLeft: `3px solid ${m.color}`,
                  clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
                  padding: '14px 16px',
                }}
              >
                <div
                  style={{
                    fontFamily: 'var(--font-label)',
                    fontSize: 'var(--text-label)',
                    fontWeight: 600,
                    letterSpacing: 'var(--tracking-label)',
                    textTransform: 'uppercase',
                    color: 'var(--color-text-muted)',
                    marginBottom: 6,
                  }}
                >
                  {m.label}
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 'var(--text-h2)',
                    fontWeight: 700,
                    color: m.color,
                    lineHeight: 1,
                    marginBottom: 4,
                  }}
                >
                  {m.value}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: 'var(--color-text-muted)',
                  }}
                >
                  {m.sub}
                </div>
              </div>
            ))}
          </div>
        </PlateCard>

      </div>
    </div>
  );
}
