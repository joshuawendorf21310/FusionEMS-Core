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

const SCENARIOS = [
  { label: 'Small', calls: 100, highlight: false },
  { label: 'Medium', calls: 200, highlight: true },
  { label: 'Large', calls: 400, highlight: false },
  { label: 'Enterprise', calls: 800, highlight: false },
];

function computeModel(
  calls: number,
  medicare: number,
  medicaid: number,
  commercial: number,
  selfPayRate: number,
  medicareP: number,
  medicaidP: number,
  commercialP: number,
  selfPayP: number,
  billingPct: number,
  collectionRate: number,
) {
  const blended =
    (medicare * medicareP + medicaid * medicaidP + commercial * commercialP + selfPayRate * selfPayP) / 100;
  const gross = blended * calls * (collectionRate / 100);
  const currentFee = gross * (billingPct / 100);
  const currentNet = gross - currentFee;

  const platformBase = 1200;
  const perCall = 6;
  const platformCost = platformBase + calls * perCall;
  const fusionNet = gross - platformCost;
  const saving = fusionNet - currentNet;

  const platformPctOfRevenue = gross > 0 ? (platformCost / gross) * 100 : 0;

  return {
    blended,
    gross,
    currentFee,
    currentNet,
    platformCost,
    fusionNet,
    saving,
    platformPctOfRevenue,
  };
}

export default function PricingSimulatorPage() {
  const [calls, setCalls] = useState(200);
  const [medicare, setMedicare] = useState(650);
  const [medicaid, setMedicaid] = useState(280);
  const [commercial, setCommercial] = useState(820);
  const [selfPayRate, setSelfPayRate] = useState(120);
  const [medicareP, setMedicareP] = useState(40);
  const [medicaidP, setMedicaidP] = useState(30);
  const [commercialP, setCommercialP] = useState(20);
  const [selfPayP, setSelfPayP] = useState(10);
  const [billingPct, setBillingPct] = useState(8);
  const [collectionRate, setCollectionRate] = useState(72);
  const [proposalEmail, setProposalEmail] = useState('');

  const model = computeModel(
    calls, medicare, medicaid, commercial, selfPayRate,
    medicareP, medicaidP, commercialP, selfPayP,
    billingPct, collectionRate,
  );

  const platformBase = 1200;
  const perCall = 6;
  const platformCost = platformBase + calls * perCall;

  const fmt = (n: number) =>
    n < 0
      ? `-$${Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: 0 })}`
      : `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

  function scenarioModel(c: number) {
    return computeModel(c, medicare, medicaid, commercial, selfPayRate, medicareP, medicaidP, commercialP, selfPayP, billingPct, collectionRate);
  }

  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-6 space-y-6">
      {/* Page Header */}
      <div className="border-b border-border-subtle pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold tracking-widest font-mono mb-1" style={{ color: 'rgba(255,152,0,0.6)' }}>
              MODULE 8 · ROI &amp; SALES
            </p>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--q-yellow)' }}>Pricing Simulator</h1>
            <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Model different pricing scenarios · compare vs competitor billing models</p>
          </div>
          <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-status-warning transition-colors font-mono">
            ← Back to Founder OS
          </Link>
        </div>
      </div>

      {/* MODULE 1 — Agency Input Parameters */}
      <Panel>
        <SectionHeader number="1" title="Agency Input Parameters" sub="Adjust to model any agency" />
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Monthly Call Volume: <span className="text-status-warning font-bold">{calls}</span></label>
              <input
                type="range" min={50} max={1000} step={10} value={calls}
                onChange={(e) => setCalls(Number(e.target.value))}
                className="w-full accent-[var(--color-status-warning)]"
              />
              <div className="flex justify-between text-[9px] text-[rgba(255,255,255,0.25)] mt-0.5">
                <span>50</span><span>1,000</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Avg Medicare Rate ($)', val: medicare, set: setMedicare },
                { label: 'Avg Medicaid Rate ($)', val: medicaid, set: setMedicaid },
                { label: 'Avg Commercial Rate ($)', val: commercial, set: setCommercial },
                { label: 'Billing % Fee', val: billingPct, set: setBillingPct },
              ].map(({ label, val, set }) => (
                <div key={label}>
                  <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">{label}</label>
                  <input
                    type="number" value={val}
                    onChange={(e) => set(Number(e.target.value))}
                    className="w-full bg-bg-input border border-border-DEFAULT text-[11px] text-text-primary px-3 py-2 rounded-sm outline-none focus:border-status-warning"
                  />
                </div>
              ))}
            </div>
            <div>
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Current Collection Rate (%): <span className="text-status-warning font-bold">{collectionRate}%</span></label>
              <input
                type="range" min={40} max={100} step={1} value={collectionRate}
                onChange={(e) => setCollectionRate(Number(e.target.value))}
                className="w-full accent-[var(--color-status-warning)]"
              />
            </div>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-3">Payer Mix (%)</p>
            <div className="space-y-3">
              {[
                { label: 'Medicare %', val: medicareP, set: setMedicareP, color: 'var(--color-status-info)' },
                { label: 'Medicaid %', val: medicaidP, set: setMedicaidP, color: 'var(--color-system-compliance)' },
                { label: 'Commercial %', val: commercialP, set: setCommercialP, color: 'var(--q-green)' },
                { label: 'Self-Pay %', val: selfPayP, set: setSelfPayP, color: 'var(--q-yellow)' },
              ].map(({ label, val, set, color }) => (
                <div key={label}>
                  <div className="flex justify-between mb-1">
                    <span className="text-[10px] text-[rgba(255,255,255,0.4)]">{label}</span>
                    <span className="text-[10px] font-bold" style={{ color }}>{val}%</span>
                  </div>
                  <input
                    type="range" min={0} max={100} step={5} value={val}
                    onChange={(e) => set(Number(e.target.value))}
                    className="w-full"
                    style={{ accentColor: color }}
                  />
                </div>
              ))}
              <div className="flex justify-between text-[10px] pt-1 border-t border-border-subtle">
                <span className="text-[rgba(255,255,255,0.35)]">Total</span>
                <span className={`font-bold ${medicareP + medicaidP + commercialP + selfPayP === 100 ? 'text-status-active' : 'text-red'}`}>
                  {medicareP + medicaidP + commercialP + selfPayP}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </Panel>

      {/* MODULE 2 — FusionEMS Quantum Pricing */}
      <Panel>
        <SectionHeader number="2" title="FusionEMS Quantum Pricing" sub="Calculated from inputs" />
        <div className="grid grid-cols-4 gap-3">
          <StatCard label="Base Platform" value="$1,200/mo" color="var(--color-status-warning)" />
          <StatCard label="Per-Transport" value="$6/call" color="var(--color-status-warning)" />
          <StatCard label={`Total Platform Cost (${calls} calls)`} value={fmt(platformCost) + '/mo'} color="var(--color-text-primary)" />
          <StatCard
            label="Platform as % of Revenue"
            value={model.gross > 0 ? `${model.platformPctOfRevenue.toFixed(1)}%` : '—'}
            color={model.platformPctOfRevenue < 8 ? 'var(--color-status-active)' : 'var(--color-brand-red)'}
            sub={model.platformPctOfRevenue < 8 ? 'Better than 8% billing' : 'Higher than 8% billing'}
          />
        </div>
        <div className="mt-3 text-[11px] text-[rgba(255,255,255,0.4)] font-mono">
          $1,200 + ({calls} × $6) = {fmt(platformCost)}/mo
        </div>
      </Panel>

      {/* MODULE 3 — Revenue Comparison */}
      <Panel>
        <SectionHeader number="3" title="Revenue Comparison" sub="Current vs FusionEMS Quantum" />
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-bg-input border border-red-ghost rounded-sm">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[rgba(229,57,53,0.7)] mb-3">Current Model ({billingPct}% billing)</p>
            <div className="space-y-2">
              {[
                { label: 'Gross Revenue', val: fmt(model.gross), color: 'rgba(255,255,255,0.7)' },
                { label: `Billing Co. Fee (${billingPct}%)`, val: `-${fmt(model.currentFee)}`, color: 'var(--q-red)' },
                { label: 'Net to Agency', val: fmt(model.currentNet), color: 'var(--color-text-primary)' },
              ].map(({ label, val, color }) => (
                <div key={label} className="flex justify-between py-1.5 border-b border-border-subtle last:border-b-2 last:border-[rgba(255,255,255,0.12)]">
                  <span className="text-[11px] text-[rgba(255,255,255,0.4)]">{label}</span>
                  <span className="text-[11px] font-bold font-mono" style={{ color }}>{val}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="p-4 bg-bg-input border border-[rgba(76,175,80,0.2)] rounded-sm">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[rgba(76,175,80,0.7)] mb-3">FusionEMS Quantum</p>
            <div className="space-y-2">
              {[
                { label: 'Gross Revenue', val: fmt(model.gross), color: 'rgba(255,255,255,0.7)' },
                { label: `Platform Cost`, val: `-${fmt(platformCost)}`, color: 'var(--q-yellow)' },
                { label: 'Net to Agency', val: fmt(model.fusionNet), color: 'var(--q-green)' },
              ].map(({ label, val, color }) => (
                <div key={label} className="flex justify-between py-1.5 border-b border-border-subtle last:border-b-2 last:border-[rgba(76,175,80,0.2)]">
                  <span className="text-[11px] text-[rgba(255,255,255,0.4)]">{label}</span>
                  <span className="text-[11px] font-bold font-mono" style={{ color }}>{val}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-2 border-t border-[rgba(76,175,80,0.2)]">
              <div className="flex justify-between items-center">
                <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.6)]">Monthly Saving</span>
                <span className="text-[15px] font-bold" style={{ color: model.saving >= 0 ? 'var(--color-status-active)' : 'var(--color-brand-red)' }}>
                  {model.saving >= 0 ? '+' : ''}{fmt(model.saving)}/mo
                </span>
              </div>
            </div>
          </div>
        </div>
      </Panel>

      {/* MODULE 4 — ROI over Time */}
      <Panel>
        <SectionHeader number="4" title="ROI over Time" sub="Cumulative savings" />
        <div className="grid grid-cols-3 gap-3">
          <StatCard
            label="1-Year Savings"
            value={fmt(model.saving * 12)}
            sub="Annual cumulative"
            color="var(--color-status-active)"
          />
          <StatCard
            label="5-Year Savings"
            value={fmt(model.saving * 60)}
            sub="5-year cumulative"
            color="var(--color-status-active)"
          />
          <StatCard
            label="10-Year Savings"
            value={fmt(model.saving * 120)}
            sub="10-year cumulative"
            color="var(--color-status-active)"
          />
        </div>
      </Panel>

      {/* MODULE 5 — Scenario Comparison */}
      <Panel>
        <SectionHeader number="5" title="Scenario Comparison" sub="Pre-built agency sizes" />
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Size', 'Calls/mo', 'Platform Cost', 'Gross Rev', 'Net (Current)', 'Net (Fusion)', 'Monthly Saving'].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {SCENARIOS.map((s) => {
                const m = scenarioModel(s.calls);
                const pc = platformBase + s.calls * perCall;
                return (
                  <tr
                    key={s.label}
                    className="border-b border-border-subtle hover:bg-[rgba(255,255,255,0.02)]"
                    style={{ background: s.highlight ? 'rgba(255,152,0,0.04)' : undefined }}
                  >
                    <td className="py-2 pr-4">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-[rgba(255,255,255,0.8)]">{s.label}</span>
                        {s.highlight && <Badge label="Most Common" status="warn" />}
                      </div>
                    </td>
                    <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{s.calls}</td>
                    <td className="py-2 pr-4 font-mono text-status-warning">{fmt(pc)}/mo</td>
                    <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.6)]">{fmt(m.gross)}/mo</td>
                    <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.5)]">{fmt(m.currentNet)}/mo</td>
                    <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.7)]">{fmt(m.fusionNet)}/mo</td>
                    <td className="py-2 pr-4 font-mono font-bold" style={{ color: m.saving >= 0 ? 'var(--color-status-active)' : 'var(--color-brand-red)' }}>
                      {m.saving >= 0 ? '+' : ''}{fmt(m.saving)}/mo
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* MODULE 6 — Export Proposal */}
      <Panel>
        <SectionHeader number="6" title="Export Proposal" sub="Generate and send ROI proposal" />
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Agency Email Address</label>
            <input
              type="email"
              value={proposalEmail}
              onChange={(e) => setProposalEmail(e.target.value)}
              placeholder="agency@example.com"
              className="w-full bg-bg-input border border-border-DEFAULT text-[11px] text-text-primary px-3 py-2 rounded-sm outline-none focus:border-status-warning"
            />
          </div>
          <button
            className="text-[11px] font-bold px-5 py-2 rounded-sm transition-all hover:opacity-90"
            style={{ background: 'var(--color-status-warning)', color: '#000' }}
          >
            Generate PDF Proposal
          </button>
          <button
            disabled={!proposalEmail}
            className="text-[11px] font-bold px-5 py-2 rounded-sm transition-all disabled:opacity-30"
            style={{ background: 'color-mix(in srgb, var(--color-status-info) 9%, transparent)', color: 'var(--color-status-info)', border: '1px solid color-mix(in srgb, var(--color-status-info) 19%, transparent)' }}
          >
            Send to Agency
          </button>
        </div>
      </Panel>
    </div>
  );
}
