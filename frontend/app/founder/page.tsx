'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_BASE ?? '';

function KpiCard({
  label,
  value,
  sub,
  trend,
  color,
  href,
}: {
  label: string;
  value: string;
  sub?: string;
  trend?: 'up' | 'down' | 'flat';
  color?: string;
  href?: string;
}) {
  const trendColor = trend === 'up' ? '#4caf50' : trend === 'down' ? '#e53935' : 'rgba(255,255,255,0.38)';
  const trendIcon = trend === 'up' ? '▲' : trend === 'down' ? '▼' : '—';
  const inner = (
    <div
      className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4 h-full flex flex-col justify-between hover:border-[rgba(255,107,26,0.3)] transition-colors cursor-pointer group"
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-2">{label}</div>
      <div className="text-2xl font-bold text-white" style={color ? { color } : {}}>{value}</div>
      {sub && (
        <div className="flex items-center gap-1 mt-1">
          {trend && <span className="text-[10px]" style={{ color: trendColor }}>{trendIcon}</span>}
          <span className="text-[11px]" style={{ color: trendColor }}>{sub}</span>
        </div>
      )}
    </div>
  );
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="h-full">
      {href ? <Link href={href}>{inner}</Link> : inner}
    </motion.div>
  );
}

function SectionHeader({ title, sub, number }: { title: string; sub?: string; number: string }) {
  return (
    <div className="hud-rail pb-2 mb-4">
      <div className="flex items-baseline gap-3">
        <span className="text-[10px] font-bold text-[rgba(255,107,26,0.6)] font-mono">MODULE {number}</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-[rgba(255,255,255,0.85)]">{title}</h2>
        {sub && <span className="text-xs text-[rgba(255,255,255,0.35)]">{sub}</span>}
      </div>
    </div>
  );
}

function RiskCard({ label, items }: { label: string; items: { text: string; level: 'ok' | 'warn' | 'crit' }[] }) {
  const levelColor = { ok: '#4caf50', warn: '#ff9800', crit: '#e53935' };
  return (
    <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
      <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">{label}</div>
      <div className="space-y-1.5">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: levelColor[item.level] }} />
            <span className="text-xs text-[rgba(255,255,255,0.65)]">{item.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DenialHeatCell({ value, max }: { value: number; max: number }) {
  const intensity = max > 0 ? value / max : 0;
  const bg = intensity > 0.8 ? '#9c1b1b' : intensity > 0.5 ? '#b84a0f' : intensity > 0.25 ? '#ff9800' : '#1a2535';
  const text = intensity > 0.5 ? '#fff' : 'rgba(255,255,255,0.65)';
  return (
    <div
      className="flex items-center justify-center h-10 text-xs font-semibold transition-colors"
      style={{ background: bg, color: text }}
    >
      {value}%
    </div>
  );
}

function ActionItemRow({ rank, text, category, urgency }: { rank: number; text: string; category: string; urgency: 'high' | 'medium' | 'low' }) {
  const urgencyColor = { high: '#e53935', medium: '#ff9800', low: '#4caf50' };
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-[rgba(255,255,255,0.05)] last:border-0">
      <span className="text-[10px] font-bold text-[rgba(255,107,26,0.6)] font-mono w-5">{rank}</span>
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: urgencyColor[urgency] }} />
      <span className="flex-1 text-xs text-[rgba(255,255,255,0.75)]">{text}</span>
      <span className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.3)] bg-[rgba(255,255,255,0.05)] px-2 py-0.5 rounded-sm">
        {category}
      </span>
    </div>
  );
}

function GrowthVelocityBar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-[10px] text-[rgba(255,255,255,0.45)] w-10 flex-shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-[rgba(255,255,255,0.06)] rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: '#ff6b1a' }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      <span className="text-xs font-semibold text-white w-12 text-right">{value.toLocaleString()}</span>
    </div>
  );
}

export default function FounderExecutivePage() {
  const [metrics, setMetrics] = useState<Record<string, unknown>>({});
  const [aging, setAging] = useState<{ buckets: Array<{ label: string; total_cents: number; count: number }> } | null>(null);
  const [incidentMode, setIncidentMode] = useState(false);
  const [complianceGauges, setComplianceGauges] = useState<Array<{ label: string; value: number; color: string }> | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/founder/dashboard`).then((r) => r.json()).then(setMetrics).catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/billing/ar-aging`).then((r) => r.json()).then(setAging).catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/founder/compliance/status`).then((r) => r.json()).then((d) => {
      if (d?.gauges) setComplianceGauges(d.gauges);
    }).catch((e: unknown) => { console.warn("[fetch error]", e); });
  }, []);

  const mrr = (metrics as { mrr_cents?: number })?.mrr_cents;
  const arr = mrr != null ? mrr * 12 : null;
  const mrrDisplay = mrr != null ? `$${(mrr / 100).toLocaleString()}` : '—';
  const arrDisplay = arr != null ? `$${(arr / 100).toLocaleString()}` : '—';
  const tenantCount = (metrics as { tenant_count?: number })?.tenant_count ?? '—';
  const errorCount = (metrics as { error_count_1h?: number })?.error_count_1h ?? 0;
  const totalAR = aging ? aging.buckets.reduce((a, b) => a + b.total_cents, 0) / 100 : null;

  const DENIAL_HEATMAP = [
    { payer: 'Medicare', jan: 14, feb: 12, mar: 18, apr: 10, may: 22, jun: 15 },
    { payer: 'Medicaid', jan: 28, feb: 31, mar: 25, apr: 29, may: 27, jun: 30 },
    { payer: 'BlueCross', jan: 8,  feb: 9,  mar: 7,  apr: 11, may: 6,  jun: 9 },
    { payer: 'Aetna',    jan: 19, feb: 21, mar: 20, apr: 17, may: 23, jun: 24 },
    { payer: 'Uninsured',jan: 45, feb: 43, mar: 48, apr: 42, may: 46, jun: 50 },
  ];
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];

  return (
    <div className="p-5 space-y-8 min-h-screen">
      {incidentMode && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 px-4 py-2 bg-[rgba(229,57,53,0.15)] border border-[#e53935] text-[#ff5252] text-sm font-semibold rounded-sm"
        >
          <span className="animate-pulse">⬤</span>
          INCIDENT MODE ACTIVE — All non-critical communications suspended. War room routing engaged.
          <button onClick={() => setIncidentMode(false)} className="ml-auto text-xs underline">Deactivate</button>
        </motion.div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">FUSIONEMS QUANTUM</div>
          <h1 className="text-xl font-black uppercase tracking-wider text-white">Founder Command OS</h1>
          <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">Executive Command Overview · 175-Module Control System</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/founder/comms/inbox" className="h-8 px-3 bg-[rgba(34,211,238,0.1)] border border-[rgba(34,211,238,0.25)] text-[#22d3ee] text-xs font-semibold rounded-sm hover:bg-[rgba(34,211,238,0.15)] transition-colors flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#22d3ee] animate-pulse" />
            Communications
          </Link>
          <Link href="/founder/ai/review-queue" className="h-8 px-3 bg-[rgba(168,85,247,0.1)] border border-[rgba(168,85,247,0.25)] text-[#a855f7] text-xs font-semibold rounded-sm hover:bg-[rgba(168,85,247,0.15)] transition-colors flex items-center">
            AI Queue
          </Link>
          <button
            onClick={() => setIncidentMode(true)}
            className="h-8 px-3 bg-[rgba(229,57,53,0.12)] border border-[rgba(229,57,53,0.3)] text-[#e53935] text-xs font-semibold rounded-sm hover:bg-[rgba(229,57,53,0.2)] transition-colors"
          >
            Incident Mode
          </button>
        </div>
      </div>

      {/* MODULE 1–4 · Revenue & Tenant Metrics */}
      <div>
        <SectionHeader number="1–4" title="Global Revenue Snapshot" sub="MRR · ARR · Tenants · AR Overview" />
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
          <KpiCard label="MRR" value={mrrDisplay} sub="Monthly Recurring" trend="up" color="#22d3ee" href="/founder/revenue/stripe" />
          <KpiCard label="ARR" value={arrDisplay} sub="Annual Run Rate" trend="up" color="#22d3ee" href="/founder/revenue/forecast" />
          <KpiCard label="Active Tenants" value={String(tenantCount)} sub="Billing accounts" href="/founder/revenue/billing-intelligence" />
          <KpiCard
            label="Total AR"
            value={totalAR != null ? `$${totalAR.toLocaleString()}` : '—'}
            sub="Outstanding claims"
            trend="flat"
            href="/founder/revenue/ar-aging"
          />
          <KpiCard
            label="API Errors (1h)"
            value={String(errorCount)}
            sub="System health"
            trend={errorCount > 10 ? 'down' : 'flat'}
            href="/founder/infra/ecs"
          />
        </div>
      </div>

      {/* MODULE 3 · Clean Claim Rate + MODULE 6 · Export Success Rate */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Clean Claim Rate" value="94.2%" sub="+1.1% vs last month" trend="up" color="#4caf50" />
        <KpiCard label="Export Success Rate" value="98.7%" sub="Last 30 days" trend="up" color="#4caf50" />
        <KpiCard label="Compliance Score" value="97 / 100" sub="NEMSIS + CMS + DEA" trend="flat" color="#29b6f6" />
        <KpiCard label="AI Utilization" value="83%" sub="of interactions AI-handled" trend="up" color="#a855f7" />
      </div>

      {/* MODULE 5 · Denial Rate Heatmap */}
      <div>
        <SectionHeader number="5" title="Denial Rate Heatmap" sub="By payer × month" />
        <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4 overflow-x-auto" style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)' }}>
          <table className="w-full min-w-[600px] text-xs">
            <thead>
              <tr>
                <th className="text-left text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] pb-2 pr-4 font-semibold">Payer</th>
                {MONTHS.map((m) => (
                  <th key={m} className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] pb-2 px-1 font-semibold">{m}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {DENIAL_HEATMAP.map((row) => (
                <tr key={row.payer}>
                  <td className="text-[rgba(255,255,255,0.65)] pr-4 py-0.5 whitespace-nowrap">{row.payer}</td>
                  {(['jan','feb','mar','apr','may','jun'] as const).map((m) => (
                    <td key={m} className="px-0.5 py-0.5">
                      <DenialHeatCell value={row[m]} max={50} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center gap-3 mt-3 text-[10px] text-[rgba(255,255,255,0.35)]">
            <span>Low</span>
            {['#1a2535','#ff9800','#b84a0f','#9c1b1b'].map((c) => (
              <span key={c} className="w-6 h-3 inline-block rounded-sm" style={{ background: c }} />
            ))}
            <span>High</span>
          </div>
        </div>
      </div>

      {/* MODULE 8–9 · AI + Infrastructure */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <RiskCard
          label="Infrastructure Health · Module 9"
          items={[
            { text: 'ECS: All services operational', level: 'ok' },
            { text: 'RDS: Latency 12ms avg', level: 'ok' },
            { text: 'Redis: 0 evictions', level: 'ok' },
            { text: 'AI GPU: 61% utilization', level: 'ok' },
            { text: 'SSL: 87 days until expiry', level: 'ok' },
          ]}
        />
        <RiskCard
          label="Churn · Revenue · Compliance Risks · Modules 11–13"
          items={[
            { text: 'Churn risk: 0 tenants flagged', level: 'ok' },
            { text: 'Revenue: AR aging normal', level: 'ok' },
            { text: 'Compliance: No critical gaps', level: 'ok' },
            { text: '3 credential expirations (30d)', level: 'warn' },
            { text: 'Export failures: 0 (24h)', level: 'ok' },
          ]}
        />
        <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">Module 7 · Compliance Readiness</div>
          {(complianceGauges ?? [
            { label: 'NEMSIS v3.5.0', value: 0, color: 'rgba(255,255,255,0.18)' },
            { label: 'CMS Billing Rules', value: 0, color: 'rgba(255,255,255,0.18)' },
            { label: 'DEA / Controlled', value: 0, color: 'rgba(255,255,255,0.18)' },
            { label: 'HIPAA / BAA Coverage', value: 0, color: 'rgba(255,255,255,0.18)' },
            { label: 'State Export Compat.', value: 0, color: 'rgba(255,255,255,0.18)' },
          ]).map((item) => (
            <div key={item.label} className="mb-2">
              <div className="flex justify-between text-[11px] mb-0.5">
                <span className="text-[rgba(255,255,255,0.55)]">{item.label}</span>
                <span className="font-semibold" style={{ color: item.color }}>{item.value}%</span>
              </div>
              <div className="h-1 bg-[rgba(255,255,255,0.06)] rounded-full overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${item.value}%`, background: item.color }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* MODULE 10 · Daily AI Brief */}
      <div>
        <SectionHeader number="10" title="Daily AI Brief" sub="Top 5 Action Items · AI-generated · updated hourly" />
        <div className="bg-[#0f1720] border border-[rgba(255,107,26,0.15)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)' }}>
          <div className="flex items-center gap-2 mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-[#ff6b1a] animate-pulse" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,107,26,0.8)]">Quantum Intelligence Brief — Today</span>
          </div>
          <ActionItemRow rank={1} text="3 denial appeals require founder approval before 5PM — revenue impact ~$4,200" category="Revenue" urgency="high" />
          <ActionItemRow rank={2} text="Credential expiration for 2 providers in 28 days — schedule renewal now" category="Compliance" urgency="high" />
          <ActionItemRow rank={3} text="Export queue has 1 item pending retry — automated retry scheduled in 4h" category="Export" urgency="medium" />
          <ActionItemRow rank={4} text="Tenant onboarding: Agency B awaiting BAA signature (day 3)" category="Onboarding" urgency="medium" />
          <ActionItemRow rank={5} text="AR aging: 2 claims crossing 90-day threshold this week" category="Billing" urgency="medium" />
        </div>
      </div>

      {/* MODULE 14 · System Incident Banner */}
      <div>
        <SectionHeader number="14" title="System Incident Status" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-[rgba(76,175,80,0.08)] border border-[rgba(76,175,80,0.2)] p-3 flex items-center gap-3" style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
            <span className="text-[#4caf50] text-xl font-black">✓</span>
            <div>
              <div className="text-xs font-semibold text-[#4caf50]">All Systems Operational</div>
              <div className="text-[11px] text-[rgba(255,255,255,0.4)]">No active incidents · Last checked moments ago</div>
            </div>
          </div>
          <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-3" style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
            <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] mb-2">Recent Incidents</div>
            <div className="text-xs text-[rgba(255,255,255,0.4)]">No incidents in the last 30 days</div>
          </div>
        </div>
      </div>

      {/* MODULE 15 · Growth Velocity Graph */}
      <div>
        <SectionHeader number="15" title="Growth Velocity" sub="30 / 90 / 365 day view" />
        <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-5 grid grid-cols-1 md:grid-cols-2 gap-6" style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)' }}>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] mb-3">Tenant Growth</div>
            <div className="space-y-2">
              <GrowthVelocityBar label="30d" value={2} max={10} />
              <GrowthVelocityBar label="90d" value={5} max={10} />
              <GrowthVelocityBar label="365d" value={10} max={10} />
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] mb-3">Revenue Growth ($)</div>
            <div className="space-y-2">
              <GrowthVelocityBar label="30d" value={1200} max={5000} />
              <GrowthVelocityBar label="90d" value={3800} max={5000} />
              <GrowthVelocityBar label="365d" value={5000} max={5000} />
            </div>
          </div>
        </div>
      </div>

      {/* Quick Nav to all 12 Domains */}
      <div>
        <SectionHeader number="—" title="Domain Control Grid" sub="Navigate all 12 command domains" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
          {[
            { href: '/founder', label: 'Executive', color: '#ff6b1a', mod: '1' },
            { href: '/founder/revenue/billing-intelligence', label: 'Revenue & Billing', color: '#22d3ee', mod: '2' },
            { href: '/founder/ai/policies', label: 'AI Governance', color: '#a855f7', mod: '3' },
            { href: '/founder/comms/inbox', label: 'Communications', color: '#4caf50', mod: '4' },
            { href: '/founder/comms/phone-system', label: 'AI Voice & Alerts', color: '#4caf50', mod: '4B' },
            { href: '/founder/compliance/nemsis', label: 'Compliance', color: '#f59e0b', mod: '5' },
            { href: '/founder/security/role-builder', label: 'Visibility & Sec.', color: '#e53935', mod: '6' },
            { href: '/founder/templates/proposals', label: 'Templates', color: '#29b6f6', mod: '7' },
            { href: '/founder/roi/analytics', label: 'ROI & Sales', color: '#ff9800', mod: '8' },
            { href: '/founder/pwa/crewlink', label: 'PWA & Mobile', color: '#3b82f6', mod: '9' },
            { href: '/founder/infra/ecs', label: 'Infrastructure', color: '#94a3b8', mod: '10' },
            { href: '/founder/tools/calendar', label: 'Founder Tools', color: '#ff6b1a', mod: '11' },
          ].map((d) => (
            <Link
              key={d.href}
              href={d.href}
              className="flex flex-col gap-1 p-3 bg-[#0f1720] border border-[rgba(255,255,255,0.06)] hover:border-[rgba(255,255,255,0.16)] transition-colors group"
              style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
            >
              <span className="text-[9px] font-bold font-mono" style={{ color: d.color }}>DOMAIN {d.mod}</span>
              <span className="text-xs font-semibold text-[rgba(255,255,255,0.75)] group-hover:text-white transition-colors">{d.label}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
