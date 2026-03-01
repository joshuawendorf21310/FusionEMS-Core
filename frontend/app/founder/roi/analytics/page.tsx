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
      style={{
        borderColor: `color-mix(in srgb, ${c[status]} 25%, transparent)`,
        color: c[status],
        background: `color-mix(in srgb, ${c[status]} 7%, transparent)`,
      }}
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

const AGENCIES = [
  { name: 'Agency A', plan: 'Professional', mrr: 1440, transports: 200, rpc: 7.20, since: 'Oct 2023' },
  { name: 'Agency B', plan: 'Professional', mrr: 1440, transports: 200, rpc: 7.20, since: 'Nov 2023' },
  { name: 'Agency C', plan: 'Starter', mrr: 720, transports: 100, rpc: 7.20, since: 'Dec 2023' },
  { name: 'Agency D', plan: 'Starter', mrr: 720, transports: 80, rpc: 9.00, since: 'Jan 2024' },
];

const PAYER_MIX = [
  { label: 'Medicare', pct: 40, color: 'var(--color-status-info)' },
  { label: 'Medicaid', pct: 30, color: 'var(--color-system-compliance)' },
  { label: 'Commercial', pct: 20, color: 'var(--q-green)' },
  { label: 'Self-Pay', pct: 10, color: 'var(--q-yellow)' },
];

const GROWTH = [
  { month: 'Aug', mrr: 0 },
  { month: 'Sep', mrr: 1440 },
  { month: 'Oct', mrr: 2880 },
  { month: 'Nov', mrr: 3600 },
  { month: 'Dec', mrr: 4320 },
  { month: 'Jan', mrr: 4320 },
];

const REGIONAL = [
  { state: 'Texas', agencies: 2, potential: 40 },
  { state: 'California', agencies: 1, potential: 85 },
  { state: 'Florida', agencies: 1, potential: 60 },
  { state: 'Wisconsin', agencies: 0, potential: 20 },
];

const CHURN_RISK = [
  { agency: 'Agency A', score: 94, risk: 'Low Risk', riskKey: 'ok' as const },
  { agency: 'Agency B', score: 88, risk: 'Low Risk', riskKey: 'ok' as const },
  { agency: 'Agency C', score: 72, risk: 'Medium Risk', riskKey: 'warn' as const },
  { agency: 'Agency D', score: 61, risk: 'Medium Risk', riskKey: 'warn' as const },
];

export default function ROIAnalyticsPage() {
  const [calcVolume, setCalcVolume] = useState(200);
  const [calcRate, setCalcRate] = useState(650);

  const grossRev = calcVolume * calcRate * 0.72;
  const fusionFee = 1200 + calcVolume * 6;
  const competitorFee = grossRev * 0.08;
  const fusionSaving = competitorFee - fusionFee;
  const fiveYrSaving = fusionSaving * 60;

  const fmt = (n: number) =>
    n < 0
      ? `-$${Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: 0 })}`
      : `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-6 space-y-6">
      {/* Page Header */}
      <div className="border-b border-border-subtle pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold tracking-widest font-mono mb-1" style={{ color: 'rgba(255,152,0,0.6)' }}>
              MODULE 8 · ROI &amp; SALES
            </p>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--q-yellow)' }}>ROI Calculator Analytics</h1>
            <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Conversion funnel · proposal acceptance rate · regional revenue heatmap</p>
          </div>
          <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-status-warning transition-colors font-mono">
            ← Back to Founder OS
          </Link>
        </div>
      </div>

      {/* MODULE 1 — Revenue KPIs */}
      <div className="grid grid-cols-5 gap-3">
        <StatCard label="MRR" value="$4,320" color="var(--color-status-info)" />
        <StatCard label="ARR" value="$51,840" color="var(--color-status-info)" />
        <StatCard label="Active Agencies" value={4} color="var(--color-text-primary)" />
        <StatCard label="Avg Rev/Agency" value="$1,080/mo" color="var(--color-text-primary)" />
        <StatCard label="MRR Growth (30d)" value="+$1,440" color="var(--color-status-active)" sub="vs prior 30d" />
      </div>

      {/* MODULE 2 — Agency Revenue Breakdown */}
      <Panel>
        <SectionHeader number="2" title="Agency Revenue Breakdown" sub="4 active accounts" />
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Agency', 'Plan', 'MRR', 'Transports/mo', 'Revenue Per Call', 'Since'].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {AGENCIES.map((a, i) => (
                <tr key={i} className="border-b border-border-subtle hover:bg-[rgba(255,255,255,0.02)]">
                  <td className="py-2 pr-4 font-semibold text-[rgba(255,255,255,0.8)]">{a.name}</td>
                  <td className="py-2 pr-4"><Badge label={a.plan} status={a.plan === 'Professional' ? 'info' : 'ok'} /></td>
                  <td className="py-2 pr-4 font-mono font-bold" style={{ color: 'var(--color-system-billing)' }}>${a.mrr.toLocaleString()}/mo</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{a.transports}</td>
                  <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.6)]">${a.rpc.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.4)]">{a.since}</td>
                </tr>
              ))}
              <tr className="border-t border-border-DEFAULT">
                <td className="py-2 pr-4 font-bold text-[rgba(255,255,255,0.6)]" colSpan={2}>Total</td>
                <td className="py-2 pr-4 font-mono font-bold" style={{ color: 'var(--color-system-billing)' }}>$4,320/mo</td>
                <td className="py-2 pr-4 font-bold text-[rgba(255,255,255,0.6)]">580</td>
                <td colSpan={2} />
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>

      {/* MODULE 3 — Payer Mix */}
      <Panel>
        <SectionHeader number="3" title="Payer Mix" sub="Revenue distribution by payer class" />
        <div className="space-y-4">
          {PAYER_MIX.map((p) => (
            <div key={p.label}>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ background: p.color }} />
                  <span className="text-[11px] text-[rgba(255,255,255,0.7)]">{p.label}</span>
                </div>
                <span className="text-[11px] font-bold" style={{ color: p.color }}>{p.pct}%</span>
              </div>
              <ProgressBar value={p.pct} max={100} color={p.color} />
            </div>
          ))}
        </div>
      </Panel>

      {/* MODULE 4 — ROI Calculator */}
      <Panel>
        <SectionHeader number="4" title="ROI Calculator" sub="Interactive live comparison" />
        <div className="grid grid-cols-2 gap-6 mb-4">
          <div className="space-y-3">
            <div>
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">
                Monthly Transport Volume: <span className="text-status-warning font-bold">{calcVolume}</span>
              </label>
              <input
                type="range" min={50} max={1000} step={10} value={calcVolume}
                onChange={(e) => setCalcVolume(Number(e.target.value))}
                className="w-full accent-[var(--color-status-warning)]"
              />
            </div>
            <div>
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">
                Avg Blended Rate ($): <span className="text-status-warning font-bold">${calcRate}</span>
              </label>
              <input
                type="range" min={200} max={1200} step={10} value={calcRate}
                onChange={(e) => setCalcRate(Number(e.target.value))}
                className="w-full accent-[var(--color-status-warning)]"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <StatCard label="Gross Revenue" value={`${fmt(grossRev)}/mo`} color="rgba(255,255,255,0.7)" />
            <StatCard label="FusionEMS Fee" value={`${fmt(fusionFee)}/mo`} color="var(--color-status-warning)" />
            <StatCard label="Competitor Fee (8%)" value={`${fmt(competitorFee)}/mo`} color="var(--color-brand-red)" />
            <StatCard label="FusionEMS Saving" value={`${fusionSaving >= 0 ? '+' : ''}${fmt(fusionSaving)}/mo`} color={fusionSaving >= 0 ? 'var(--color-status-active)' : 'var(--color-brand-red)'} />
          </div>
        </div>
        <div className="p-3 bg-bg-input border border-[rgba(76,175,80,0.15)] rounded-sm flex items-center justify-between">
          <span className="text-[11px] text-[rgba(255,255,255,0.5)]">5-Year Cumulative Saving</span>
          <span className="text-[15px] font-bold" style={{ color: fiveYrSaving >= 0 ? 'var(--color-status-active)' : 'var(--color-brand-red)' }}>
            {fiveYrSaving >= 0 ? '+' : ''}{fmt(fiveYrSaving)}
          </span>
        </div>
      </Panel>

      {/* MODULE 5 — Growth Trend */}
      <Panel>
        <SectionHeader number="5" title="Growth Trend" sub="6-month MRR progression" />
        <div className="space-y-3">
          {GROWTH.map((g) => (
            <div key={g.month}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] text-[rgba(255,255,255,0.5)] w-8 font-mono">{g.month}</span>
                <span className="text-[11px] font-bold flex-1 text-right" style={{ color: 'var(--color-system-billing)' }}>
                  {g.mrr === 0 ? '$0' : `$${g.mrr.toLocaleString()}`}
                </span>
              </div>
              <ProgressBar value={g.mrr} max={5000} color="var(--color-status-info)" />
            </div>
          ))}
          <div className="flex justify-between text-[9px] text-[rgba(255,255,255,0.2)] mt-1">
            <span>$0</span><span>$5,000</span>
          </div>
        </div>
      </Panel>

      {/* MODULE 6 — Regional Coverage */}
      <Panel>
        <SectionHeader number="6" title="Regional Coverage" sub="State-level market penetration" />
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border-subtle">
                {['State', 'Active Agencies', 'Market Potential', 'Penetration', ''].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {REGIONAL.map((r, i) => {
                const pct = r.potential > 0 ? (r.agencies / r.potential) * 100 : 0;
                return (
                  <tr key={i} className="border-b border-border-subtle hover:bg-[rgba(255,255,255,0.02)]">
                    <td className="py-2 pr-4 font-semibold text-[rgba(255,255,255,0.8)]">{r.state}</td>
                    <td className="py-2 pr-4">
                      <span className="font-bold text-system-billing">{r.agencies}</span>
                      {r.agencies === 0 && <Badge label="Target" status="warn" />}
                    </td>
                    <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{r.potential} agencies</td>
                    <td className="py-2 pr-4 w-40">
                      <div className="flex items-center gap-2">
                        <div className="flex-1">
                          <ProgressBar
                            value={r.agencies}
                            max={r.potential}
                            color={r.agencies === 0 ? 'var(--color-status-warning)' : 'var(--color-status-info)'}
                          />
                        </div>
                        <span className="text-[10px] font-mono w-10 text-right" style={{ color: r.agencies === 0 ? 'var(--color-status-warning)' : 'var(--color-status-info)' }}>
                          {pct.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-2 pr-4">
                      {r.agencies === 0 && (
                        <button
                          className="text-[10px] font-semibold px-2 py-0.5 rounded-sm"
                          style={{ background: 'color-mix(in srgb, var(--color-status-warning) 6%, transparent)', color: 'var(--q-yellow)', border: '1px solid color-mix(in srgb, var(--color-status-warning) 14%, transparent)' }}
                        >
                          Target
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* MODULE 7 — Churn Risk */}
      <Panel>
        <SectionHeader number="7" title="Churn Risk" sub="Agency health scores" />
        <div className="space-y-3">
          {CHURN_RISK.map((a, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-bg-input border border-border-subtle rounded-sm">
              <div className="flex items-center gap-4">
                <div className="text-center w-12">
                  <div
                    className="text-[18px] font-bold"
                    style={{ color: a.score >= 80 ? 'var(--color-status-active)' : a.score >= 60 ? 'var(--color-status-warning)' : 'var(--color-brand-red)' }}
                  >
                    {a.score}
                  </div>
                  <div className="text-[9px] text-[rgba(255,255,255,0.25)]">/ 100</div>
                </div>
                <div>
                  <div className="text-[12px] font-semibold text-[rgba(255,255,255,0.85)]">{a.agency}</div>
                  <div className="w-28 mt-1">
                    <ProgressBar
                      value={a.score}
                      max={100}
                      color={a.score >= 80 ? 'var(--color-status-active)' : 'var(--color-status-warning)'}
                    />
                  </div>
                </div>
              </div>
              <Badge label={a.risk} status={a.riskKey} />
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
