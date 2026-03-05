'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useState, useEffect } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

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

export default function ReportsPage() {
  const [data, setData] = useState<{ templates: any[], recent: any[], scheduled: any[], archive: any[] }>({
    templates: [],
    recent: [],
    scheduled: [],
    archive: []
  });

  useEffect(() => {
    const token = localStorage.getItem('token');
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    fetch(`${API}/api/v1/founder/reports`, { headers })
      .then(r => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-6 space-y-6">
      {/* Header */}
      <div className="border-b border-border-subtle pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold tracking-widest font-mono mb-1" style={{ color: 'rgba(41,182,246,0.6)' }}>
              MODULE 8 · TEMPLATES
            </p>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--color-status-info)' }}>Report Foundry</h1>
            <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Audit automation · clinical outcomes · denial intelligence</p>
          </div>
          <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-status-info transition-colors font-mono">
            ← Back to Founder OS
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Panel>
            <SectionHeader number="1" title="Report Matrix" sub={`${data.templates.length} system templates`} />
            <div className="space-y-3">
              {data.templates.map(t => (
                <div key={t.id} className="p-3 bg-bg-input border border-border-DEFAULT rounded-sm flex items-start justify-between hover:border-status-info/40 transition-colors cursor-pointer">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[12px] font-semibold text-[rgba(255,255,255,0.85)]">{t.name}</span>
                      <Badge label={t.freq} status="info" />
                    </div>
                    <p className="text-[11px] text-[rgba(255,255,255,0.4)]">{t.desc}</p>
                  </div>
                  <button className="text-[10px] font-semibold px-3 py-1.5 rounded-sm" style={{ background: 'color-mix(in srgb, var(--color-status-info) 9%, transparent)', color: 'var(--color-status-info)', border: '1px solid color-mix(in srgb, var(--color-status-info) 19%, transparent)' }}>
                    Generate
                  </button>
                </div>
              ))}
            </div>
          </Panel>

          <Panel>
            <SectionHeader number="2" title="Recent Executions" sub="Last 5 generated reports" />
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-border-subtle">
                  {['ID', 'Name', 'Domain', 'Date', 'Status'].map(h => (
                    <th key={h} className="text-left py-2 pr-4 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.recent.map(r => (
                  <tr key={r.id} className="border-b border-border-subtle hover:bg-[rgba(255,255,255,0.02)]">
                    <td className="py-2 pr-4 font-mono text-status-info">{r.id}</td>
                    <td className="py-2 pr-4 text-[rgba(255,255,255,0.7)]">{r.name}</td>
                    <td className="py-2 pr-4 text-[rgba(255,255,255,0.4)]">{r.type}</td>
                    <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{r.date}</td>
                    <td className="py-2 pr-4"><Badge label={r.status} status={r.statusKey as any} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel>
            <SectionHeader number="3" title="Scheduled Runs" sub="Automated cron jobs" />
            <div className="space-y-3">
              {data.scheduled.map((s, i) => (
                <div key={i} className="p-3 bg-bg-input border border-border-subtle rounded-sm">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.85)]">{s.name}</span>
                    <span className="text-[10px] font-mono text-status-warning">{s.time}</span>
                  </div>
                  <div className="flex items-center gap-4 text-[10px] text-[rgba(255,255,255,0.4)]">
                    <span>Target: <span className="text-[rgba(255,255,255,0.6)]">{s.targets}</span></span>
                    <span>Format: <span className="text-[rgba(255,255,255,0.6)]">{s.format}</span></span>
                  </div>
                </div>
              ))}
            </div>
            <button className="w-full mt-3 text-[10px] uppercase tracking-widest font-semibold py-2 rounded-sm border border-dashed border-status-info/30 text-status-info hover:bg-status-info/5 transition-colors">
              + Add Schedule
            </button>
          </Panel>

          <Panel>
            <SectionHeader number="4" title="Deep Archive" sub="Compliance retention" />
            <div className="space-y-2">
              {data.archive.map((a) => (
                <div key={a.year} className="flex items-center justify-between p-2 pl-3 bg-bg-input border-l-2 border-l-border-subtle hover:border-l-status-info transition-colors cursor-pointer">
                  <span className="text-[12px] font-mono text-[rgba(255,255,255,0.85)]">{a.year} Core Sync</span>
                  <div className="text-right">
                    <div className="text-[11px] text-[rgba(255,255,255,0.6)]">{a.count} artifacts</div>
                    <div className="text-[9px] text-[rgba(255,255,255,0.3)]">{a.size}</div>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
