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

const FUNNEL_STAGES = [
  { stage: 'Awareness', leads: 48, pct: 100, color: 'var(--color-status-info)' },
  { stage: 'Qualified', leads: 24, pct: 50, color: 'var(--q-green)' },
  { stage: 'Demo Scheduled', leads: 12, pct: 25, color: 'var(--color-system-compliance)' },
  { stage: 'Proposal Sent', leads: 6, pct: 12.5, color: 'var(--q-yellow)' },
  { stage: 'Negotiation', leads: 3, pct: 6.25, color: 'var(--q-red)' },
  { stage: 'Closed Won', leads: 2, pct: 4.2, color: 'var(--q-green)' },
];

const PIPELINE = [
  { agency: 'Agency B', stage: 'Proposal Sent', value: '$34,560/yr', days: 8, next: 'Follow up call' },
  { agency: 'Agency C', stage: 'Demo Scheduled', value: '$17,280/yr', days: 3, next: 'Demo Feb 5' },
  { agency: 'Agency D', stage: 'Negotiation', value: '$17,280/yr', days: 12, next: 'Contract review' },
  { agency: 'Agency E', stage: 'Qualified', value: '$8,640/yr', days: 5, next: 'Schedule demo' },
  { agency: 'Agency F', stage: 'Qualified', value: '$17,280/yr', days: 2, next: 'Send ROI proposal' },
  { agency: 'Agency G', stage: 'Awareness', value: '$8,640/yr', days: 1, next: 'Initial outreach' },
];

const CONVERSIONS = [
  { label: 'Lead → Qualified', pct: 50, color: 'var(--q-green)' },
  { label: 'Qualified → Demo', pct: 50, color: 'var(--q-green)' },
  { label: 'Demo → Proposal', pct: 50, color: 'var(--q-yellow)' },
  { label: 'Proposal → Close', pct: 33, color: 'var(--q-red)' },
];

const VELOCITY = [
  { stage: 'Awareness → Qualified', days: 4.2 },
  { stage: 'Qualified → Demo', days: 3.8 },
  { stage: 'Demo → Proposal', days: 2.1 },
  { stage: 'Proposal → Close', days: 18.4 },
];

function stageBadgeStatus(stage: string): 'ok' | 'warn' | 'error' | 'info' {
  if (stage === 'Closed Won' || stage === 'Demo Scheduled') return 'ok';
  if (stage === 'Proposal Sent') return 'info';
  if (stage === 'Negotiation') return 'warn';
  return 'info';
}

export default function SalesFunnelPage() {
  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-6 space-y-6">
      {/* Page Header */}
      <div className="border-b border-border-subtle pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold tracking-widest font-mono mb-1" style={{ color: 'rgba(255,152,0,0.6)' }}>
              MODULE 8 · ROI &amp; SALES
            </p>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--q-yellow)' }}>Sales Funnel Dashboard</h1>
            <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Lead pipeline · conversion rates · deal velocity · revenue forecast</p>
          </div>
          <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-status-warning transition-colors font-mono">
            ← Back to Founder OS
          </Link>
        </div>
      </div>

      {/* MODULE 1 — Funnel Overview */}
      <div className="grid grid-cols-5 gap-3">
        <StatCard label="Leads (30d)" value={24} color="var(--color-text-primary)" />
        <StatCard label="Qualified" value={12} color="var(--color-status-warning)" />
        <StatCard label="Proposals Sent" value={6} color="var(--color-status-info)" />
        <StatCard label="Negotiations" value={3} color="var(--color-system-compliance)" />
        <StatCard label="Closed Won (30d)" value={2} color="var(--color-status-active)" />
      </div>

      {/* MODULE 2 — Funnel Visualization */}
      <Panel>
        <SectionHeader number="2" title="Funnel Visualization" sub="Stage by stage conversion" />
        <div className="flex flex-col items-center gap-1 py-2">
          {FUNNEL_STAGES.map((s, i) => (
            <motion.div
              key={s.stage}
              className="flex items-center justify-between px-4 py-2 rounded-sm"
              style={{
                width: `${Math.max(s.pct, 20)}%`,
                background: `${s.color}18`,
                border: `1px solid ${s.color}30`,
                minWidth: '200px',
              }}
              initial={{ opacity: 0, scaleX: 0.6 }}
              animate={{ opacity: 1, scaleX: 1 }}
              transition={{ delay: i * 0.1, duration: 0.4 }}
            >
              <div className="flex items-center gap-3">
                <span className="text-[10px] font-mono" style={{ color: s.color }}>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.8)]">{s.stage}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[11px] font-bold" style={{ color: s.color }}>{s.leads} leads</span>
                <span className="text-[10px] text-[rgba(255,255,255,0.35)]">{s.pct}%</span>
              </div>
            </motion.div>
          ))}
        </div>
      </Panel>

      {/* MODULE 3 — Active Pipeline */}
      <Panel>
        <SectionHeader number="3" title="Active Pipeline" sub="6 active deals" />
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Agency', 'Stage', 'Deal Value', 'Days in Stage', 'Next Action'].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {PIPELINE.map((p, i) => (
                <tr key={i} className="border-b border-border-subtle hover:bg-[rgba(255,255,255,0.02)]">
                  <td className="py-2 pr-4 font-semibold text-[rgba(255,255,255,0.8)]">{p.agency}</td>
                  <td className="py-2 pr-4"><Badge label={p.stage} status={stageBadgeStatus(p.stage)} /></td>
                  <td className="py-2 pr-4 font-mono text-status-warning">{p.value}</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{p.days} days</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{p.next}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* MODULE 4 — Conversion Metrics */}
      <Panel>
        <SectionHeader number="4" title="Conversion Metrics" sub="Stage-to-stage rates" />
        <div className="space-y-4">
          {CONVERSIONS.map((c) => (
            <div key={c.label}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] text-[rgba(255,255,255,0.7)]">{c.label}</span>
                <span className="text-[11px] font-bold" style={{ color: c.color }}>{c.pct}%</span>
              </div>
              <ProgressBar value={c.pct} max={100} color={c.color} />
            </div>
          ))}
        </div>
      </Panel>

      {/* MODULE 5 — Revenue Forecast */}
      <Panel>
        <SectionHeader number="5" title="Revenue Forecast" sub="If all pipeline deals close" />
        <div className="grid grid-cols-3 gap-3 mb-4">
          <StatCard label="Best Case" value="$103,680/yr" sub="All deals close" color="var(--color-status-active)" />
          <StatCard label="Likely (weighted)" value="$62,208/yr" sub="60% probability" color="var(--color-status-warning)" />
          <StatCard label="Conservative" value="$34,560/yr" sub="Confirmed only" color="var(--color-status-info)" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-bg-input border border-border-subtle rounded-sm">
            <span className="text-[10px] text-[rgba(255,255,255,0.35)] uppercase tracking-wider block mb-1">Current ARR</span>
            <span className="text-lg font-bold text-[rgba(255,255,255,0.8)]">$48,000</span>
          </div>
          <div className="p-3 bg-bg-input border border-border-subtle rounded-sm">
            <span className="text-[10px] text-[rgba(255,255,255,0.35)] uppercase tracking-wider block mb-1">Target ARR</span>
            <span className="text-lg font-bold" style={{ color: 'var(--q-yellow)' }}>$240,000</span>
          </div>
        </div>
        <div className="mt-3">
          <div className="flex justify-between mb-1">
            <span className="text-[10px] text-[rgba(255,255,255,0.35)]">ARR Progress to Target</span>
            <span className="text-[10px] text-[rgba(255,255,255,0.35)]">20%</span>
          </div>
          <ProgressBar value={48000} max={240000} color="var(--color-status-warning)" />
        </div>
      </Panel>

      {/* MODULE 6 — Deal Velocity */}
      <Panel>
        <SectionHeader number="6" title="Deal Velocity" sub="Average time per stage" />
        <div className="space-y-3">
          {VELOCITY.map((v, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b border-border-subtle last:border-0">
              <span className="text-[11px] text-[rgba(255,255,255,0.7)]">{v.stage}</span>
              <span className="text-[11px] font-bold font-mono" style={{ color: 'var(--q-yellow)' }}>{v.days} days</span>
            </div>
          ))}
          <div className="flex items-center justify-between pt-2 border-t border-border-DEFAULT">
            <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.85)]">Total Avg Deal Cycle</span>
            <span className="text-[13px] font-bold" style={{ color: 'var(--q-green)' }}>28.5 days</span>
          </div>
        </div>
      </Panel>
    </div>
  );
}
