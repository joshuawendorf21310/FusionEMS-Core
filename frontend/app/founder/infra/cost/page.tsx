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
  const c = { ok: '#4caf50', warn: '#ff9800', error: '#e53935', info: '#29b6f6' };
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

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div
      className="bg-bg-panel border border-border-DEFAULT p-4"
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-1">{label}</div>
      <div className="text-xl font-bold" style={{ color: color ?? '#fff' }}>{value}</div>
      {sub && <div className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">{sub}</div>}
    </div>
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

const SERVICES = [
  { name: 'ECS Fargate', mtd: 380, pct: '30.5%', mom: '+2%', trend: 'up', trendColor: '#ff9800' },
  { name: 'RDS Multi-AZ', mtd: 210, pct: '16.8%', mom: '0%', trend: 'flat', trendColor: 'rgba(255,255,255,0.3)' },
  { name: 'ElastiCache', mtd: 85, pct: '6.8%', mom: '0%', trend: 'flat', trendColor: 'rgba(255,255,255,0.3)' },
  { name: 'ALB', mtd: 42, pct: '3.4%', mom: '+1%', trend: 'up-small', trendColor: '#ff9800' },
  { name: 'S3', mtd: 28, pct: '2.2%', mom: '+5%', trend: 'up', trendColor: '#ff9800' },
  { name: 'CloudFront', mtd: 18, pct: '1.4%', mom: '-2%', trend: 'down', trendColor: '#4caf50' },
  { name: 'Route53', mtd: 5, pct: '0.4%', mom: '0%', trend: 'flat', trendColor: 'rgba(255,255,255,0.3)' },
  { name: 'Other', mtd: 479, pct: '38.4%', mom: '+1%', trend: 'up-small', trendColor: '#ff9800' },
];

function TrendIcon({ trend, color }: { trend: string; color: string }) {
  if (trend === 'up' || trend === 'up-small') {
    return <span style={{ color }} className="text-xs font-bold">↑</span>;
  }
  if (trend === 'down') {
    return <span style={{ color }} className="text-xs font-bold">↓</span>;
  }
  return <span style={{ color }} className="text-xs font-bold">—</span>;
}

const MONTHS = [
  { label: 'Aug', cost: 980 },
  { label: 'Sep', cost: 1020 },
  { label: 'Oct', cost: 1100 },
  { label: 'Nov', cost: 1150 },
  { label: 'Dec', cost: 1184 },
  { label: 'Jan', cost: 1247 },
];

const ALERTS: { text: string; status: 'ok' | 'warn' | 'error' | 'info' }[] = [
  { text: 'S3 costs increased 5% MoM — review storage lifecycle rules', status: 'info' },
  { text: 'Fargate CPU over-provisioned — potential $45/mo saving by right-sizing', status: 'warn' },
  { text: 'All services within monthly budget', status: 'ok' },
];

const TENANTS = [
  { name: 'Agency-A1', exports: 412, compute: '48hrs', cost: '$124' },
  { name: 'Agency-B2', exports: 280, compute: '32hrs', cost: '$86' },
  { name: 'Agency-C3', exports: 190, compute: '22hrs', cost: '$62' },
  { name: 'Agency-D4', exports: 88, compute: '10hrs', cost: '$31' },
];

const OPTIMIZATIONS = [
  {
    title: 'Enable S3 Intelligent-Tiering',
    desc: 'Automatically moves objects between tiers based on access frequency to reduce storage costs.',
    saving: '~$8/mo',
  },
  {
    title: 'Use Fargate Savings Plan',
    desc: 'Commit to consistent compute usage in exchange for a discounted rate on Fargate workloads.',
    saving: '~$100/mo',
  },
  {
    title: 'Right-size worker ECS tasks',
    desc: 'Worker tasks are currently provisioned at 2 vCPU but analysis shows 1 vCPU is sufficient.',
    saving: '~$45/mo',
  },
  {
    title: 'Enable RDS read replica for reporting',
    desc: 'Offload heavy reporting queries to a read replica to reduce primary DB load and latency.',
    saving: '$0 (performance gain)',
  },
];

export default function InfraCostPage() {
  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-6 space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="text-[10px] font-bold font-mono text-orange-dim uppercase tracking-widest mb-1">
            MODULE 10 · INFRASTRUCTURE
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">Infrastructure Cost Dashboard</h1>
          <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">
            AWS spend · service breakdown · budget tracking · optimization
          </p>
        </div>
        <Badge label="Within Budget" status="ok" />
      </div>

      {/* MODULE 1 — Cost Overview */}
      <section>
        <SectionHeader number="1" title="Cost Overview" />
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <StatCard label="MTD Total" value="$1,247" color="#fff" />
          <StatCard label="Last Month" value="$1,184" color="#fff" />
          <StatCard label="Projected" value="$1,310" color="#ff9800" />
          <StatCard label="Budget" value="$1,500" color="#fff" />
          <StatCard label="Budget Remaining" value="$253" color="#4caf50" />
          <StatCard label="YTD Total" value="$8,420" color="#fff" />
        </div>
      </section>

      {/* MODULE 2 — Cost by Service */}
      <section>
        <SectionHeader number="2" title="Cost by Service" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[rgba(255,255,255,0.35)] uppercase tracking-widest text-[10px]">
                  <th className="text-left pb-2 pr-4 font-semibold">Service</th>
                  <th className="text-left pb-2 pr-4 font-semibold">MTD Cost</th>
                  <th className="text-left pb-2 pr-4 font-semibold">% of Total</th>
                  <th className="text-left pb-2 pr-4 font-semibold">MoM Change</th>
                  <th className="text-left pb-2 font-semibold">Trend</th>
                </tr>
              </thead>
              <tbody>
                {SERVICES.map((svc) => (
                  <tr key={svc.name} className="border-t border-border-subtle">
                    <td className="py-2 pr-4 text-[rgba(255,255,255,0.8)]">{svc.name}</td>
                    <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.7)]">${svc.mtd}</td>
                    <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{svc.pct}</td>
                    <td className="py-2 pr-4" style={{ color: svc.trendColor }}>{svc.mom}</td>
                    <td className="py-2"><TrendIcon trend={svc.trend} color={svc.trendColor} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>

      {/* MODULE 3 — 6-Month Cost Trend */}
      <section>
        <SectionHeader number="3" title="6-Month Cost Trend" />
        <Panel>
          <div className="space-y-3">
            {MONTHS.map((m) => (
              <div key={m.label} className="flex items-center gap-3">
                <span className="text-[11px] font-mono text-[rgba(255,255,255,0.4)] w-8 flex-shrink-0">{m.label}</span>
                <div className="flex-1">
                  <ProgressBar value={m.cost} max={1500} color="#94a3b8" />
                </div>
                <span className="text-[11px] font-mono text-[rgba(255,255,255,0.6)] w-14 text-right flex-shrink-0">${m.cost.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      {/* MODULE 4 — Reserved vs On-Demand */}
      <section>
        <SectionHeader number="4" title="Reserved vs On-Demand" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Panel>
            <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-3">Current Savings</div>
            <div className="space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-xs text-[rgba(255,255,255,0.75)]">RDS Reserved</div>
                  <div className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">1-year reserved instance active</div>
                </div>
                <span className="text-sm font-bold text-status-active">-$85/mo</span>
              </div>
              <div className="border-t border-[rgba(255,255,255,0.05)] pt-3 flex justify-between items-start">
                <div>
                  <div className="text-xs text-[rgba(255,255,255,0.75)]">Fargate Spot</div>
                  <div className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">18% of tasks on Spot pricing</div>
                </div>
                <span className="text-[11px] font-mono text-[rgba(255,255,255,0.5)]">18%</span>
              </div>
            </div>
          </Panel>
          <Panel>
            <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-3">Optimization Potential</div>
            <div className="space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-xs text-[rgba(255,255,255,0.75)]">Full RDS Reservation</div>
                  <div className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">Reserve remaining on-demand instances</div>
                </div>
                <span className="text-sm font-bold text-status-warning">+$42/mo</span>
              </div>
              <div className="border-t border-[rgba(255,255,255,0.05)] pt-3 flex justify-between items-start">
                <div>
                  <div className="text-xs text-[rgba(255,255,255,0.75)]">Fargate Savings Plan</div>
                  <div className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">Commit to hourly compute spend</div>
                </div>
                <span className="text-sm font-bold text-status-warning">+$100/mo</span>
              </div>
            </div>
          </Panel>
        </div>
      </section>

      {/* MODULE 5 — Cost Alerts */}
      <section>
        <SectionHeader number="5" title="Cost Alerts" />
        <Panel>
          <div className="space-y-3">
            {ALERTS.map((alert, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-border-subtle last:border-0">
                <Badge label={alert.status} status={alert.status} />
                <span className="text-xs text-text-secondary">{alert.text}</span>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      {/* MODULE 6 — Cost Per Tenant */}
      <section>
        <SectionHeader number="6" title="Cost Per Tenant" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[rgba(255,255,255,0.35)] uppercase tracking-widest text-[10px]">
                  <th className="text-left pb-2 pr-4 font-semibold">Tenant</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Exports/mo</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Compute hrs</th>
                  <th className="text-left pb-2 font-semibold">Est. Cost</th>
                </tr>
              </thead>
              <tbody>
                {TENANTS.map((t) => (
                  <tr key={t.name} className="border-t border-border-subtle">
                    <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.7)]">{t.name}</td>
                    <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.55)]">{t.exports}</td>
                    <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.55)]">{t.compute}</td>
                    <td className="py-2 font-mono font-semibold text-[rgba(255,255,255,0.75)]">{t.cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>

      {/* MODULE 7 — Optimization Recommendations */}
      <section>
        <SectionHeader number="7" title="Optimization Recommendations" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {OPTIMIZATIONS.map((opt, i) => (
            <Panel key={i}>
              <div className="text-xs font-bold text-[rgba(255,255,255,0.85)] mb-1">{opt.title}</div>
              <div className="text-[11px] text-[rgba(255,255,255,0.45)] mb-3 leading-relaxed">{opt.desc}</div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.3)]">Est. Saving</span>
                <span className="text-xs font-bold text-status-active">{opt.saving}</span>
              </div>
            </Panel>
          ))}
        </div>
      </section>

      {/* Back */}
      <div>
        <Link href="/founder" className="text-xs text-system-cad hover:text-text-primary transition-colors">
          ← Back to Founder OS
        </Link>
      </div>
    </div>
  );
}
