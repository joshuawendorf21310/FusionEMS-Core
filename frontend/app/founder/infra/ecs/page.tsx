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
      style={{ borderColor: `${colors[status]}40`, color: colors[status], background: `${colors[status]}12` }}>
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

const SERVICES = [
  { name: 'api-service',     tasks: '2/2', cpu: 34, mem: 41, status: 'ok' as const },
  { name: 'worker-service',  tasks: '2/2', cpu: 12, mem: 28, status: 'ok' as const },
  { name: 'opa-sidecar',     tasks: '1/1', cpu:  2, mem:  8, status: 'ok' as const },
  { name: 'otel-collector',  tasks: '1/1', cpu:  5, mem: 12, status: 'ok' as const },
  { name: 'redis-proxy',     tasks: '1/1', cpu:  8, mem: 15, status: 'ok' as const },
  { name: 'scheduler',       tasks: '1/1', cpu:  6, mem: 11, status: 'ok' as const },
];

const HEALTH_CHECKS = [
  { endpoint: '/health',    rt: '12ms',    status: 'ok' as const },
  { endpoint: '/api/v1/',   rt: '48ms',    status: 'ok' as const },
  { endpoint: '/ws',        rt: 'active',  status: 'ok' as const },
  { endpoint: '/metrics',   rt: '8ms',     status: 'ok' as const },
];

const LOGS = [
  { ts: '2026-02-27 09:42:01', svc: 'api-service',    level: 'INFO' as const,  msg: 'Request handled successfully: POST /api/v1/incidents (201)' },
  { ts: '2026-02-27 09:41:58', svc: 'worker-service', level: 'WARN' as const,  msg: 'High memory usage on worker task (82%)' },
  { ts: '2026-02-27 09:41:55', svc: 'otel-collector',  level: 'INFO' as const, msg: 'Trace batch exported: 1200 spans flushed to OTLP endpoint' },
  { ts: '2026-02-27 09:41:50', svc: 'scheduler',      level: 'INFO' as const,  msg: 'Scheduled job run completed: billing_sweep (0 errors)' },
  { ts: '2026-02-27 09:41:45', svc: 'redis-proxy',    level: 'INFO' as const,  msg: 'Connection pool healthy: 12/20 active connections' },
];

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function ECSClusterHealth() {
  const [refreshed, setRefreshed] = useState(false);

  function handleRefresh() {
    setRefreshed(true);
    setTimeout(() => setRefreshed(false), 1200);
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
            <h1 className="text-2xl font-bold uppercase tracking-widest text-text-primary">ECS Cluster Health</h1>
            <p className="text-[12px] text-[rgba(255,255,255,0.4)] mt-1">
              Fargate cluster · task health · ALB metrics · auto scaling
            </p>
          </div>
          <div className="flex items-center gap-3 mt-1">
            <Badge label="All Services Healthy" status="ok" />
            <button
              onClick={handleRefresh}
              className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-widest border transition-all"
              style={{
                borderColor: 'rgba(255,107,26,0.4)',
                color: refreshed ? 'var(--color-text-primary)' : 'var(--color-brand-orange)',
                background: refreshed ? 'rgba(255,107,26,0.2)' : 'rgba(255,107,26,0.06)',
              }}
            >
              {refreshed ? 'Refreshed' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* MODULE 1 — Cluster Overview */}
        <section>
          <SectionHeader number="1" title="Cluster Overview" sub="ECS Fargate · us-east-1" />
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <StatCard label="Running Tasks"  value={8}        color="var(--color-status-active)" />
            <StatCard label="Desired Tasks"  value={8}        />
            <StatCard label="Pending"        value={0}        color="var(--color-status-active)" />
            <StatCard label="CPU Utilization" value="34%"     color="var(--color-status-warning)" />
            <StatCard label="Memory Util"    value="41%"      color="var(--color-status-warning)" />
            <StatCard label="Uptime 30d"     value="99.97%"   color="var(--color-status-active)" />
          </div>
        </section>

        {/* MODULE 2 — Service Status Table */}
        <section>
          <SectionHeader number="2" title="Service Status" sub="per-service breakdown" />
          <Panel>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-[rgba(255,255,255,0.35)] uppercase tracking-widest border-b border-border-subtle">
                    <th className="text-left py-2 pr-4 font-semibold">Service</th>
                    <th className="text-right py-2 px-4 font-semibold">Tasks</th>
                    <th className="text-right py-2 px-4 font-semibold">CPU%</th>
                    <th className="text-right py-2 px-4 font-semibold">Memory%</th>
                    <th className="text-right py-2 pl-4 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {SERVICES.map((s, i) => (
                    <tr key={s.name} className={`border-b border-border-subtle ${i % 2 === 0 ? 'bg-[rgba(255,255,255,0.01)]' : ''}`}>
                      <td className="py-2.5 pr-4 font-semibold text-[rgba(255,255,255,0.8)]">{s.name}</td>
                      <td className="py-2.5 px-4 text-right text-[rgba(255,255,255,0.6)]">{s.tasks}</td>
                      <td className="py-2.5 px-4 text-right" style={{ color: s.cpu > 60 ? 'var(--color-status-warning)' : 'var(--color-status-active)' }}>{s.cpu}%</td>
                      <td className="py-2.5 px-4 text-right" style={{ color: s.mem > 60 ? 'var(--color-status-warning)' : 'var(--color-status-active)' }}>{s.mem}%</td>
                      <td className="py-2.5 pl-4 text-right"><Badge label={s.status} status={s.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </section>

        {/* MODULE 3 — Auto Scaling Policy */}
        <section>
          <SectionHeader number="3" title="Auto Scaling Policy" sub="Application Auto Scaling" />
          <Panel>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-12 gap-y-2.5">
              {[
                { k: 'Min Tasks',            v: '2' },
                { k: 'Max Tasks',            v: '10' },
                { k: 'Current Tasks',        v: '8' },
                { k: 'Target CPU',           v: '70%' },
                { k: 'Scale-Out Threshold',  v: '>70% CPU for 3 min' },
                { k: 'Scale-In Threshold',   v: '<30% CPU for 10 min' },
              ].map(({ k, v }) => (
                <div key={k} className="flex justify-between items-center border-b border-border-subtle py-1.5">
                  <span className="text-[11px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">{k}</span>
                  <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.8)]">{v}</span>
                </div>
              ))}
            </div>
          </Panel>
        </section>

        {/* MODULE 4 — ALB Metrics */}
        <section>
          <SectionHeader number="4" title="ALB Metrics" sub="Application Load Balancer" />
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <StatCard label="Request Rate"       value="342 req/min" />
            <StatCard label="P50 Latency"        value="48ms"        color="var(--color-status-active)" />
            <StatCard label="P95 Latency"        value="210ms"       color="var(--color-status-warning)" />
            <StatCard label="5xx Rate"           value="0.01%"       color="var(--color-status-active)" />
            <StatCard label="Active Connections" value={87}          />
          </div>
        </section>

        {/* MODULE 5 — Health Check Status */}
        <section>
          <SectionHeader number="5" title="Health Check Status" sub="ALB target group health" />
          <Panel>
            <div className="space-y-2">
              <div className="grid grid-cols-3 text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.3)] border-b border-border-subtle pb-2 mb-1">
                <span>Endpoint</span>
                <span className="text-center">Response Time</span>
                <span className="text-right">Status</span>
              </div>
              {HEALTH_CHECKS.map((h) => (
                <div key={h.endpoint} className="grid grid-cols-3 items-center py-1.5 border-b border-border-subtle">
                  <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.75)]">{h.endpoint}</span>
                  <span className="text-[11px] text-[rgba(255,255,255,0.5)] text-center">{h.rt}</span>
                  <span className="text-right"><Badge label={h.status} status={h.status} /></span>
                </div>
              ))}
            </div>
          </Panel>
        </section>

        {/* MODULE 6 — Container Log Preview */}
        <section>
          <SectionHeader number="6" title="Container Log Preview" sub="last 5 entries" />
          <Panel>
            <div className="space-y-1.5">
              {LOGS.map((l, i) => (
                <div key={i} className="flex items-start gap-3 py-1.5 border-b border-border-subtle last:border-0">
                  <span className="text-[10px] text-[rgba(255,255,255,0.25)] whitespace-nowrap shrink-0">{l.ts}</span>
                  <span className="text-[10px] font-semibold text-system-cad whitespace-nowrap shrink-0 w-28">{l.svc}</span>
                  <span className="shrink-0">
                    <Badge label={l.level} status={l.level === 'WARN' ? 'warn' : 'info'} />
                  </span>
                  <span className="text-[11px] text-[rgba(255,255,255,0.6)]">{l.msg}</span>
                </div>
              ))}
            </div>
          </Panel>
        </section>

        {/* MODULE 7 — Task History */}
        <section>
          <SectionHeader number="7" title="Task History" sub="last 7 days" />
          <Panel>
            <div className="text-[11px] text-[rgba(255,255,255,0.4)] mb-4">Last 7 days — all tasks stable</div>
            <div className="grid grid-cols-7 gap-2">
              {DAYS.map((day) => (
                <div key={day} className="flex flex-col items-center gap-2 p-3 bg-[rgba(255,255,255,0.02)] border border-border-subtle"
                  style={{ clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)' }}>
                  <span className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.35)]">{day}</span>
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: 'var(--color-status-active)', boxShadow: '0 0 6px color-mix(in srgb, var(--color-status-active) 53%, transparent)' }} />
                  <span className="text-[10px] font-bold" style={{ color: 'var(--q-green)' }}>8/8</span>
                </div>
              ))}
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
