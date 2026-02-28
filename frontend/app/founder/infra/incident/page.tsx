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

const SERVICES_STATUS = [
  { name: 'API Gateway', uptime: '99.97%' },
  { name: 'PostgreSQL RDS', uptime: '99.99%' },
  { name: 'Redis Cache', uptime: '99.98%' },
  { name: 'AI Engine', uptime: '99.95%' },
  { name: 'Export Service', uptime: '99.97%' },
  { name: 'SMS / Voice', uptime: '99.90%' },
  { name: 'Billing Engine', uptime: '99.97%' },
  { name: 'WebSocket', uptime: '99.95%' },
];

const INCIDENT_HISTORY = [
  { date: 'Jan 15', title: 'API elevated latency', severity: 'medium', duration: '8 min', affected: 'api-service', resolution: 'Resolved: ECS task restart' },
  { date: 'Dec 28', title: 'Redis connection pool exhausted', severity: 'high', duration: '3 min', affected: 'redis', resolution: 'Resolved: Pool limit increased' },
  { date: 'Dec 15', title: 'Export SFTP timeout', severity: 'low', duration: '12 min', affected: 'export-service', resolution: 'Resolved: State API recovered' },
  { date: 'Nov 28', title: 'AI GPU memory spike', severity: 'medium', duration: '5 min', affected: 'ai-engine', resolution: 'Resolved: Model cache cleared' },
  { date: 'Nov 10', title: 'Database slow query', severity: 'low', duration: '18 min', affected: 'rds', resolution: 'Resolved: Query optimized' },
];

function severityBadge(s: string): 'ok' | 'warn' | 'error' | 'info' {
  if (s === 'high') return 'error';
  if (s === 'medium') return 'warn';
  return 'info';
}

const PLAYBOOKS = [
  { name: 'Database Down', desc: 'Follow PG-001: failover to standby, notify on-call', id: 'PG-001' },
  { name: 'API Degraded', desc: 'Follow API-002: check ECS health, rollback if needed', id: 'API-002' },
  { name: 'Export Failure Spike', desc: 'Follow EXP-003: check state APIs, enable retry engine', id: 'EXP-003' },
  { name: 'Auth Service Down', desc: 'Follow AUTH-004: check Cognito, enable maintenance mode', id: 'AUTH-004' },
  { name: 'AI Engine Overloaded', desc: 'Follow AI-005: reduce batch size, scale GPU instances', id: 'AI-005' },
];

const CONTACT_METHODS_FOUNDER = ['PagerDuty', 'SMS', 'Phone'];
const CONTACT_METHODS_TL = ['PagerDuty', 'SMS'];

export default function IncidentControlCenterPage() {
  const [incidentMode, setIncidentMode] = useState(false);

  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-6 space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="text-[10px] font-bold font-mono text-orange-dim uppercase tracking-widest mb-1">
            MODULE 10 · INFRASTRUCTURE
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">Incident Control Center</h1>
          <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">
            System status · incident history · response playbooks · on-call
          </p>
        </div>
      </div>

      {/* MODULE 1 — System Status Overview */}
      <section>
        <SectionHeader number="1" title="System Status Overview" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {SERVICES_STATUS.map((svc) => (
            <div
              key={svc.name}
              className="bg-bg-panel border border-border-DEFAULT p-4"
              style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
            >
              <div className="text-xs font-semibold text-[rgba(255,255,255,0.75)] mb-2">{svc.name}</div>
              <div className="mb-2">
                <Badge label="operational" status="ok" />
              </div>
              <div className="text-[10px] font-mono text-[rgba(255,255,255,0.35)]">{svc.uptime} uptime</div>
            </div>
          ))}
        </div>
      </section>

      {/* MODULE 2 — Active Incidents */}
      <section>
        <SectionHeader number="2" title="Active Incidents" />
        <Panel>
          <div
            className="flex items-center gap-4 p-4 rounded-sm"
            style={{ background: '#4caf5014', border: '1px solid #4caf5030' }}
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: '#4caf5022', border: '1px solid #4caf5050' }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8L6.5 11.5L13 5" stroke="#4caf50" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <div className="text-sm font-bold text-status-active tracking-wide uppercase">ALL SYSTEMS OPERATIONAL</div>
              <div className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">No active incidents · Last checked moments ago</div>
            </div>
          </div>
        </Panel>
      </section>

      {/* MODULE 3 — Incident History */}
      <section>
        <SectionHeader number="3" title="Incident History" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[rgba(255,255,255,0.35)] uppercase tracking-widest text-[10px]">
                  <th className="text-left pb-2 pr-4 font-semibold">Date</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Title</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Severity</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Duration</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Affected</th>
                  <th className="text-left pb-2 font-semibold">Resolution</th>
                </tr>
              </thead>
              <tbody>
                {INCIDENT_HISTORY.map((inc, i) => (
                  <tr key={i} className="border-t border-border-subtle">
                    <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.4)]">{inc.date}</td>
                    <td className="py-2 pr-4 text-[rgba(255,255,255,0.75)]">{inc.title}</td>
                    <td className="py-2 pr-4"><Badge label={inc.severity} status={severityBadge(inc.severity)} /></td>
                    <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.5)]">{inc.duration}</td>
                    <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.45)]">{inc.affected}</td>
                    <td className="py-2 text-[rgba(255,255,255,0.45)]">{inc.resolution}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>

      {/* MODULE 4 — Response Playbooks */}
      <section>
        <SectionHeader number="4" title="Response Playbooks" />
        <Panel>
          <div className="space-y-0">
            {PLAYBOOKS.map((pb, i) => (
              <div
                key={pb.id}
                className="flex items-center justify-between gap-4 py-3 border-b border-border-subtle last:border-0"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-[10px] font-mono text-[rgba(255,107,26,0.5)] flex-shrink-0">{pb.id}</span>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-[rgba(255,255,255,0.8)]">{pb.name}</div>
                    <div className="text-[11px] text-[rgba(255,255,255,0.4)] truncate">{pb.desc}</div>
                  </div>
                </div>
                <button
                  className="flex-shrink-0 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider rounded-sm border border-border-DEFAULT text-system-cad hover:bg-bg-overlay transition-colors"
                >
                  View Playbook
                </button>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      {/* MODULE 5 — Incident Mode Controls */}
      <section>
        <SectionHeader number="5" title="Incident Mode Controls" />
        <Panel>
          <p className="text-[11px] text-[rgba(255,255,255,0.4)] mb-4 leading-relaxed">
            Activating incident mode suspends all non-critical automated communications, routes all alerts to the founder dashboard, and enables war-room protocols.
          </p>

          {!incidentMode ? (
            <button
              onClick={() => setIncidentMode(true)}
              className="px-6 py-2.5 text-xs font-bold uppercase tracking-widest rounded-sm border border-red-ghost text-red hover:bg-red-ghost transition-colors"
              style={{ background: '#e5393508' }}
            >
              ACTIVATE INCIDENT MODE
            </button>
          ) : (
            <div className="space-y-3">
              <motion.div
                className="flex items-center gap-3 p-3 rounded-sm"
                style={{ background: '#e5393514', border: '1px solid #e5393540' }}
                animate={{ opacity: [1, 0.7, 1] }}
                transition={{ duration: 1.4, repeat: Infinity }}
              >
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: '#e53935' }} />
                <div>
                  <div className="text-xs font-bold text-red uppercase tracking-widest">INCIDENT MODE ACTIVE</div>
                  <div className="text-[11px] text-[rgba(255,255,255,0.5)] mt-0.5">
                    Non-critical comms suspended · War room routing engaged · Founder alerted
                  </div>
                </div>
              </motion.div>
              <button
                onClick={() => setIncidentMode(false)}
                className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wider rounded-sm border border-[rgba(255,255,255,0.12)] text-[rgba(255,255,255,0.5)] hover:bg-[rgba(255,255,255,0.05)] transition-colors"
              >
                Deactivate
              </button>
            </div>
          )}
        </Panel>
      </section>

      {/* MODULE 6 — Public Status Page */}
      <section>
        <SectionHeader number="6" title="Public Status Page" />
        <Panel>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-4">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-1">Status Page URL</div>
              <div className="text-[11px] font-mono text-system-billing">status.fusionemsquantum.com</div>
            </div>
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-1">Last Published</div>
              <div className="text-[11px] text-text-secondary">2 minutes ago</div>
            </div>
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-1">Agency Subscribers</div>
              <div className="text-[11px] font-bold text-text-primary">12</div>
            </div>
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-1">30d Uptime</div>
              <div className="text-[11px] font-bold text-status-active">99.97%</div>
            </div>
          </div>
          <button
            className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wider rounded-sm border border-border-DEFAULT text-system-cad hover:bg-bg-overlay transition-colors"
          >
            Publish Update
          </button>
        </Panel>
      </section>

      {/* MODULE 7 — On-Call Schedule */}
      <section>
        <SectionHeader number="7" title="On-Call Schedule" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Primary */}
          <Panel>
            <div className="flex items-center justify-between mb-2">
              <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.3)]">Primary On-Call</div>
              <Badge label="active" status="ok" />
            </div>
            <div className="text-sm font-bold text-[rgba(255,255,255,0.9)] mb-1">Founder</div>
            <div className="flex flex-wrap gap-1.5">
              {CONTACT_METHODS_FOUNDER.map((m) => (
                <span
                  key={m}
                  className="px-2 py-0.5 text-[10px] font-semibold rounded-sm border border-border-DEFAULT text-[rgba(255,255,255,0.5)]"
                  style={{ background: 'rgba(255,255,255,0.04)' }}
                >
                  {m}
                </span>
              ))}
            </div>
          </Panel>

          {/* Secondary */}
          <Panel>
            <div className="flex items-center justify-between mb-2">
              <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.3)]">Secondary On-Call</div>
              <Badge label="standby" status="info" />
            </div>
            <div className="text-sm font-bold text-[rgba(255,255,255,0.9)] mb-1">Tech Lead</div>
            <div className="flex flex-wrap gap-1.5">
              {CONTACT_METHODS_TL.map((m) => (
                <span
                  key={m}
                  className="px-2 py-0.5 text-[10px] font-semibold rounded-sm border border-border-DEFAULT text-[rgba(255,255,255,0.5)]"
                  style={{ background: 'rgba(255,255,255,0.04)' }}
                >
                  {m}
                </span>
              ))}
            </div>
          </Panel>
        </div>
        <div className="mt-3 px-1">
          <span className="text-[11px] text-[rgba(255,255,255,0.3)]">Next rotation: </span>
          <span className="text-[11px] text-[rgba(255,255,255,0.6)]">in 5 days</span>
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
