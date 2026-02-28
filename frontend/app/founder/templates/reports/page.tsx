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

const REPORT_TEMPLATES = [
  { id: 'monthly-compliance', name: 'Monthly Compliance Report', desc: 'NEMSIS/NIERS/NFIRS compliance summary.', freq: 'Monthly' },
  { id: 'ar-aging', name: 'AR Aging Report', desc: 'Accounts receivable by bucket.', freq: 'Weekly' },
  { id: 'export-perf', name: 'Export Performance Report', desc: 'Export success rates by state.', freq: 'Weekly' },
  { id: 'exec-brief', name: 'Executive Briefing', desc: 'AI-generated executive summary.', freq: 'Daily' },
  { id: 'payer-mix', name: 'Payer Mix Analysis', desc: 'Revenue by payer class.', freq: 'Monthly' },
  { id: 'cred-expiry', name: 'Credential Expiry Report', desc: 'Staff credential status.', freq: 'Monthly' },
];

const RECENT_REPORTS = [
  { name: 'Monthly Compliance Report', generated: 'Jan 26', period: 'January 2024', status: 'Ready', statusKey: 'ok' as const },
  { name: 'AR Aging Report', generated: 'Jan 26', period: 'Week of Jan 22', status: 'Ready', statusKey: 'ok' as const },
  { name: 'Export Performance', generated: 'Jan 25', period: 'Week of Jan 22', status: 'Ready', statusKey: 'ok' as const },
  { name: 'Executive Briefing', generated: 'Jan 26', period: 'Today', status: 'Ready', statusKey: 'ok' as const },
  { name: 'Monthly Compliance Report', generated: 'Dec 31', period: 'December 2023', status: 'Ready', statusKey: 'ok' as const },
  { name: 'Payer Mix Analysis', generated: 'Jan 1', period: 'Q4 2023', status: 'Ready', statusKey: 'ok' as const },
  { name: 'Credential Expiry Report', generated: 'Jan 1', period: 'January 2024', status: 'Ready', statusKey: 'ok' as const },
  { name: 'AR Aging Report', generated: 'Jan 19', period: 'Week of Jan 15', status: 'Ready', statusKey: 'ok' as const },
];

const SCHEDULED = [
  { name: 'Daily AI Brief', schedule: 'Every day 07:00 UTC', next: 'Tomorrow 07:00', recipient: 'founder@fusionemsquantum.com' },
  { name: 'Weekly AR Aging', schedule: 'Every Monday 08:00 UTC', next: 'Mon Feb 3', recipient: 'billing@fusionemsquantum.com' },
  { name: 'Monthly Compliance', schedule: '1st of month', next: 'Feb 1', recipient: 'compliance@fusionemsquantum.com' },
];

const ARCHIVE = [
  { month: 'January 2024', count: 4 },
  { month: 'December 2023', count: 3 },
  { month: 'November 2023', count: 3 },
  { month: 'October 2023', count: 3 },
  { month: 'September 2023', count: 2 },
];

export default function ReportTemplatesPage() {
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [brandingLogo, setBrandingLogo] = useState('FusionEMS Quantum');
  const [brandingCompany, setBrandingCompany] = useState('FusionEMS Quantum LLC');
  const [brandingColor, setBrandingColor] = useState('var(--color-status-info)');
  const [deliveryEmail, setDeliveryEmail] = useState('reports@fusionemsquantum.com');
  const [deliveryFormat, setDeliveryFormat] = useState<'PDF' | 'CSV'>('PDF');
  const [includeCharts, setIncludeCharts] = useState(true);

  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-6 space-y-6">
      {/* Page Header */}
      <div className="border-b border-border-subtle pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold tracking-widest font-mono mb-1" style={{ color: 'rgba(41,182,246,0.6)' }}>
              MODULE 7 · TEMPLATES
            </p>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--color-status-info)' }}>Report Templates</h1>
            <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Compliance reports · AR aging · export summaries · executive briefings</p>
          </div>
          <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-status-info transition-colors font-mono">
            ← Back to Founder OS
          </Link>
        </div>
      </div>

      {/* MODULE 1 — Available Report Templates */}
      <Panel>
        <SectionHeader number="1" title="Available Report Templates" sub="6 templates" />
        <div className="grid grid-cols-2 gap-3">
          {REPORT_TEMPLATES.map((t) => (
            <div
              key={t.id}
              className="border p-3 bg-bg-input cursor-pointer transition-all"
              style={{
                clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)',
                borderColor: selectedType === t.id ? 'color-mix(in srgb, var(--color-status-info) 19%, transparent)' : 'rgba(255,255,255,0.08)',
                background: selectedType === t.id ? 'color-mix(in srgb, var(--color-status-info) 4%, transparent)' : 'var(--color-bg-input)',
              }}
              onClick={() => setSelectedType(t.id)}
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <span className="text-[12px] font-semibold text-[rgba(255,255,255,0.85)] leading-tight">{t.name}</span>
                <Badge
                  label={t.freq}
                  status={t.freq === 'Daily' ? 'ok' : t.freq === 'Weekly' ? 'info' : 'warn'}
                />
              </div>
              <p className="text-[11px] text-[rgba(255,255,255,0.4)] mb-3">{t.desc}</p>
              <button
                className="text-[10px] font-semibold px-3 py-1 rounded-sm"
                style={{ background: 'color-mix(in srgb, var(--color-status-info) 9%, transparent)', color: 'var(--color-status-info)', border: '1px solid color-mix(in srgb, var(--color-status-info) 19%, transparent)' }}
                onClick={(e) => { e.stopPropagation(); setSelectedType(t.id); }}
              >
                Generate
              </button>
            </div>
          ))}
        </div>
      </Panel>

      {/* MODULE 2 — Recently Generated */}
      <Panel>
        <SectionHeader number="2" title="Recently Generated" sub="Last 8 reports" />
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Report', 'Generated', 'Period', 'Status', 'Download'].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {RECENT_REPORTS.map((r, i) => (
                <tr key={i} className="border-b border-border-subtle hover:bg-[rgba(255,255,255,0.02)]">
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.75)]">{r.name}</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{r.generated}</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{r.period}</td>
                  <td className="py-2 pr-4"><Badge label={r.status} status={r.statusKey} /></td>
                  <td className="py-2 pr-4">
                    <button
                      className="text-[10px] font-semibold px-2 py-0.5 rounded-sm"
                      style={{ background: 'color-mix(in srgb, var(--color-status-info) 6%, transparent)', color: 'var(--color-status-info)', border: '1px solid color-mix(in srgb, var(--color-status-info) 14%, transparent)' }}
                    >
                      PDF
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* MODULE 3 — Scheduled Reports */}
      <Panel>
        <SectionHeader number="3" title="Scheduled Reports" sub="3 active schedules" />
        <div className="space-y-2">
          {SCHEDULED.map((s, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-bg-input border border-border-subtle rounded-sm">
              <div>
                <span className="text-[12px] font-semibold text-[rgba(255,255,255,0.85)]">{s.name}</span>
                <div className="flex items-center gap-3 mt-0.5">
                  <span className="text-[10px] text-[rgba(255,255,255,0.35)]">{s.schedule}</span>
                  <span className="text-[10px] text-[rgba(255,255,255,0.35)]">·</span>
                  <span className="text-[10px] text-status-info">Next: {s.next}</span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-[rgba(255,255,255,0.35)] block">Recipient</span>
                <span className="text-[10px] font-mono text-[rgba(255,255,255,0.6)]">{s.recipient}</span>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* MODULE 4 — Report Settings */}
      <Panel>
        <SectionHeader number="4" title="Report Settings" />
        <div className="grid grid-cols-2 gap-6">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-3">Branding</p>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Logo / Header Name</label>
                <input
                  value={brandingLogo}
                  onChange={(e) => setBrandingLogo(e.target.value)}
                  className="w-full bg-bg-input border border-border-DEFAULT text-[11px] text-text-primary px-3 py-2 rounded-sm outline-none focus:border-status-info"
                />
              </div>
              <div>
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Company Name</label>
                <input
                  value={brandingCompany}
                  onChange={(e) => setBrandingCompany(e.target.value)}
                  className="w-full bg-bg-input border border-border-DEFAULT text-[11px] text-text-primary px-3 py-2 rounded-sm outline-none focus:border-status-info"
                />
              </div>
              <div>
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Accent Color</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={brandingColor}
                    onChange={(e) => setBrandingColor(e.target.value)}
                    className="w-8 h-8 rounded-sm border border-border-DEFAULT bg-bg-input cursor-pointer"
                  />
                  <span className="text-[11px] font-mono text-[rgba(255,255,255,0.5)]">{brandingColor}</span>
                </div>
              </div>
            </div>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-3">Delivery</p>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Email Recipient</label>
                <input
                  value={deliveryEmail}
                  onChange={(e) => setDeliveryEmail(e.target.value)}
                  className="w-full bg-bg-input border border-border-DEFAULT text-[11px] text-text-primary px-3 py-2 rounded-sm outline-none focus:border-status-info"
                />
              </div>
              <div>
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Format</label>
                <div className="flex gap-2">
                  {(['PDF', 'CSV'] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setDeliveryFormat(f)}
                      className="text-[10px] font-semibold px-4 py-1.5 rounded-sm transition-all"
                      style={{
                        background: deliveryFormat === f ? 'color-mix(in srgb, var(--color-status-info) 9%, transparent)' : 'transparent',
                        color: deliveryFormat === f ? 'var(--color-status-info)' : 'rgba(255,255,255,0.4)',
                        border: `1px solid ${deliveryFormat === f ? 'color-mix(in srgb, var(--color-status-info) 25%, transparent)' : 'rgba(255,255,255,0.08)'}`,
                      }}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Include Charts</label>
                <button
                  onClick={() => setIncludeCharts(!includeCharts)}
                  className="flex items-center gap-2 text-[10px] font-semibold"
                >
                  <div
                    className="w-8 h-4 rounded-full relative transition-all"
                    style={{ background: includeCharts ? 'var(--color-status-info)' : 'rgba(255,255,255,0.1)' }}
                  >
                    <div
                      className="w-3 h-3 bg-white rounded-full absolute top-0.5 transition-all"
                      style={{ left: includeCharts ? '17px' : '2px' }}
                    />
                  </div>
                  <span style={{ color: includeCharts ? 'var(--color-status-info)' : 'rgba(255,255,255,0.4)' }}>
                    {includeCharts ? 'Enabled' : 'Disabled'}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </Panel>

      {/* MODULE 5 — Report Archive */}
      <Panel>
        <SectionHeader number="5" title="Report Archive" sub="30 reports stored · 8.4 MB total" />
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Month', 'Reports', 'Download'].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ARCHIVE.map((a, i) => (
                <tr key={i} className="border-b border-border-subtle hover:bg-[rgba(255,255,255,0.02)]">
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.7)]">{a.month}</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{a.count} reports</td>
                  <td className="py-2 pr-4">
                    <button
                      className="text-[10px] font-semibold px-2 py-0.5 rounded-sm"
                      style={{ background: 'color-mix(in srgb, var(--color-status-info) 6%, transparent)', color: 'var(--color-status-info)', border: '1px solid color-mix(in srgb, var(--color-status-info) 14%, transparent)' }}
                    >
                      Download All
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
