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
      style={{ borderColor: `${c[status]}40`, color: c[status], background: `${c[status]}12` }}
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

const ALL_DOCS = [
  { name: 'Agency A BAA', category: 'BAA', status: 'Executed', date: 'Jan 15', actions: ['View', 'Download'] },
  { name: 'Agency B Service Agreement', category: 'Contract', status: 'Pending Signature', date: 'Jan 22', actions: ['View', 'Send Reminder'] },
  { name: 'Q4 Compliance Certificate', category: 'Certificate', status: 'Active', date: 'Dec 31', actions: ['View', 'Download'] },
  { name: 'ROI Proposal – Agency C', category: 'Proposal', status: 'Sent', date: 'Jan 18', actions: ['View', 'Download'] },
  { name: 'HIPAA BAA Template v3', category: 'BAA', status: 'Template', date: 'Jan 1', actions: ['View', 'Edit'] },
  { name: 'Agency D Contract', category: 'Contract', status: 'Executed', date: 'Nov 10', actions: ['View', 'Download'] },
  { name: 'NEMSIS Certification Letter', category: 'Certificate', status: 'Active', date: 'Oct 15', actions: ['View', 'Download'] },
  { name: 'Agency E Renewal Agreement', category: 'Contract', status: 'Draft', date: 'Jan 25', actions: ['View', 'Edit'] },
  { name: 'Data Processing Addendum', category: 'Legal', status: 'Executed', date: 'Sep 5', actions: ['View', 'Download'] },
  { name: 'Privacy Policy v4', category: 'Legal', status: 'Active', date: 'Dec 1', actions: ['View', 'Download'] },
  { name: 'Terms of Service v2', category: 'Legal', status: 'Active', date: 'Dec 1', actions: ['View', 'Download'] },
  { name: 'Invoice Template', category: 'Template', status: 'Active', date: 'Jan 1', actions: ['View', 'Edit'] },
];

const TEMPLATES = [
  'BAA Template',
  'Service Agreement',
  'ROI Proposal',
  'Invoice',
  'NDA',
  'Data Processing Addendum',
];

function statusBadge(s: string) {
  if (s === 'Executed' || s === 'Active') return <Badge label={s} status="ok" />;
  if (s === 'Pending Signature') return <Badge label={s} status="warn" />;
  if (s === 'Sent') return <Badge label={s} status="info" />;
  if (s === 'Draft') return <Badge label={s} status="warn" />;
  return <Badge label={s} status="info" />;
}

export default function DocumentsVaultPage() {
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState('All');

  const filtered = ALL_DOCS.filter((d) => {
    const matchSearch = d.name.toLowerCase().includes(search.toLowerCase());
    const matchCat = catFilter === 'All' || d.category === catFilter;
    return matchSearch && matchCat;
  });

  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-6 space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-bold text-orange-dim font-mono tracking-widest uppercase">
            MODULE 11 · FOUNDER TOOLS
          </span>
          <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-orange transition-colors">
            ← Back to Founder OS
          </Link>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary" style={{ textShadow: '0 0 24px rgba(255,107,26,0.3)' }}>
          Documents Vault
        </h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Contracts · BAAs · proposals · compliance certificates · legal</p>
      </motion.div>

      {/* MODULE 3 — Document Stats */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Total Documents', value: '12', status: 'info' as const },
            { label: 'Pending Signature', value: '2', status: 'warn' as const },
            { label: 'Expiring in 90d', value: '1', status: 'warn' as const },
            { label: 'Storage Used', value: '24 MB', status: 'ok' as const },
          ].map((s) => (
            <Panel key={s.label} className="flex flex-col gap-1">
              <span className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">{s.label}</span>
              <span className="text-2xl font-bold" style={{ color: s.value === '2' || s.value === '1' ? 'var(--color-status-warning)' : 'rgba(255,255,255,0.9)' }}>
                {s.value}
              </span>
              <Badge label={s.status} status={s.status} />
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 1 — Search & Filter */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Panel>
          <SectionHeader number="1" title="Search & Filter" />
          <div className="flex flex-col md:flex-row gap-3 items-start md:items-center">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search documents..."
              className="flex-1 bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-xs text-text-primary px-3 py-2 rounded-sm outline-none focus:border-orange placeholder:text-[rgba(255,255,255,0.2)]"
            />
            <select
              value={catFilter}
              onChange={(e) => setCatFilter(e.target.value)}
              className="bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-xs text-text-primary px-3 py-2 rounded-sm outline-none focus:border-orange"
            >
              {['All', 'Contracts', 'BAA', 'Proposals', 'Certificates', 'Legal'].map((c) => (
                <option key={c} value={c} className="bg-bg-panel">{c}</option>
              ))}
            </select>
            <span className="text-[11px] text-[rgba(255,255,255,0.4)] whitespace-nowrap">
              Showing {filtered.length} document{filtered.length !== 1 ? 's' : ''}
            </span>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 2 — Recent Documents */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <Panel>
          <SectionHeader number="2" title="Recent Documents" />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border-subtle">
                  {['Document', 'Category', 'Status', 'Date', 'Actions'].map((h) => (
                    <th key={h} className="text-left py-1.5 px-2 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((doc, i) => (
                  <tr key={i} className="border-b border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.02)]">
                    <td className="py-2 px-2 text-[rgba(255,255,255,0.8)] font-medium">{doc.name}</td>
                    <td className="py-2 px-2 text-[rgba(255,255,255,0.45)]">{doc.category}</td>
                    <td className="py-2 px-2">{statusBadge(doc.status)}</td>
                    <td className="py-2 px-2 font-mono text-[rgba(255,107,26,0.7)] text-[11px]">{doc.date}</td>
                    <td className="py-2 px-2">
                      <div className="flex gap-2">
                        {doc.actions.map((a) => (
                          <button
                            key={a}
                            className="text-[10px] font-semibold px-2 py-0.5 rounded-sm transition-all hover:brightness-110"
                            style={{
                              background: a === 'View' ? 'rgba(41,182,246,0.1)' : 'rgba(255,107,26,0.1)',
                              color: a === 'View' ? 'var(--color-status-info)' : 'var(--color-brand-orange)',
                              border: `1px solid ${a === 'View' ? 'rgba(41,182,246,0.25)' : 'rgba(255,107,26,0.25)'}`,
                            }}
                          >
                            {a}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 4 — Signature Queue */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Panel>
          <SectionHeader number="4" title="Signature Queue" sub="awaiting action" />
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-sm" style={{ background: 'rgba(255,152,0,0.06)', border: '1px solid rgba(255,152,0,0.2)' }}>
              <div>
                <p className="text-xs font-semibold text-[rgba(255,255,255,0.85)]">Agency B Service Agreement</p>
                <p className="text-[10px] text-[rgba(255,255,255,0.4)] mt-0.5">Sent Jan 22 · Waiting for client signature</p>
              </div>
              <button
                className="text-[10px] font-bold px-3 py-1.5 rounded-sm uppercase tracking-wider transition-all hover:brightness-110"
                style={{ background: 'rgba(255,152,0,0.15)', color: 'var(--q-yellow)', border: '1px solid rgba(255,152,0,0.35)' }}
              >
                Send Reminder
              </button>
            </div>
            <div className="flex items-center justify-between p-3 rounded-sm" style={{ background: 'rgba(255,107,26,0.06)', border: '1px solid rgba(255,107,26,0.2)' }}>
              <div>
                <p className="text-xs font-semibold text-[rgba(255,255,255,0.85)]">Agency E Renewal Agreement</p>
                <p className="text-[10px] text-[rgba(255,255,255,0.4)] mt-0.5">Draft · Not yet sent</p>
              </div>
              <button
                className="text-[10px] font-bold px-3 py-1.5 rounded-sm uppercase tracking-wider transition-all hover:brightness-110"
                style={{ background: 'var(--color-brand-orange)', color: '#000' }}
              >
                Send for Signature
              </button>
            </div>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 5 — Templates Library */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <Panel>
          <SectionHeader number="5" title="Templates Library" />
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {TEMPLATES.map((t) => (
              <div
                key={t}
                className="flex items-center justify-between p-3 rounded-sm"
                style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}
              >
                <span className="text-xs text-[rgba(255,255,255,0.7)]">{t}</span>
                <button
                  className="text-[10px] font-bold px-2 py-1 rounded-sm uppercase tracking-wider transition-all hover:brightness-110 ml-2 whitespace-nowrap"
                  style={{ background: 'rgba(255,107,26,0.12)', color: 'var(--q-orange)', border: '1px solid rgba(255,107,26,0.25)' }}
                >
                  Use Template
                </button>
              </div>
            ))}
          </div>
        </Panel>
      </motion.div>

      <div className="pt-2">
        <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.35)] hover:text-orange transition-colors">
          ← Back to Founder OS
        </Link>
      </div>
    </div>
  );
}
