'use client';

import React, { useState } from 'react';
import AppShell from '@/components/AppShell';
import { StatusChip } from '@/components/ui/StatusChip';

type DocStatusVariant = 'active' | 'warning' | 'neutral' | 'info' | 'critical';

interface DocRow {
  type: string;
  patientId: string;
  date: string;
  statusVariant: DocStatusVariant;
  statusLabel: string;
  size: string;
}

const DOCUMENTS: DocRow[] = [
  { type: 'PCR', patientId: 'P-3821', date: '02/14/2026', statusVariant: 'active', statusLabel: 'Verified', size: '842 KB' },
  { type: 'ABN', patientId: 'P-0194', date: '02/14/2026', statusVariant: 'warning', statusLabel: 'Pending Review', size: '124 KB' },
  { type: 'Prior Auth', patientId: 'P-7742', date: '02/13/2026', statusVariant: 'info', statusLabel: 'Submitted', size: '98 KB' },
  { type: 'Explanation of Benefits', patientId: 'P-5503', date: '02/13/2026', statusVariant: 'active', statusLabel: 'Received', size: '217 KB' },
  { type: 'Remittance Advice', patientId: 'P-9918', date: '02/12/2026', statusVariant: 'active', statusLabel: 'Processed', size: '305 KB' },
  { type: 'Signature Form', patientId: 'P-2267', date: '02/12/2026', statusVariant: 'critical', statusLabel: 'Missing', size: '—' },
  { type: 'PCR', patientId: 'P-6641', date: '02/11/2026', statusVariant: 'active', statusLabel: 'Verified', size: '1.1 MB' },
  { type: 'ABN', patientId: 'P-1130', date: '02/11/2026', statusVariant: 'neutral', statusLabel: 'Archived', size: '133 KB' },
];

const SUPPORTED_TYPES = ['PDF', 'TIFF', 'PNG', 'JPG', 'DOCX', 'HL7', 'XML'];

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

export default function DocumentsPage() {
  const [dragOver, setDragOver] = useState(false);

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
            Documents &amp; Attachments
          </h1>
        </div>

        {/* Two-column layout */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left: Document List (2/3) */}
          <div style={{ flex: '2 1 0' }}>
            <div className="label-caps mb-3" style={{ color: 'var(--color-text-muted)', letterSpacing: 'var(--tracking-label)' }}>
              Document List
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
                    <th style={TH}>Type</th>
                    <th style={TH}>Patient ID</th>
                    <th style={TH}>Date</th>
                    <th style={{ ...TH, textAlign: 'center' }}>Status</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Size</th>
                    <th style={{ ...TH, textAlign: 'center' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {DOCUMENTS.map((doc, i) => (
                    <tr
                      key={`${doc.patientId}-${i}`}
                      style={{
                        background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                      }}
                    >
                      <td
                        style={{
                          ...TD,
                          fontWeight: 600,
                          color: 'var(--color-text-primary)',
                        }}
                      >
                        {doc.type}
                      </td>
                      <td
                        style={{
                          ...TD,
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--color-text-muted)',
                        }}
                      >
                        {doc.patientId}
                      </td>
                      <td style={TD}>{doc.date}</td>
                      <td style={{ ...TD, textAlign: 'center' }}>
                        <StatusChip status={doc.statusVariant} size="sm">
                          {doc.statusLabel}
                        </StatusChip>
                      </td>
                      <td
                        style={{
                          ...TD,
                          textAlign: 'right',
                          fontFamily: 'var(--font-mono)',
                          color: doc.size === '—' ? 'var(--color-text-muted)' : 'var(--color-text-secondary)',
                        }}
                      >
                        {doc.size}
                      </td>
                      <td style={{ ...TD, textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                          {doc.size !== '—' && (
                            <button
                              style={{
                                padding: '3px 10px',
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
                              }}
                            >
                              Download
                            </button>
                          )}
                          <button
                            style={{
                              padding: '3px 10px',
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
                            }}
                          >
                            View
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right: Upload Panel (1/3) */}
          <div style={{ flex: '1 1 0', minWidth: '260px' }}>
            <div className="label-caps mb-3" style={{ color: 'var(--color-text-muted)', letterSpacing: 'var(--tracking-label)' }}>
              Upload Documents
            </div>

            {/* Drop Zone */}
            <div
              style={{
                background: 'var(--color-bg-panel)',
                clipPath: 'var(--chamfer-8)',
                padding: '32px 24px',
                marginBottom: '12px',
                border: `2px dashed ${dragOver ? 'var(--color-brand-orange)' : 'var(--color-border-strong)'}`,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '12px',
                transition: 'border-color var(--duration-fast)',
                cursor: 'pointer',
              }}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => { e.preventDefault(); setDragOver(false); }}
            >
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  background: dragOver
                    ? 'var(--color-brand-orange-ghost)'
                    : 'var(--color-bg-panel-raised)',
                  clipPath: 'var(--chamfer-8)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '20px',
                  color: dragOver ? 'var(--color-brand-orange)' : 'var(--color-text-muted)',
                  transition: 'all var(--duration-fast)',
                }}
                aria-hidden="true"
              >
                &#x2191;
              </div>
              <div style={{ textAlign: 'center' }}>
                <div
                  style={{
                    fontSize: 'var(--text-body)',
                    color: dragOver ? 'var(--color-brand-orange)' : 'var(--color-text-secondary)',
                    fontWeight: 600,
                    marginBottom: '4px',
                  }}
                >
                  Drop files here
                </div>
                <div style={{ fontSize: 'var(--text-body)', color: 'var(--color-text-muted)' }}>
                  or click to browse
                </div>
              </div>
            </div>

            {/* Supported Types */}
            <div
              style={{
                background: 'var(--color-bg-panel)',
                clipPath: 'var(--chamfer-8)',
                padding: '16px',
                marginBottom: '12px',
              }}
            >
              <div className="micro-caps mb-2" style={{ color: 'var(--color-text-muted)' }}>
                Supported Formats
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {SUPPORTED_TYPES.map((t) => (
                  <span
                    key={t}
                    style={{
                      padding: '3px 8px',
                      background: 'var(--color-bg-panel-raised)',
                      clipPath: 'var(--chamfer-4)',
                      border: '1px solid var(--color-border-default)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 'var(--text-micro)',
                      color: 'var(--color-text-secondary)',
                      letterSpacing: 'var(--tracking-micro)',
                    }}
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>

            {/* Recent Uploads Count */}
            <div
              style={{
                background: 'var(--color-bg-panel)',
                clipPath: 'var(--chamfer-8)',
                padding: '16px',
              }}
            >
              <div className="micro-caps mb-1" style={{ color: 'var(--color-text-muted)' }}>
                Recent Uploads
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--text-h3)',
                  fontWeight: 700,
                  color: 'var(--color-system-billing)',
                }}
              >
                38
              </div>
              <div style={{ fontSize: 'var(--text-body)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                Files uploaded in last 7 days
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
