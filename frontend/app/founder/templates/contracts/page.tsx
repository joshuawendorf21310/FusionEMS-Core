'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE ?? '';

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="border-b border-border-subtle pb-2 mb-4">
      <div className="flex items-baseline gap-3">
        <span className="text-[10px] font-bold text-orange-dim font-mono">MODULE {number}</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-[rgba(255,255,255,0.85)]">{title}</h2>
        {sub && <span className="text-xs text-[rgba(255,255,255,0.35)]">{sub}</span>}
      </div>
    </div>
  );
}

function Badge({ label, status }: { label: string; status: 'ok' | 'warn' | 'error' | 'info' }) {
  const c = { ok: 'var(--color-status-active)', warn: 'var(--color-status-warning)', error: 'var(--color-brand-red)', info: 'var(--color-status-info)' };
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-semibold uppercase tracking-wider border"
      style={{ borderColor: `color-mix(in srgb, ${c[status]} 25%, transparent)`, color: c[status], background: `color-mix(in srgb, ${c[status]} 7%, transparent)` }}
    >
      <span className="w-1 h-1 rounded-full" style={{ background: c[status] }} />
      {label}
    </span>
  );
}

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-bg-panel border border-border-DEFAULT p-4 ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div
      className="bg-bg-panel border border-border-DEFAULT p-4"
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-1">{label}</div>
      <div className="text-xl font-bold" style={{ color: color ?? 'var(--color-text-primary)' }}>{value}</div>
      {sub && <div className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">{sub}</div>}
    </div>
  );
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-1.5 bg-[rgba(255,255,255,0.06)] rounded-full overflow-hidden">
      <motion.div
        className="h-full rounded-full"
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.8 }}
      />
    </div>
  );
}

const TEMPLATES = [
  { id: 'msa', name: 'Master Service Agreement', desc: 'Full platform service agreement with SLA terms.', used: 4 },
  { id: 'baa', name: 'HIPAA Business Associate Agreement', desc: 'BAA for all data handling relationships.', used: 4 },
  { id: 'dpa', name: 'Data Processing Addendum', desc: 'GDPR/CCPA compliant DPA addendum.', used: 2 },
  { id: 'renewal', name: 'Agency Renewal Agreement', desc: 'Simplified renewal for existing clients.', used: 1 },
  { id: 'pilot', name: 'Pilot Program Agreement', desc: '90-day pilot with conversion terms.', used: 0 },
  { id: 'nda', name: 'NDA (Mutual)', desc: 'Standard mutual non-disclosure.', used: 3 },
];

const ACTIVE_CONTRACTS = [
  { id: 'MSA-001', agency: 'Agency A', type: 'Service Agreement', status: 'Executed', statusKey: 'ok' as const, signed: 'Jan 15, 2024', expiry: 'Jan 15, 2025' },
  { id: 'BAA-001', agency: 'Agency A', type: 'BAA', status: 'Executed', statusKey: 'ok' as const, signed: 'Jan 15, 2024', expiry: 'Jan 15, 2025' },
  { id: 'MSA-002', agency: 'Agency B', type: 'Service Agreement', status: 'Executed', statusKey: 'ok' as const, signed: 'Nov 10, 2023', expiry: 'Nov 10, 2024' },
  { id: 'BAA-002', agency: 'Agency B', type: 'BAA', status: 'Executed', statusKey: 'ok' as const, signed: 'Nov 10, 2023', expiry: 'Nov 10, 2024' },
  { id: 'MSA-003', agency: 'Agency C', type: 'Service Agreement', status: 'Pending', statusKey: 'warn' as const, signed: '—', expiry: '—' },
  { id: 'NDA-001', agency: 'Agency D', type: 'NDA', status: 'Executed', statusKey: 'ok' as const, signed: 'Dec 5, 2023', expiry: 'Dec 5, 2024' },
];

const TEMPLATE_VARS = ['{{agency_name}}', '{{start_date}}', '{{monthly_fee}}', '{{state}}'];

export default function ContractBuilderPage() {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [previewMode, setPreviewMode] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  function handleCopy(v: string) {
    navigator.clipboard.writeText(v).catch(() => {});
    setCopied(v);
    setTimeout(() => setCopied(null), 1200);
  }

  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-6 space-y-6">
      {/* Page Header */}
      <div className="border-b border-border-subtle pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold tracking-widest font-mono mb-1" style={{ color: 'rgba(41,182,246,0.6)' }}>
              MODULE 7 · TEMPLATES
            </p>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--color-status-info)' }}>Contract Builder</h1>
            <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Service agreements · BAAs · data processing · renewal contracts</p>
          </div>
          <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-status-info transition-colors font-mono">
            ← Back to Founder OS
          </Link>
        </div>
      </div>

      {/* MODULE 1 — Template Library */}
      <Panel>
        <SectionHeader number="1" title="Template Library" sub="6 templates available" />
        <div className="grid grid-cols-2 gap-3">
          {TEMPLATES.map((t) => (
            <div
              key={t.id}
              className="border border-border-DEFAULT p-3 bg-bg-input cursor-pointer transition-all"
              style={{
                clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)',
                borderColor: selectedTemplate === t.id ? 'color-mix(in srgb, var(--color-status-info) 12%, transparent)' : 'rgba(255,255,255,0.08)',
                background: selectedTemplate === t.id ? 'color-mix(in srgb, var(--color-status-info) 4%, transparent)' : 'var(--color-bg-input)',
              }}
              onClick={() => setSelectedTemplate(t.id)}
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <span className="text-[12px] font-semibold text-[rgba(255,255,255,0.85)] leading-tight">{t.name}</span>
                {t.used > 0 ? (
                  <Badge label={`Used ${t.used}x`} status="info" />
                ) : (
                  <Badge label="New" status="warn" />
                )}
              </div>
              <p className="text-[11px] text-[rgba(255,255,255,0.4)] mb-3">{t.desc}</p>
              <button
                className="text-[10px] font-semibold px-3 py-1 rounded-sm transition-colors"
                style={{ background: 'color-mix(in srgb, var(--color-status-info) 9%, transparent)', color: 'var(--color-status-info)', border: '1px solid color-mix(in srgb, var(--color-status-info) 19%, transparent)' }}
                onClick={(e) => { e.stopPropagation(); setSelectedTemplate(t.id); }}
              >
                Use Template
              </button>
            </div>
          ))}
        </div>
      </Panel>

      {/* MODULE 2 — Active Contracts */}
      <Panel>
        <SectionHeader number="2" title="Active Contracts" sub="6 contracts" />
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Contract', 'Agency', 'Type', 'Status', 'Signed Date', 'Expiry'].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ACTIVE_CONTRACTS.map((c, i) => (
                <tr key={c.id} className="border-b border-border-subtle hover:bg-[rgba(255,255,255,0.02)]">
                  <td className="py-2 pr-4 font-mono text-status-info">{c.id}</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.7)]">{c.agency}</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{c.type}</td>
                  <td className="py-2 pr-4"><Badge label={c.status} status={c.statusKey} /></td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{c.signed}</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{c.expiry}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* MODULE 3 — Expiring Soon */}
      <Panel>
        <SectionHeader number="3" title="Expiring Soon" sub="Within 90 days" />
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-bg-input border border-red-ghost rounded-sm">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[12px] font-semibold text-[rgba(255,255,255,0.85)]">MSA-002 — Agency B</span>
                <Badge label="37 days" status="error" />
              </div>
              <p className="text-[11px] text-[rgba(255,255,255,0.4)]">Expires Nov 10, 2024</p>
            </div>
            <button
              className="text-[10px] font-semibold px-3 py-1.5 rounded-sm"
              style={{ background: 'color-mix(in srgb, var(--color-brand-red) 9%, transparent)', color: 'var(--q-red)', border: '1px solid color-mix(in srgb, var(--color-brand-red) 19%, transparent)' }}
            >
              Send Renewal
            </button>
          </div>
          <div className="flex items-center justify-between p-3 bg-bg-input border border-status-warning/15 rounded-sm">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[12px] font-semibold text-[rgba(255,255,255,0.85)]">NDA-001 — Agency D</span>
                <Badge label="62 days" status="warn" />
              </div>
              <p className="text-[11px] text-[rgba(255,255,255,0.4)]">Expires Dec 5, 2024</p>
            </div>
            <button
              className="text-[10px] font-semibold px-3 py-1.5 rounded-sm"
              style={{ background: 'color-mix(in srgb, var(--color-status-warning) 9%, transparent)', color: 'var(--q-yellow)', border: '1px solid color-mix(in srgb, var(--color-status-warning) 19%, transparent)' }}
            >
              Send Renewal
            </button>
          </div>
        </div>
      </Panel>

      {/* MODULE 4 — Contract Editor */}
      <Panel>
        <SectionHeader number="4" title="Contract Editor" sub={selectedTemplate ? `Editing: ${TEMPLATES.find(t => t.id === selectedTemplate)?.name}` : 'No template selected'} />
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div
              className="border border-border-DEFAULT bg-bg-input p-4 min-h-[140px] flex items-center justify-center mb-3"
              style={{ clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)' }}
            >
              {selectedTemplate ? (
                <div className="w-full">
                  <p className="text-[11px] text-[rgba(255,255,255,0.5)] mb-2">Editing: <span className="text-status-info">{TEMPLATES.find(t => t.id === selectedTemplate)?.name}</span></p>
                  <div className="h-16 bg-[rgba(255,255,255,0.03)] border border-border-subtle rounded-sm flex items-center justify-center">
                    <span className="text-[10px] text-[rgba(255,255,255,0.2)]">Contract content area</span>
                  </div>
                </div>
              ) : (
                <p className="text-[11px] text-[rgba(255,255,255,0.3)]">Select a template to begin editing</p>
              )}
            </div>
            <div className="flex gap-2">
              <button
                disabled={!selectedTemplate}
                className="flex-1 text-[10px] font-semibold py-2 rounded-sm transition-colors disabled:opacity-30"
                style={{ background: 'color-mix(in srgb, var(--color-status-info) 9%, transparent)', color: 'var(--color-status-info)', border: '1px solid color-mix(in srgb, var(--color-status-info) 19%, transparent)' }}
              >
                Download as PDF
              </button>
              <button
                disabled={!selectedTemplate}
                className="flex-1 text-[10px] font-semibold py-2 rounded-sm transition-colors disabled:opacity-30"
                style={{ background: 'color-mix(in srgb, var(--color-status-active) 9%, transparent)', color: 'var(--q-green)', border: '1px solid color-mix(in srgb, var(--color-status-active) 19%, transparent)' }}
              >
                Send for Signature
              </button>
            </div>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-2">Template Variables</p>
            <div className="flex flex-wrap gap-2">
              {TEMPLATE_VARS.map((v) => (
                <button
                  key={v}
                  onClick={() => handleCopy(v)}
                  className="text-[10px] font-mono px-2 py-1 rounded-sm transition-all"
                  style={{
                    background: copied === v ? 'color-mix(in srgb, var(--color-status-info) 12%, transparent)' : 'color-mix(in srgb, var(--color-status-info) 6%, transparent)',
                    color: copied === v ? 'var(--color-status-active)' : 'var(--color-status-info)',
                    border: '1px solid color-mix(in srgb, var(--color-status-info) 14%, transparent)',
                  }}
                  title="Click to copy"
                >
                  {copied === v ? 'Copied!' : v}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-[rgba(255,255,255,0.25)] mt-2">Click variable to copy to clipboard</p>
          </div>
        </div>
      </Panel>

      {/* MODULE 5 — Signature Status */}
      <Panel>
        <SectionHeader number="5" title="Signature Status" sub="Awaiting signatures" />
        <div className="flex items-center justify-between p-3 bg-bg-input border border-status-warning/15 rounded-sm">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[12px] font-semibold text-[rgba(255,255,255,0.85)]">Agency C — MSA-003</span>
              <Badge label="Awaiting" status="warn" />
            </div>
            <p className="text-[11px] text-[rgba(255,255,255,0.4)]">Sent Jan 22 · 3 days awaiting signature</p>
          </div>
          <div className="flex gap-2">
            <button
              className="text-[10px] font-semibold px-3 py-1.5 rounded-sm"
              style={{ background: 'color-mix(in srgb, var(--color-status-warning) 9%, transparent)', color: 'var(--q-yellow)', border: '1px solid color-mix(in srgb, var(--color-status-warning) 19%, transparent)' }}
            >
              Resend
            </button>
            <button
              className="text-[10px] font-semibold px-3 py-1.5 rounded-sm"
              style={{ background: 'color-mix(in srgb, var(--color-status-info) 9%, transparent)', color: 'var(--color-status-info)', border: '1px solid color-mix(in srgb, var(--color-status-info) 19%, transparent)' }}
            >
              View Doc
            </button>
          </div>
        </div>
      </Panel>
    </div>
  );
}
