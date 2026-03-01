'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useState, useEffect } from 'react';

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
  const colors = { ok: 'var(--color-status-active)', warn: 'var(--color-status-warning)', error: 'var(--color-brand-red)', info: 'var(--color-status-info)' };
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-semibold uppercase tracking-wider border"
      style={{
        borderColor: `color-mix(in srgb, ${colors[status]} 25%, transparent)`,
        color: colors[status],
        background: `color-mix(in srgb, ${colors[status]} 7%, transparent)`,
      }}>
      <span className="w-1 h-1 rounded-full" style={{ background: colors[status] }} />
      {label}
    </span>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-bg-panel border border-border-DEFAULT p-4" style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}>
      <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-1">{label}</div>
      <div className="text-xl font-bold" style={{ color: color ?? 'var(--color-text-primary)' }}>{value}</div>
      {sub && <div className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">{sub}</div>}
    </div>
  );
}

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-bg-panel border border-border-DEFAULT p-4 ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}>
      {children}
    </div>
  );
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-1.5 bg-[rgba(255,255,255,0.06)] rounded-full overflow-hidden">
      <motion.div className="h-full rounded-full" style={{ background: color }} initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8 }} />
    </div>
  );
}

const PERF_METRICS = [
  { label: 'CPU Utilization',     value: 12,  max: 100, color: 'var(--q-green)' },
  { label: 'Memory Utilization',  value: 38,  max: 100, color: 'var(--q-yellow)' },
  { label: 'Storage Utilization', value: 8.4, max: 100, color: 'var(--q-green)' },
  { label: 'Read IOPS',           value: 180, max: 1000, color: 'var(--color-status-info)' },
  { label: 'Write IOPS',          value: 160, max: 1000, color: 'var(--color-status-info)' },
];

const POOLS = [
  { name: 'api-pool',    size: 20, active: 14, idle: 6, waiting: 0 },
  { name: 'worker-pool', size: 10, active:  3, idle: 7, waiting: 0 },
  { name: 'admin-pool',  size:  5, active:  1, idle: 4, waiting: 0 },
];

const SLOW_QUERIES = [
  { query: 'SELECT incidents WHERE tenant_id=? LIMIT 100', avg: '42ms',  calls: 240, table: 'incidents'  },
  { query: 'UPDATE claims SET status=? WHERE id=?',        avg: '18ms',  calls: 120, table: 'claims'     },
  { query: 'INSERT INTO audit_logs ...',                   avg: '8ms',   calls: 840, table: 'audit_logs' },
  { query: 'SELECT patients WHERE ...',                    avg: '65ms',  calls:  60, table: 'patients'   },
  { query: 'SELECT vitals WHERE incident_id=?',            avg: '12ms',  calls: 480, table: 'vitals'     },
];

const CW_ALARMS = [
  { name: 'CPUUtilization',       threshold: '>80%',     current: '12%',   status: 'ok' as const },
  { name: 'FreeStorageSpace',     threshold: '<10GB',    current: '458GB', status: 'ok' as const },
  { name: 'DatabaseConnections',  threshold: '>180',     current: '47',    status: 'ok' as const },
  { name: 'ReadLatency',          threshold: '>200ms',   current: '4ms',   status: 'ok' as const },
  { name: 'WriteLatency',         threshold: '>200ms',   current: '6ms',   status: 'ok' as const },
];

export default function RDSPostgresHealth() {
  const [drillScheduled, setDrillScheduled] = useState(false);

  function handleScheduleDrill() {
    setDrillScheduled(true);
    setTimeout(() => setDrillScheduled(false), 1400);
  }

  return (
    <div className="min-h-screen bg-bg-void text-text-primary px-6 py-8 font-mono">
      <div className="max-w-6xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: 'var(--color-text-muted)' }}>
              MODULE 10 · INFRASTRUCTURE
            </div>
            <h1 className="text-2xl font-bold uppercase tracking-widest text-text-primary">RDS PostgreSQL Health</h1>
            <p className="text-[12px] text-[rgba(255,255,255,0.4)] mt-1">
              Multi-AZ · automated backups · connection pooling · performance insights
            </p>
          </div>
          <div className="mt-1">
            <Badge label="Available" status="ok" />
          </div>
        </div>

        {/* MODULE 1 — Database Overview */}
        <section>
          <SectionHeader number="1" title="Database Overview" sub="db.r6g.large · PostgreSQL 15" />
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <StatCard label="Status"           value="Available"    color="var(--color-status-active)" />
            <StatCard label="Connections"      value="47 / 200"     color="var(--color-status-info)" />
            <StatCard label="CPU"              value="12%"          color="var(--color-status-active)" />
            <StatCard label="Storage"          value="42 GB"        sub="/ 500 GB" />
            <StatCard label="Replication Lag"  value="0ms"          color="var(--color-status-active)" />
            <StatCard label="IOPS"             value={340}          />
          </div>
        </section>

        {/* MODULE 2 — Performance Metrics */}
        <section>
          <SectionHeader number="2" title="Performance Metrics" sub="CloudWatch Insights" />
          <Panel>
            <div className="space-y-4">
              {PERF_METRICS.map((m) => (
                <div key={m.label}>
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[11px] text-[rgba(255,255,255,0.5)] uppercase tracking-wider">{m.label}</span>
                    <span className="text-[11px] font-semibold" style={{ color: m.color }}>
                      {m.value}{m.max === 100 ? '%' : ''}{m.max !== 100 ? ` / ${m.max}` : ''}
                    </span>
                  </div>
                  <ProgressBar value={m.value} max={m.max} color={m.color} />
                </div>
              ))}
            </div>
          </Panel>
        </section>

        {/* MODULE 3 — Connection Pools */}
        <section>
          <SectionHeader number="3" title="Connection Pools" sub="PgBouncer · transaction mode" />
          <Panel>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-[rgba(255,255,255,0.35)] uppercase tracking-widest border-b border-border-subtle">
                    <th className="text-left py-2 pr-4 font-semibold">Pool</th>
                    <th className="text-right py-2 px-4 font-semibold">Size</th>
                    <th className="text-right py-2 px-4 font-semibold">Active</th>
                    <th className="text-right py-2 px-4 font-semibold">Idle</th>
                    <th className="text-right py-2 pl-4 font-semibold">Waiting</th>
                  </tr>
                </thead>
                <tbody>
                  {POOLS.map((p, i) => (
                    <tr key={p.name} className={`border-b border-border-subtle ${i % 2 === 0 ? 'bg-[rgba(255,255,255,0.01)]' : ''}`}>
                      <td className="py-2.5 pr-4 font-semibold text-[rgba(255,255,255,0.8)]">{p.name}</td>
                      <td className="py-2.5 px-4 text-right text-[rgba(255,255,255,0.6)]">{p.size}</td>
                      <td className="py-2.5 px-4 text-right" style={{ color: 'var(--q-green)' }}>{p.active}</td>
                      <td className="py-2.5 px-4 text-right text-[rgba(255,255,255,0.5)]">{p.idle}</td>
                      <td className="py-2.5 pl-4 text-right" style={{ color: p.waiting > 0 ? 'var(--color-status-warning)' : 'var(--color-status-active)' }}>{p.waiting}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </section>

        {/* MODULE 4 — Slow Query Log */}
        <section>
          <SectionHeader number="4" title="Slow Query Log" sub="sanitized · top 5 by avg duration" />
          <Panel>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-[rgba(255,255,255,0.35)] uppercase tracking-widest border-b border-border-subtle">
                    <th className="text-left py-2 pr-4 font-semibold">Query (sanitized)</th>
                    <th className="text-right py-2 px-4 font-semibold">Avg Duration</th>
                    <th className="text-right py-2 px-4 font-semibold">Calls/hr</th>
                    <th className="text-right py-2 pl-4 font-semibold">Table</th>
                  </tr>
                </thead>
                <tbody>
                  {SLOW_QUERIES.map((q, i) => (
                    <tr key={i} className={`border-b border-border-subtle ${i % 2 === 0 ? 'bg-[rgba(255,255,255,0.01)]' : ''}`}>
                      <td className="py-2.5 pr-4 text-text-secondary max-w-[280px] truncate">{q.query}</td>
                      <td className="py-2.5 px-4 text-right font-semibold"
                        style={{ color: parseInt(q.avg) > 50 ? 'var(--color-status-warning)' : 'var(--color-status-active)' }}>{q.avg}</td>
                      <td className="py-2.5 px-4 text-right text-[rgba(255,255,255,0.5)]">{q.calls}</td>
                      <td className="py-2.5 pl-4 text-right text-system-cad font-semibold">{q.table}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </section>

        {/* MODULE 5 — Backup Status */}
        <section>
          <SectionHeader number="5" title="Backup Status" sub="automated · S3 encrypted" />
          <Panel>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-12 gap-y-2.5">
              {[
                { k: 'Last Backup',        v: '2 hours ago',     badge: { label: 'ok', status: 'ok' as const } },
                { k: 'Retention Period',   v: '14 days',         badge: null },
                { k: 'Backup Window',      v: '03:00–04:00 UTC', badge: null },
                { k: 'Next Backup',        v: 'in 22 hours',     badge: null },
                { k: 'Last Restore Test',  v: '30 days ago',     badge: { label: 'warn', status: 'warn' as const } },
                { k: 'Backup Size',        v: '8.4 GB',          badge: null },
              ].map(({ k, v, badge }) => (
                <div key={k} className="flex justify-between items-center border-b border-border-subtle py-1.5">
                  <span className="text-[11px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">{k}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.8)]">{v}</span>
                    {badge && <Badge label={badge.label} status={badge.status} />}
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </section>

        {/* MODULE 6 — CloudWatch Alarms */}
        <section>
          <SectionHeader number="6" title="CloudWatch Alarms" sub="RDS alarm group" />
          <Panel>
            <div className="space-y-1">
              <div className="grid grid-cols-4 text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.3)] border-b border-border-subtle pb-2 mb-1">
                <span>Alarm</span>
                <span className="text-center">Threshold</span>
                <span className="text-center">Current</span>
                <span className="text-right">Status</span>
              </div>
              {CW_ALARMS.map((a, i) => (
                <div key={a.name} className={`grid grid-cols-4 items-center py-2 border-b border-border-subtle ${i % 2 === 0 ? 'bg-[rgba(255,255,255,0.01)]' : ''}`}>
                  <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.8)]">{a.name}</span>
                  <span className="text-[11px] text-[rgba(255,255,255,0.45)] text-center">{a.threshold}</span>
                  <span className="text-[11px] font-semibold text-center" style={{ color: 'var(--q-green)' }}>{a.current}</span>
                  <span className="text-right"><Badge label={a.status} status={a.status} /></span>
                </div>
              ))}
            </div>
          </Panel>
        </section>

        {/* MODULE 7 — Multi-AZ Status */}
        <section>
          <SectionHeader number="7" title="Multi-AZ Status" sub="synchronous replication" />
          <Panel>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
              {/* Primary */}
              <div className="bg-[rgba(76,175,80,0.04)] border border-[rgba(76,175,80,0.15)] p-4"
                style={{ clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)' }}>
                <div className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-3">Primary AZ</div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-[11px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Availability Zone</span>
                    <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.8)]">us-east-1a</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[11px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Status</span>
                    <Badge label="Primary / Active" status="ok" />
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[11px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Last Failover</span>
                    <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.5)]">Never</span>
                  </div>
                </div>
              </div>

              {/* Standby */}
              <div className="bg-[rgba(41,182,246,0.04)] border border-[rgba(41,182,246,0.15)] p-4"
                style={{ clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)' }}>
                <div className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-3">Standby AZ</div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-[11px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Availability Zone</span>
                    <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.8)]">us-east-1b</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[11px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Status</span>
                    <Badge label="Standby / Synced" status="info" />
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[11px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Replication Lag</span>
                    <span className="text-[11px] font-semibold" style={{ color: 'var(--q-green)' }}>0ms</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Failover drill row */}
            <div className="flex items-center justify-between border-t border-border-subtle pt-4">
              <div className="flex items-center gap-3">
                <span className="text-[11px] text-[rgba(255,255,255,0.45)] uppercase tracking-wider">Last failover drill:</span>
                <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.7)]">30 days ago</span>
                <Badge label="Due Soon" status="warn" />
              </div>
              <button
                onClick={handleScheduleDrill}
                className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-widest border transition-all"
                style={{
                  borderColor: 'rgba(255,107,26,0.4)',
                  color: drillScheduled ? 'var(--color-text-primary)' : 'var(--color-brand-orange)',
                  background: drillScheduled ? 'rgba(255,107,26,0.2)' : 'rgba(255,107,26,0.06)',
                }}
              >
                {drillScheduled ? 'Scheduled' : 'Schedule Drill'}
              </button>
            </div>
          </Panel>
        </section>

        {/* Back link */}
        <div className="pt-2 pb-8">
          <Link href="/founder" className="text-[12px] font-semibold uppercase tracking-wider transition-opacity hover:opacity-70" style={{ color: 'var(--q-orange)' }}>
            ← Back to Founder Command OS
          </Link>
        </div>

      </div>
    </div>
  );
}
