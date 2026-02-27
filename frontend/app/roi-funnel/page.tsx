"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "";

function KpiCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4"
      style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}>
      <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-2">{label}</div>
      <div className="text-2xl font-bold" style={{ color: color ?? "#fff" }}>{value}</div>
      {sub && <div className="text-[11px] text-[rgba(255,255,255,0.35)] mt-1">{sub}</div>}
    </motion.div>
  );
}

function Slider({ label, min, max, value, onChange, unit }: { label: string; min: number; max: number; value: number; onChange: (v: number) => void; unit: string }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[11px]">
        <span className="text-[rgba(255,255,255,0.5)]">{label}</span>
        <span className="font-semibold text-white">{value.toLocaleString()}{unit}</span>
      </div>
      <input type="range" min={min} max={max} value={value} onChange={e => onChange(Number(e.target.value))}
        className="w-full accent-[#ff6b1a] h-1.5 cursor-pointer" />
    </div>
  );
}

const PLANS = [
  { key: "standard", label: "Standard", price: 499, color: "#94a3b8" },
  { key: "professional", label: "Professional", price: 899, color: "#22d3ee" },
  { key: "enterprise", label: "Enterprise", price: 1499, color: "#ff6b1a" },
];

const FEATURES = [
  "ZIP revenue estimator","Call volume projection","Payer mix estimator","% billing comparator",
  "Revenue retention calc","Multi-year ROI forecast","Growth scenario simulator","Break-even analysis",
  "Subscription cost model","Module impact estimator","Competitive comparison","Revenue opportunity heatmap",
  "Conversion funnel tracker","Abandoned signup recovery","Proposal auto-generator","Proposal analytics",
  "Stripe checkout integration","Subscription activation","BAA signing workflow","Contract digital signing",
  "Onboarding checklist","Plan tier AI recommendation","Module upsell predictor","Conversion A/B testing",
  "Signup geographic analytics","Lead scoring engine","Funnel drop-off heatmap","ROI accuracy tuning",
  "Revenue uplift estimator","Denial reduction model","Doc improvement impact","Subscription LTV estimate",
  "Module bundle suggestion","Proposal expiration timer","Automated follow-up","Pricing simulation sandbox",
  "Regional reimbursement DB","Service-level mapping","Conversion cohort analysis","ROI confidence score",
  "Historical validation","Sales script AI","Onboarding timeline","Compliance readiness",
  "Subscription churn model","Revenue per ZIP","Proposal-to-payment rate","ROI sharing export",
  "White-labeled ROI PDF","Conversion heatmap","Revenue gap comparison","Upsell probability",
  "Subscription forecast","Pricing sensitivity","Funnel stage automation","Self-service wizard",
  "Role assignment automation","Tenant auto-provisioning","Upgrade path preview","ROI recalculation",
  "Pricing fairness simulator","Competitive pricing","Module profitability","ROI explanation AI",
  "Interactive revenue sliders","Historical growth projection","Cost breakdown chart","Friction detection",
  "Signup intent detection","ROI sharing link","Proposal template library","Digital acceptance tracking",
  "Plan recommendation engine","Upgrade impact preview","Payment method validation","Billing start calc",
  "Grace period logic","ROI scenario comparison","Self-service doc upload","ROI summary email",
  "Conversion KPI dashboard","Lead source tracking","ROI recalibration","Trial-to-paid converter",
  "Revenue potential ranking","Pricing guarantee display","Proposal view analytics","Abandonment AI",
  "ROI-based prioritization","Subscription lifecycle","Trial engagement score","Funnel velocity metric",
  "Region-based upsell","Pricing bundle optimizer","Revenue simulation export","Sales forecasting",
  "Self-service activation","Downgrade prevention AI","Subscription revenue pipeline","Revenue acquisition engine",
];

export default function ROIFunnelPage() {
  const [callVolume, setCallVolume] = useState(1200);
  const [billingPct, setBillingPct] = useState(6);
  const [years, setYears] = useState(3);
  const [selectedPlan, setSelectedPlan] = useState("professional");
  const [roiResult, setRoiResult] = useState<Record<string, unknown> | null>(null);
  const [funnelData, setFunnelData] = useState<{ funnel?: Array<{ stage: string; count: number }>; total_events?: number }>({});
  const [kpis, setKpis] = useState<Record<string, unknown>>({});
  const [pipeline, setPipeline] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/v1/roi-funnel/conversion-funnel`).then(r => r.json()).then(setFunnelData).catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/roi-funnel/conversion-kpis`).then(r => r.json()).then(setKpis).catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/roi-funnel/revenue-pipeline`).then(r => r.json()).then(setPipeline).catch((e: unknown) => { console.warn("[fetch error]", e); });
  }, []);

  const handleCalculate = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/roi-funnel/roi-estimate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ zip_code: "53202", call_volume: callVolume, current_billing_pct: billingPct, years }),
      });
      const d = await r.json();
      setRoiResult(d.outputs ?? d);
    } catch (e: unknown) { console.warn("[roi-estimate error]", e); } finally {
      setLoading(false);
    }
  };

  const fmt$ = (v: unknown) => typeof v === "number" ? `$${(v / 100).toLocaleString()}` : (typeof v === "string" ? v : "—");
  const fmtN = (v: unknown) => typeof v === "number" ? v.toLocaleString() : (v != null ? String(v) : "—");

  const planPrice = PLANS.find(p => p.key === selectedPlan)?.price ?? 0;
  const est3yrRevenue = callVolume * 0.7 * 450 * years;
  const subscriptionCost = planPrice * 12 * years;
  const roi = subscriptionCost > 0 ? Math.round(((est3yrRevenue * 0.08) - subscriptionCost) / subscriptionCost * 100) : 0;

  const stageOrder = ["awareness","interest","consideration","intent","evaluation","purchase"];
  const maxCount = Math.max(...(funnelData.funnel?.map(s => s.count) ?? [1]), 1);

  return (
    <div className="p-5 space-y-6 min-h-screen">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">CATEGORY 8</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">ROI + Self-Service Funnel</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">100-Feature Revenue Intelligence · Lead Scoring · Proposals · Subscription Activation</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Total Events" value={fmtN(funnelData.total_events)} />
        <KpiCard label="Active Subscriptions" value={fmtN(kpis.active_subscriptions)} color="#4caf50" />
        <KpiCard label="Proposal → Paid" value={kpis.proposal_to_paid_conversion_pct != null ? `${kpis.proposal_to_paid_conversion_pct}%` : "—"} color="#22d3ee" />
        <KpiCard label="Pipeline Value" value={fmt$(pipeline.pending_pipeline_cents)} color="#ff9800" sub="Pending proposals" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ROI Calculator */}
        <div className="bg-[#0f1720] border border-[rgba(255,107,26,0.15)] p-5 space-y-4" style={{ clipPath: "polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)" }}>
          <div className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,107,26,0.7)]">Interactive ROI Calculator</div>

          <Slider label="Annual Call Volume" min={100} max={10000} value={callVolume} onChange={setCallVolume} unit=" calls" />
          <Slider label="Current Billing %" min={1} max={12} value={billingPct} onChange={setBillingPct} unit="%" />
          <Slider label="Projection Years" min={1} max={5} value={years} onChange={setYears} unit=" yr" />

          <div>
            <div className="text-[10px] text-[rgba(255,255,255,0.4)] mb-2">Select Plan</div>
            <div className="grid grid-cols-3 gap-2">
              {PLANS.map(p => (
                <button key={p.key} onClick={() => setSelectedPlan(p.key)}
                  className="py-2 text-[11px] font-semibold border rounded-sm transition-colors"
                  style={{
                    borderColor: selectedPlan === p.key ? p.color : "rgba(255,255,255,0.1)",
                    color: selectedPlan === p.key ? p.color : "rgba(255,255,255,0.45)",
                    background: selectedPlan === p.key ? `${p.color}15` : "transparent",
                  }}>
                  {p.label}<br /><span className="text-[10px] font-normal">${p.price}/mo</span>
                </button>
              ))}
            </div>
          </div>

          <div className="border border-[rgba(255,255,255,0.06)] rounded-sm p-3 space-y-2 text-[11px]">
            <div className="flex justify-between"><span className="text-[rgba(255,255,255,0.45)]">Est. {years}yr Revenue Uplift</span><span className="font-semibold text-[#4caf50]">${(est3yrRevenue * 0.08 / 100).toLocaleString()}</span></div>
            <div className="flex justify-between"><span className="text-[rgba(255,255,255,0.45)]">Subscription Cost ({years}yr)</span><span className="font-semibold text-[#ff9800]">${(subscriptionCost / 100).toLocaleString()}</span></div>
            <div className="flex justify-between border-t border-[rgba(255,255,255,0.06)] pt-2"><span className="text-[rgba(255,255,255,0.6)]">Estimated ROI</span><span className="text-xl font-black" style={{ color: roi >= 0 ? "#4caf50" : "#e53935" }}>{roi}%</span></div>
          </div>

          <button onClick={handleCalculate} disabled={loading}
            className="w-full h-9 text-xs font-bold uppercase tracking-wider bg-[rgba(255,107,26,0.2)] border border-[rgba(255,107,26,0.5)] text-[#ff6b1a] rounded-sm hover:bg-[rgba(255,107,26,0.3)] transition-colors disabled:opacity-50">
            {loading ? "Calculating…" : "Calculate & Save Scenario"}
          </button>

          {roiResult && (
            <div className="bg-[rgba(34,211,238,0.05)] border border-[rgba(34,211,238,0.2)] rounded-sm p-3 text-[11px] space-y-1">
              <div className="text-[10px] font-bold text-[#22d3ee] uppercase tracking-wider mb-2">Scenario Result</div>
              {Object.entries(roiResult).slice(0, 8).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-[rgba(255,255,255,0.45)] capitalize">{k.replace(/_/g, " ")}</span>
                  <span className="font-semibold text-white">{typeof v === "number" ? v.toLocaleString() : String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Conversion Funnel */}
        <div className="space-y-4">
          <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: "polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)" }}>
            <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">Conversion Funnel · {fmtN(funnelData.total_events)} Events</div>
            <div className="space-y-1.5">
              {(funnelData.funnel?.length ? funnelData.funnel : stageOrder.map(s => ({ stage: s, count: 0 }))).map((stage, i) => {
                const pct = maxCount > 0 ? (stage.count / maxCount) * 100 : 0;
                const colors = ["#ff6b1a","#ff9800","#f59e0b","#22d3ee","#3b82f6","#4caf50"];
                const c = colors[i % colors.length];
                return (
                  <div key={stage.stage}>
                    <div className="flex justify-between text-[11px] mb-0.5">
                      <span className="capitalize text-[rgba(255,255,255,0.6)]">{stage.stage}</span>
                      <span className="font-semibold text-white">{stage.count}</span>
                    </div>
                    <div className="h-5 bg-[rgba(255,255,255,0.04)] rounded-sm overflow-hidden relative">
                      <motion.div className="h-full rounded-sm flex items-center px-2" style={{ background: `${c}22`, borderLeft: `2px solid ${c}` }}
                        initial={{ width: 0 }} animate={{ width: `${Math.max(pct, 2)}%` }} transition={{ duration: 0.8, delay: i * 0.1 }}>
                      </motion.div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}>
            <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">Revenue Pipeline</div>
            <div className="space-y-2 text-[11px]">
              {[
                { label: "Pending Pipeline", value: fmt$(pipeline.pending_pipeline_cents), color: "#ff9800" },
                { label: "Active MRR", value: fmt$(pipeline.active_mrr_cents), color: "#4caf50" },
                { label: "Pipeline / MRR Ratio", value: pipeline.pipeline_to_mrr_ratio != null ? `${pipeline.pipeline_to_mrr_ratio}x` : "—", color: "#22d3ee" },
              ].map(item => (
                <div key={item.label} className="flex justify-between py-1.5 border-b border-[rgba(255,255,255,0.05)] last:border-0">
                  <span className="text-[rgba(255,255,255,0.5)]">{item.label}</span>
                  <span className="font-bold" style={{ color: item.color }}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: "polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)" }}>
        <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">100 Active Funnel Features</div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-1.5">
          {FEATURES.map(f => (
            <div key={f} className="flex items-center gap-1.5 text-[10px] text-[rgba(255,255,255,0.5)]">
              <span className="w-1 h-1 rounded-full bg-[#ff9800] flex-shrink-0" />
              <span className="truncate">{f}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
