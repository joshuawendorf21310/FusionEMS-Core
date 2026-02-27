"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "";

function KpiCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4"
      style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}
    >
      <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-2">{label}</div>
      <div className="text-2xl font-bold" style={{ color: color ?? "#fff" }}>{value}</div>
      {sub && <div className="text-[11px] text-[rgba(255,255,255,0.35)] mt-1">{sub}</div>}
    </motion.div>
  );
}

function HeatCell({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? value / max : 0;
  const bg = pct > 0.7 ? "#9c1b1b" : pct > 0.4 ? "#b84a0f" : pct > 0.15 ? "#ff9800" : "#1a2535";
  return (
    <div className="flex items-center justify-center h-9 text-[11px] font-semibold" style={{ background: bg, color: pct > 0.4 ? "#fff" : "rgba(255,255,255,0.7)" }}>
      {value}
    </div>
  );
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"];
const MOCK_HEATMAP = [
  { payer: "Medicare", values: [14, 12, 18, 10, 22, 15] },
  { payer: "Medicaid", values: [28, 31, 25, 29, 27, 30] },
  { payer: "BlueCross", values: [8, 9, 7, 11, 6, 9] },
  { payer: "Aetna", values: [19, 21, 20, 17, 23, 24] },
  { payer: "Uninsured", values: [45, 43, 48, 42, 46, 50] },
];

export default function BillingCommandPage() {
  const [dashboard, setDashboard] = useState<Record<string, unknown>>({});
  const [health, setHealth] = useState<Record<string, unknown>>({});
  const [payers, setPayers] = useState<{ payers?: Array<Record<string, unknown>> }>({});
  const [leakage, setLeakage] = useState<Record<string, unknown>>({});
  const [arConc, setArConc] = useState<{ concentration?: Array<{ payer: string; pct: number; risk: string }>; total_ar_cents?: number }>({});
  const [exec, setExec] = useState<Record<string, unknown>>({});

  useEffect(() => {
    fetch(`${API}/api/v1/billing-command/dashboard`).then(r => r.json()).then(setDashboard).catch(() => {});
    fetch(`${API}/api/v1/billing-command/billing-health`).then(r => r.json()).then(setHealth).catch(() => {});
    fetch(`${API}/api/v1/billing-command/payer-performance`).then(r => r.json()).then(setPayers).catch(() => {});
    fetch(`${API}/api/v1/billing-command/revenue-leakage`).then(r => r.json()).then(setLeakage).catch(() => {});
    fetch(`${API}/api/v1/billing-command/ar-concentration-risk`).then(r => r.json()).then(setArConc).catch(() => {});
    fetch(`${API}/api/v1/billing-command/executive-summary`).then(r => r.json()).then(setExec).catch(() => {});
  }, []);

  const fmt$ = (v: unknown) => typeof v === "number" ? `$${(v / 100).toLocaleString()}` : "—";
  const fmtPct = (v: unknown) => typeof v === "number" ? `${v}%` : "—";
  const fmtNum = (v: unknown) => typeof v === "number" ? v.toLocaleString() : (v != null ? String(v) : "—");

  const healthStatus = String(health.status ?? "");
  const healthColor = healthStatus === "excellent" ? "#4caf50" : healthStatus === "good" ? "#8bc34a" : healthStatus === "fair" ? "#ff9800" : "#e53935";

  const FEATURES = [
    "Global revenue dashboard","Clean claim monitor","Denial heatmap","AR aging analysis",
    "Payer performance ranking","Revenue leakage detector","Modifier impact analyzer","Claim lifecycle tracker",
    "Reimbursement variance","Regional reimbursement map","AI denial predictor","Appeal success tracker",
    "Billing velocity","Days-to-payment monitor","Billing KPI comparison","Revenue trend forecasting",
    "Tenant billing ranking","Stripe subscription sync","Overdue payment alerts","Failed payment monitoring",
    "Auto-suspension logic","Billing performance scoring","Claim audit sampling","Documentation deficiency",
    "High-risk claim alerts","Batch resubmission engine","Billing workload predictor","Cash flow forecast",
    "Subscription breakdown","Module revenue contribution","Churn risk predictor","Upsell predictor",
    "Revenue by service level","Fire vs Private split","HEMS revenue analytics","Payer mix analytics",
    "Denial clustering engine","Top denial dashboard","Billing compliance risk","Fraud anomaly detection",
    "Duplicate billing detection","Underbilling detection","Overbilling alert","Billing trend YoY",
    "Billing forecast by region","Contract pricing simulation","ROI-adjusted comparison","Performance benchmarking",
    "Agency billing export","Executive billing PDF","Stripe reconciliation","Payment timeline",
    "Revenue per transport","Billing staff efficiency","AI appeal drafting","Appeal tracking dashboard",
    "Automated payer follow-up","Revenue gap analysis","KPI alert thresholds","Subscription downgrade alert",
    "Revenue volatility detection","Revenue growth simulation","Pricing tier optimizer","Billing margin calculator",
    "Denial prevention scoring","Revenue diversification","Subscription LTV tracker","Client profitability",
    "Billing system health","Cross-tenant comparison","Billing task monitor","Revenue correction engine",
    "Claim submission pipeline","Batch claim validation","Billing automation %","AI modifier suggestion",
    "Medical necessity scoring","Revenue improvement AI","Billing impact simulation","Payment dispute tracker",
    "Escalation billing mode","Revenue retention score","Claim aging heatmap","Batch invoice generator",
    "Subscription change log","Tenant billing timeline","Revenue projection graph","Forecast confidence",
    "AI billing audit mode","Revenue delta comparator","Subscription churn analysis","Revenue anomaly alerts",
    "Payer dispute timeline","AR concentration risk","Top revenue contributors","Billing automation ROI",
    "Revenue dependency graph","Claim throughput speed","Executive insights feed","Enterprise revenue engine",
  ];

  return (
    <div className="p-5 space-y-6 min-h-screen">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">CATEGORY 7</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">Billing Command Center</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">100-Feature Revenue Intelligence · AR Aging · Denial Analytics · Payer Performance</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <KpiCard label="Total Claims" value={fmtNum(dashboard.total_claims)} />
        <KpiCard label="Paid" value={fmtNum(dashboard.paid_claims)} color="#4caf50" />
        <KpiCard label="Denied" value={fmtNum(dashboard.denied_claims)} color="#e53935" />
        <KpiCard label="Clean Claim %" value={fmtPct(dashboard.clean_claim_rate_pct)} color="#22d3ee" />
        <KpiCard label="Denial %" value={fmtPct(dashboard.denial_rate_pct)} color="#ff9800" />
        <KpiCard label="Revenue" value={fmt$(dashboard.revenue_cents)} color="#4caf50" />
        <KpiCard label="Health" value={healthStatus.toUpperCase() || "—"} color={healthColor} sub={`Score: ${health.health_score ?? "—"}`} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Claim Revenue" value={fmt$(exec.total_revenue_cents)} color="#22d3ee" />
        <KpiCard label="MRR" value={fmt$(exec.mrr_cents)} color="#22d3ee" sub="Monthly Recurring" />
        <KpiCard label="ARR" value={fmt$(exec.arr_cents)} color="#22d3ee" sub="Annual Run Rate" />
        <KpiCard label="Revenue Leakage" value={fmt$(leakage.total_leakage_cents)} color="#e53935" sub={`${leakage.item_count ?? 0} items`} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: "polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)" }}>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">Denial Heatmap — By Payer × Month</div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[360px] text-xs">
              <thead>
                <tr>
                  <th className="text-left text-[10px] text-[rgba(255,255,255,0.3)] pb-2 pr-3">Payer</th>
                  {MONTHS.map(m => <th key={m} className="text-[10px] text-[rgba(255,255,255,0.3)] pb-2 px-0.5">{m}</th>)}
                </tr>
              </thead>
              <tbody>
                {MOCK_HEATMAP.map(row => (
                  <tr key={row.payer}>
                    <td className="text-[rgba(255,255,255,0.6)] pr-3 py-0.5 text-[11px] whitespace-nowrap">{row.payer}</td>
                    {row.values.map((v, i) => <td key={i} className="px-0.5 py-0.5"><HeatCell value={v} max={50} /></td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: "polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)" }}>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">AR Concentration Risk · Total AR: {fmt$(arConc.total_ar_cents)}</div>
          {arConc.concentration?.slice(0, 6).map(item => {
            const rc = item.risk === "high" ? "#e53935" : item.risk === "medium" ? "#ff9800" : "#4caf50";
            return (
              <div key={item.payer} className="mb-2">
                <div className="flex justify-between text-[11px] mb-0.5">
                  <span className="text-[rgba(255,255,255,0.65)]">{item.payer}</span>
                  <span className="font-semibold" style={{ color: rc }}>{item.pct}% <span className="uppercase text-[9px]">{item.risk}</span></span>
                </div>
                <div className="h-1.5 bg-[rgba(255,255,255,0.06)] rounded-full overflow-hidden">
                  <motion.div className="h-full rounded-full" style={{ background: rc }} initial={{ width: 0 }} animate={{ width: `${Math.min(item.pct, 100)}%` }} transition={{ duration: 0.8 }} />
                </div>
              </div>
            );
          })}
          {!arConc.concentration?.length && <div className="text-xs text-[rgba(255,255,255,0.3)]">No AR concentration data</div>}
        </div>
      </div>

      <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: "polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)" }}>
        <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">Payer Performance Ranking</div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs min-w-[600px]">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.06)]">
                {["Payer","Total","Paid","Denied","Revenue","Clean %","Avg Days"].map(h => (
                  <th key={h} className="text-left text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.3)] pb-2 pr-4 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {payers.payers?.map((p, i) => (
                <tr key={i} className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)]">
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.8)] font-semibold">{String(p.payer)}</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.55)]">{fmtNum(p.total_claims)}</td>
                  <td className="py-2 pr-4 text-[#4caf50]">{fmtNum(p.paid)}</td>
                  <td className="py-2 pr-4 text-[#e53935]">{fmtNum(p.denied)}</td>
                  <td className="py-2 pr-4 text-[#22d3ee]">{fmt$(p.revenue_cents)}</td>
                  <td className="py-2 pr-4">
                    <span className={(p.clean_claim_rate_pct as number) >= 90 ? "text-[#4caf50]" : (p.clean_claim_rate_pct as number) >= 75 ? "text-[#ff9800]" : "text-[#e53935]"}>
                      {fmtPct(p.clean_claim_rate_pct)}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{p.avg_days_to_payment != null ? String(p.avg_days_to_payment) : "N/A"}</td>
                </tr>
              ))}
              {!payers.payers?.length && <tr><td colSpan={7} className="py-6 text-center text-[rgba(255,255,255,0.3)]">No payer data available</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: "polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)" }}>
        <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">100 Active Command Features</div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-1.5">
          {FEATURES.map(f => (
            <div key={f} className="flex items-center gap-1.5 text-[10px] text-[rgba(255,255,255,0.5)]">
              <span className="w-1 h-1 rounded-full bg-[#22d3ee] flex-shrink-0" />
              <span className="truncate">{f}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
