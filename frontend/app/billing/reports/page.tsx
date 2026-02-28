'use client';

import React from 'react';
import AppShell from '@/components/AppShell';

interface ReportCard {
  title: string;
  description: string;
  lastGenerated: string;
}

interface RecentReport {
  name: string;
  generated: string;
  period: string;
  format: 'PDF' | 'CSV';
}

const REPORT_CARDS: ReportCard[] = [
  {
    title: 'Denial Analysis',
    description: 'Root cause breakdown of denied claims by payer, code, and reason',
    lastGenerated: '02/25/2026',
  },
  {
    title: 'Payer Mix',
    description: 'Revenue distribution across Medicare, Medicaid, commercial, and self-pay',
    lastGenerated: '02/24/2026',
  },
  {
    title: 'Productivity',
    description: 'Coder and biller throughput, time-to-submit, and clean claim metrics',
    lastGenerated: '02/23/2026',
  },
  {
    title: 'AR Aging Trend',
    description: 'Month-over-month aging bucket trends and collectability analysis',
    lastGenerated: '02/22/2026',
  },
  {
    title: 'Collection Analysis',
    description: 'Net collection rate, write-offs, adjustments, and cash flow trends',
    lastGenerated: '02/20/2026',
  },
  {
    title: 'Compliance Report',
    description: 'HIPAA compliance status, audit flags, and billing integrity summary',
    lastGenerated: '02/18/2026',
  },
];

const RECENT_REPORTS: RecentReport[] = [
  { name: 'Denial Analysis — February 2026', generated: '02/25/2026 09:14', period: 'Feb 2026', format: 'PDF' },
  { name: 'Payer Mix — Q1 2026', generated: '02/24/2026 15:32', period: 'Q1 2026', format: 'CSV' },
  { name: 'AR Aging Trend — YTD', generated: '02/23/2026 08:07', period: 'Jan–Feb 2026', format: 'PDF' },
  { name: 'Productivity — Week 8', generated: '02/22/2026 11:45', period: 'Wk 8 2026', format: 'CSV' },
  { name: 'Collection Analysis — January', generated: '02/20/2026 14:20', period: 'Jan 2026', format: 'PDF' },
  { name: 'Compliance Report — Q1', generated: '02/18/2026 10:05', period: 'Q1 2026', format: 'PDF' },
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

export default function ReportsPage() {
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
            Reports &amp; Analytics
          </h1>
        </div>

        {/* Report Category Cards */}
        <div className="label-caps mb-4" style={{ color: 'var(--color-text-muted)', letterSpacing: 'var(--tracking-label)' }}>
          Report Categories
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-10">
          {REPORT_CARDS.map((card) => (
            <div
              key={card.title}
              style={{
                background: 'var(--color-bg-panel)',
                clipPath: 'var(--chamfer-8)',
                padding: '20px',
                boxShadow: 'var(--elevation-1)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                borderTop: '2px solid var(--color-system-billing)',
              }}
            >
              {/* Title */}
              <div
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
              </div>

              {/* Description */}
              <p
                style={{
                  fontSize: 'var(--text-body)',
                  color: 'var(--color-text-secondary)',
                  margin: 0,
                  lineHeight: 'var(--leading-base)',
                  flex: 1,
                }}
              >
                {card.description}
              </p>

              {/* Footer: last generated + button */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginTop: '4px',
                }}
              >
                <div
                  style={{
                    fontSize: 'var(--text-micro)',
                    color: 'var(--color-text-muted)',
                    fontFamily: 'var(--font-mono)',
                    textTransform: 'uppercase',
                    letterSpacing: 'var(--tracking-micro)',
                  }}
                >
                  Last: {card.lastGenerated}
                </div>
                <button
                  style={{
                    padding: '5px 14px',
                    background: 'var(--color-brand-orange)',
                    clipPath: 'var(--chamfer-4)',
                    border: 'none',
                    color: 'rgba(0,0,0,0.92)',
                    fontFamily: 'var(--font-label)',
                    fontSize: 'var(--text-label)',
                    fontWeight: 700,
                    letterSpacing: 'var(--tracking-label)',
                    textTransform: 'uppercase',
                    cursor: 'pointer',
                    transition: 'opacity var(--duration-fast)',
                  }}
                  onMouseEnter={(e) =>
                    ((e.currentTarget as HTMLButtonElement).style.opacity = '0.88')
                  }
                  onMouseLeave={(e) =>
                    ((e.currentTarget as HTMLButtonElement).style.opacity = '1')
                  }
                >
                  Run Report
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Recent Reports */}
        <div className="label-caps mb-4" style={{ color: 'var(--color-text-muted)', letterSpacing: 'var(--tracking-label)' }}>
          Recent Reports
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
                <th style={TH}>Report Name</th>
                <th style={TH}>Generated</th>
                <th style={TH}>Period</th>
                <th style={{ ...TH, textAlign: 'center' }}>Format</th>
                <th style={{ ...TH, textAlign: 'center' }}>Download</th>
              </tr>
            </thead>
            <tbody>
              {RECENT_REPORTS.map((report, i) => (
                <tr
                  key={report.name}
                  style={{
                    background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                  }}
                >
                  <td
                    style={{
                      ...TD,
                      color: 'var(--color-text-primary)',
                      fontWeight: 500,
                    }}
                  >
                    {report.name}
                  </td>
                  <td
                    style={{
                      ...TD,
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--color-text-muted)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {report.generated}
                  </td>
                  <td style={TD}>{report.period}</td>
                  <td style={{ ...TD, textAlign: 'center' }}>
                    <span
                      style={{
                        display: 'inline-block',
                        padding: '3px 10px',
                        background:
                          report.format === 'PDF'
                            ? 'rgba(229,57,53,0.10)'
                            : 'rgba(34,211,238,0.10)',
                        clipPath: 'var(--chamfer-4)',
                        border: `1px solid ${
                          report.format === 'PDF'
                            ? 'rgba(229,57,53,0.25)'
                            : 'rgba(34,211,238,0.25)'
                        }`,
                        fontFamily: 'var(--font-mono)',
                        fontSize: 'var(--text-label)',
                        fontWeight: 600,
                        letterSpacing: 'var(--tracking-label)',
                        color:
                          report.format === 'PDF'
                            ? 'var(--color-brand-red-bright)'
                            : 'var(--color-system-billing)',
                        textTransform: 'uppercase',
                      }}
                    >
                      {report.format}
                    </span>
                  </td>
                  <td style={{ ...TD, textAlign: 'center' }}>
                    <button
                      style={{
                        padding: '4px 14px',
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
                          'var(--color-brand-orange)')
                      }
                      onMouseLeave={(e) =>
                        ((e.currentTarget as HTMLButtonElement).style.color =
                          'var(--color-text-secondary)')
                      }
                    >
                      Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
