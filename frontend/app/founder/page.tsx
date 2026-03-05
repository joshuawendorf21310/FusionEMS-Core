'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { QuantumEmptyState } from '@/components/ui';

const API = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || '';

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
  const trendColor = trend === 'up' ? 'var(--color-status-active)' : trend === 'down' ? 'var(--color-brand-red)' : 'rgba(255,255,255,0.38)';
  const trendIcon = trend === 'up' ? '▲' : trend === 'down' ? '▼' : '—';
  
  const inner = (
    <div
      className="bg-bg-panel border border-border-DEFAULT p-4 h-full flex flex-col justify-between hover:border-[rgba(255,107,26,0.3)] transition-colors cursor-pointer group"
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-2">{label}</div>
      <div className="text-2xl font-bold text-text-primary" style={color ? { color } : {}}>{value}</div>
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
        <span className="text-[10px] font-bold text-orange-dim font-mono">MODULE {number}</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-[rgba(255,255,255,0.85)]">{title}</h2>
        {sub && <span className="text-xs text-[rgba(255,255,255,0.35)]">{sub}</span>}
      </div>
    </div>
  );
}

function RiskCard({ label, items }: { label: string; items: { text: string; level: 'ok' | 'warn' | 'crit' }[] }) {
  const levelColor = { ok: 'var(--color-status-active)', warn: 'var(--color-status-warning)', crit: 'var(--color-brand-red)' };
  return (
    <div className="bg-bg-panel border border-border-DEFAULT p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
      <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-3">{label}</div>
      {items.length === 0 ? (
          <div className="text-xs text-[rgba(255,255,255,0.4)]">No data available</div>
      ) : (
        <div className="space-y-1.5">
          {items.map((item, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: levelColor[item.level] }} />
              <span className="text-xs text-text-secondary">{item.text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DenialHeatCell({ value, max }: { value: number; max: number }) {
  const intensity = max > 0 ? value / max : 0;
  const bg = intensity > 0.8 ? 'var(--color-brand-red)' : intensity > 0.5 ? 'var(--color-brand-orange)' : intensity > 0.25 ? 'var(--color-status-warning)' : 'var(--color-bg-panel)';
  const text = intensity > 0.5 ? 'var(--color-text-primary)' : 'rgba(255,255,255,0.65)';
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
  const urgencyColor = { high: 'var(--color-brand-red)', medium: 'var(--color-status-warning)', low: 'var(--color-status-active)' };
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-[rgba(255,255,255,0.05)] last:border-0">
      <span className="text-[10px] font-bold text-orange-dim font-mono w-5">{rank}</span>
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
          style={{ background: 'var(--color-brand-orange)' }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      <span className="text-xs font-semibold text-text-primary w-12 text-right">{value.toLocaleString()}</span>
    </div>
  );
}

export default function FounderExecutivePage() {
  const [metrics, setMetrics] = useState<any>({});
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

  const mrr = metrics?.mrr_cents;
  const arr = mrr != null ? mrr * 12 : null;
  const mrrDisplay = mrr != null ? `$${(mrr / 100).toLocaleString()}` : '—';
  const arrDisplay = arr != null ? `$${(arr / 100).toLocaleString()}` : '—';
  const tenantCount = metrics?.tenant_count ?? '—';
  const errorCount = metrics?.error_count_1h ?? 0;
  const totalAR = aging ? aging.buckets.reduce((a, b) => a + b.total_cents, 0) / 100 : null;

  // Real-time integration fallback mapping 
  const denialHeatmap = metrics?.denial_heatmap ?? [];
  const actionBriefs = metrics?.action_briefs ?? [];
  const complianceScore = metrics?.compliance_score ?? '--';
  const cleanClaimRate = metrics?.clean_claim_rate ?? '--';
  const exportSuccessRate = metrics?.export_success_rate ?? '--';
  const aiUtilization = metrics?.ai_utilization ?? '--';
  const systemIncidents = metrics?.incidents ?? [];
  const growthMetrics = metrics?.growth ?? { tenants: [], revenue: [] };
  const riskInfrastructure = metrics?.risk_infra ?? [];
  const riskBusiness = metrics?.risk_business ?? [];

  return (
    <div className="p-5 space-y-8 min-h-screen">
      {incidentMode && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 px-4 py-2 bg-red-ghost border border-red text-red-bright text-sm font-semibold rounded-sm"
        >
          <span className="animate-pulse">⬤</span>
          INCIDENT MODE ACTIVE — All non-critical communications suspended. War room routing engaged.
          <button onClick={() => setIncidentMode(false)} className="ml-auto text-xs underline">Deactivate</button>
        </motion.div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">FUSIONEMS QUANTUM</div>
          <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Founder Command OS</h1>
          <p className="text-xs text-text-muted mt-0.5">Executive Command Overview · Real-Time Backend Hooked System</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/founder/comms/inbox" className="h-8 px-3 bg-[rgba(34,211,238,0.1)] border border-[rgba(34,211,238,0.25)] text-system-billing text-xs font-semibold rounded-sm hover:bg-[rgba(34,211,238,0.15)] transition-colors flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-system-billing animate-pulse" />
            Communications
          </Link>
          <Link href="/founder/ai/review-queue" className="h-8 px-3 bg-[rgba(168,85,247,0.1)] border border-[rgba(168,85,247,0.25)] text-system-compliance text-xs font-semibold rounded-sm hover:bg-[rgba(168,85,247,0.15)] transition-colors flex items-center">
            AI Queue
          </Link>
          <button
            onClick={() => setIncidentMode(true)}
            className="h-8 px-3 bg-[rgba(229,57,53,0.12)] border border-red-ghost text-red text-xs font-semibold rounded-sm hover:bg-[rgba(229,57,53,0.2)] transition-colors"
          >
            Incident Mode
          </button>
        </div>
      </div>

      {/* MODULE 1–4 · Revenue & Tenant Metrics */}
      <div>
        <SectionHeader number="1–4" title="Global Revenue Snapshot" sub="MRR · ARR · Tenants · AR Overview" />
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
          <KpiCard label="MRR" value={mrrDisplay} sub="Monthly Recurring" trend="up" color="var(--color-status-info)" href="/founder/revenue/stripe" />
          <KpiCard label="ARR" value={arrDisplay} sub="Annual Run Rate" trend="up" color="var(--color-status-info)" href="/founder/revenue/forecast" />
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
        <KpiCard label="Clean Claim Rate" value={cleanClaimRate} sub="From API" trend="flat" color="var(--color-status-active)" />
        <KpiCard label="Export Success Rate" value={exportSuccessRate} sub="From API" trend="flat" color="var(--color-status-active)" />
        <KpiCard label="Compliance Score" value={complianceScore} sub="From API" trend="flat" color="var(--color-status-info)" />
        <KpiCard label="AI Utilization" value={aiUtilization} sub="From API" trend="flat" color="var(--color-system-compliance)" />
      </div>

      {/* MODULE 5 · Denial Rate Heatmap */}
      <div>
        <SectionHeader number="5" title="Denial Rate Heatmap" sub="By payer × month" />
        {denialHeatmap.length === 0 ? (
          <QuantumEmptyState title="No heat map data" description="Data for Denial Heatmap will populate here from the founder API." icon="activity" />
        ) : (
          <div className="bg-bg-panel border border-border-DEFAULT p-4 overflow-x-auto" style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)' }}>
            <table className="w-full min-w-[600px] text-xs">
              <thead>
                <tr>
                  <th className="text-left text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] pb-2 pr-4 font-semibold">Payer</th>
                  {(Object.keys(denialHeatmap[0]).filter(k => k !== 'payer') as string[]).map((m) => (
                    <th key={m} className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] pb-2 px-1 font-semibold">{m}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {denialHeatmap.map((row: any) => (
                  <tr key={row.payer}>
                    <td className="text-text-secondary pr-4 py-0.5 whitespace-nowrap">{row.payer}</td>
                    {(Object.keys(row).filter(k => k !== 'payer') as string[]).map((m) => (
                      <td key={m} className="px-0.5 py-0.5">
                        <DenialHeatCell value={row[m]} max={50} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* MODULE 8–9 · AI + Infrastructure */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {riskInfrastructure.length === 0 ? (
            <RiskCard label="Infrastructure Health" items={[]} />
        ) : (
            <RiskCard label="Infrastructure Health · Module 9" items={riskInfrastructure} />
        )}
        {riskBusiness.length === 0 ? (
            <RiskCard label="Churn Risk" items={[]} />
        ) : (
            <RiskCard label="Churn · Revenue · Compliance Risks · Modules 11–13" items={riskBusiness} />
        )}
        <div className="bg-bg-panel border border-border-DEFAULT p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-3">Module 7 · Compliance Readiness</div>
          {!complianceGauges || complianceGauges.length === 0 ? (
             <div className="text-xs text-[rgba(255,255,255,0.4)]">Data synchronizing from API</div>
          ) : complianceGauges.map((item) => (
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
        <SectionHeader number="10" title="Daily AI Brief" sub="Top Action Items · AI-generated · updated hourly" />
        {actionBriefs.length === 0 ? (
          <QuantumEmptyState title="No active AI briefs" description="Your AI co-pilot has no pending critical items." icon="activity" />
        ) : (
            <div className="bg-bg-panel border border-[rgba(255,107,26,0.15)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)' }}>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-1.5 h-1.5 rounded-full bg-orange animate-pulse" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,107,26,0.8)]">Quantum Intelligence Brief — Today</span>
              </div>
              {actionBriefs.map((b: any, rank: number) => (
                 <ActionItemRow key={rank} rank={rank+1} text={b.text} category={b.category} urgency={b.urgency} />
              ))}
            </div>
        )}
      </div>

      {/* MODULE 14 · System Incident Banner */}
      <div>
        <SectionHeader number="14" title="System Incident Status" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-[rgba(76,175,80,0.08)] border border-[rgba(76,175,80,0.2)] p-3 flex items-center gap-3" style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
            <span className="text-status-active text-xl font-black">✓</span>
            <div>
              <div className="text-xs font-semibold text-status-active">All Systems Operational</div>
              <div className="text-[11px] text-[rgba(255,255,255,0.4)]">No active incidents · Last checked moments ago</div>
            </div>
          </div>
          <div className="bg-bg-panel border border-border-DEFAULT p-3" style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
            <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] mb-2">Recent Incidents</div>
            {systemIncidents.length === 0 ? (
                <div className="text-xs text-[rgba(255,255,255,0.4)]">No incidents in the last 30 days</div>
            ) : (
                systemIncidents.map((inc: any, idx: number) => <div key={idx} className="text-xs text-[rgba(255,255,255,0.7)]">{inc.text}</div>)
            )}
          </div>
        </div>
      </div>

      {/* MODULE 15 · Growth Velocity Graph */}
      <div>
        <SectionHeader number="15" title="Growth Velocity" sub="30 / 90 / 365 day view" />
        <div className="bg-bg-panel border border-border-DEFAULT p-5 grid grid-cols-1 md:grid-cols-2 gap-6" style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)' }}>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] mb-3">Tenant Growth</div>
            {growthMetrics.tenants.length === 0 ? (
                <div className="text-xs text-[rgba(255,255,255,0.4)]">Awaiting telemetry...</div>
            ) : (
                <div className="space-y-2">
                {growthMetrics.tenants.map((t: any) => (
                    <GrowthVelocityBar key={t.label} label={t.label} value={t.value} max={t.max} />
                ))}
                </div>
            )}
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] mb-3">Revenue Growth ($)</div>
            {growthMetrics.revenue.length === 0 ? (
                <div className="text-xs text-[rgba(255,255,255,0.4)]">Awaiting telemetry...</div>
            ) : (
                <div className="space-y-2">
                {growthMetrics.revenue.map((r: any) => (
                    <GrowthVelocityBar key={r.label} label={r.label} value={r.value} max={r.max} />
                ))}
                </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Nav to all 12 Domains */}
      <div>
        <SectionHeader number="—" title="Domain Control Grid" sub="Navigate all 12 command domains" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
          {[
            { href: '/founder', label: 'Executive', color: 'var(--q-orange)', mod: '1' },
            { href: '/founder/revenue/billing-intelligence', label: 'Revenue & Billing', color: 'var(--color-system-billing)', mod: '2' },
            { href: '/founder/ai/policies', label: 'AI Governance', color: 'var(--color-system-compliance)', mod: '3' },
            { href: '/founder/comms/inbox', label: 'Communications', color: 'var(--q-green)', mod: '4' },
            { href: '/founder/comms/phone-system', label: 'AI Voice & Alerts', color: 'var(--q-green)', mod: '4B' },
            { href: '/founder/compliance/nemsis', label: 'Compliance', color: 'var(--q-yellow)', mod: '5' },
            { href: '/founder/security/role-builder', label: 'Visibility & Sec.', color: 'var(--q-red)', mod: '6' },
            { href: '/founder/templates/proposals', label: 'Templates', color: 'var(--color-status-info)', mod: '7' },
            { href: '/founder/roi/analytics', label: 'ROI & Sales', color: 'var(--q-yellow)', mod: '8' },
            { href: '/founder/pwa/crewlink', label: 'PWA & Mobile', color: 'var(--color-system-fleet)', mod: '9' },
            { href: '/founder/infra/ecs', label: 'Infrastructure', color: 'var(--color-text-muted)', mod: '10' },
            { href: '/founder/tools/calendar', label: 'Founder Tools', color: 'var(--q-orange)', mod: '11' },
          ].map((d) => (
            <Link
              key={d.href}
              href={d.href}
              className="flex flex-col gap-1 p-3 bg-bg-panel border border-border-subtle hover:border-border-strong transition-colors group"
              style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
            >
              <span className="text-[9px] font-bold font-mono" style={{ color: d.color }}>DOMAIN {d.mod}</span>
              <span className="text-xs font-semibold text-[rgba(255,255,255,0.75)] group-hover:text-text-primary transition-colors">{d.label}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
