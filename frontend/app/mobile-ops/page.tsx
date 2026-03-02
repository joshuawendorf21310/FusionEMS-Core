"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "";

function KpiCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      className="bg-bg-panel border border-border-DEFAULT p-4"
      style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}>
      <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-2">{label}</div>
      <div className="text-2xl font-bold" style={{ color: color ?? "var(--color-text-primary)" }}>{value}</div>
      {sub && <div className="text-[11px] text-[rgba(255,255,255,0.35)] mt-1">{sub}</div>}
    </motion.div>
  );
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = { active: "var(--color-status-active)", healthy: "var(--color-status-active)", deployed: "var(--color-status-active)", logged_out: "var(--color-text-muted)", wiped: "var(--color-brand-red)", pending: "var(--color-status-warning)", failed: "var(--color-brand-red)" };
  return <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: colors[status] ?? "var(--color-text-muted)" }} />;
}

const FEATURES = [
  "CrewLink PWA deployment","Scheduling PWA deploy","Version tracking","Device registration",
  "Push notification keys","App manifest editor","Offline sync engine","Update enforcement",
  "Version adoption analytics","Mobile error reporting","Device performance monitor","Push failure analytics",
  "User session monitor","Credential expiration alerts","Shift swap approval","Scheduling conflict detector",
  "Staffing shortage predictor","Credential compliance","Mobile OCR capture","Facesheet scan validator",
  "Vital sign auto-detect","Rhythm strip parser","Vent settings extractor","Infusion pump capture",
  "Medication recognition","Lab result OCR","Field mapping NEMSIS","Provider verification",
  "Real-time sync conflicts","Offline data encryption","Mobile biometric login","Push priority control",
  "Incident acknowledgment","Dispatch-EPCR linking","Real-time incident map","Multi-device session",
  "App crash analytics","Mobile compliance mode","Data usage monitor","Low bandwidth fallback",
  "Image compression control","Secure file upload","Tenant PWA branding","App feature gating",
  "Remote device logout","Device trust scoring","Geo-based alert routing","Mobile SLA monitor",
  "Push analytics dashboard","Deployment rollback","Mobile policy enforcement","Role-based mobile access",
  "Offline validation rules","Scheduling heatmap","Crew availability analytics","Shift coverage forecast",
  "Overtime risk alert","Credential gap detection","Notification read tracking","Incident response time",
  "Device compliance check","Session timeout enforcement","Multi-agency management","Tenant push templates",
  "Mobile audit trail","In-app messaging","Secure camera capture","Background sync monitor",
  "Image integrity verification","Upload retry logic","Mobile alert escalation","Credential upload portal",
  "Training module push","App usage analytics","Mobile performance scoring","Battery usage alert",
  "Offline queue monitor","Sync health indicator","Secure local storage","PWA installation tracking",
  "Version compliance enforcement","Push quiet hours","Mobile UI personalization","On-call notifications",
  "Incident priority tagging","Real-time transport status","EPCR draft auto-save","NEMSIS mobile alerts",
  "Crew performance analytics","Shift confirmation alerts","Geo-fencing alerts","Multi-language support",
  "Remote config update","App feature toggle","Mobile auth logs","Secure data wipe",
  "PWA CDN health","Deployment cost tracking","Mobile adoption KPI","Enterprise mobile engine",
];

export default function MobileOpsPage() {
  const [deployments, setDeployments] = useState<{ deployments?: Array<Record<string, unknown>>; total?: number }>({});
  const [devices, setDevices] = useState<{ devices?: Array<Record<string, unknown>>; total?: number }>({});
  const [versionAdoption, setVersionAdoption] = useState<{ version_adoption?: Array<{ version: string; count: number; pct: number }>; total_devices?: number }>({});
  const [syncHealth, setSyncHealth] = useState<Record<string, unknown>>({});
  const [pushAnalytics, setPushAnalytics] = useState<Record<string, unknown>>({});
  const [adoptionKpis, setAdoptionKpis] = useState<Record<string, unknown>>({});
  const [credCompliance, setCredCompliance] = useState<Record<string, unknown>>({});
  const [shortage, setShortage] = useState<Record<string, unknown>>({});

  useEffect(() => {
    fetch(`${API}/api/v1/mobile-ops/pwa/deployments`).then(r => r.json()).then(setDeployments).catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/mobile-ops/devices`).then(r => r.json()).then(setDevices).catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/mobile-ops/pwa/version-adoption`).then(r => r.json()).then(setVersionAdoption).catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/mobile-ops/sync/health`).then(r => r.json()).then(setSyncHealth).catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/mobile-ops/push/analytics`).then(r => r.json()).then(setPushAnalytics).catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/mobile-ops/adoption/kpis`).then(r => r.json()).then(setAdoptionKpis).catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/mobile-ops/credentials/compliance`).then(r => r.json()).then(setCredCompliance).catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/mobile-ops/staffing/shortage-predictor`).then(r => r.json()).then(setShortage).catch((e: unknown) => { console.warn("[fetch error]", e); });
  }, []);

  const fmtN = (v: unknown) => typeof v === "number" ? v.toLocaleString() : (v != null ? String(v) : "—");
  const fmtPct = (v: unknown) => typeof v === "number" ? `${v}%` : "—";

  const syncStatus = String(syncHealth.health ?? "unknown");
  const syncColor = syncStatus === "healthy" ? "var(--color-status-active)" : "var(--color-brand-red)";
  const shortageRisk = String(shortage.shortage_risk ?? "");
  const shortageColor = shortageRisk === "high" ? "var(--color-brand-red)" : shortageRisk === "medium" ? "var(--color-status-warning)" : "var(--color-status-active)";

  return (
    <div className="p-5 space-y-6 min-h-screen">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">CATEGORY 9</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">PWA Deployment & Mobile Ops</h1>
        <p className="text-xs text-text-muted mt-0.5">100-Feature Mobile Command · CrewLink · Scheduling · OCR · Push Notifications · Compliance</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        <KpiCard label="PWA Deployments" value={fmtN(deployments.total)} color="var(--color-status-info)" />
        <KpiCard label="Registered Devices" value={fmtN(devices.total)} />
        <KpiCard label="Active Devices" value={fmtN(adoptionKpis.active_devices)} color="var(--color-status-active)" />
        <KpiCard label="Adoption Rate" value={fmtPct(adoptionKpis.adoption_rate_pct)} color="var(--color-status-info)" />
        <KpiCard label="Push Sent" value={fmtN(pushAnalytics.sent)} color="var(--color-system-fleet)" />
        <KpiCard label="Push Read Rate" value={fmtPct(pushAnalytics.read_rate_pct)} color="var(--color-status-info)" />
        <KpiCard label="Sync Health" value={syncStatus.toUpperCase()} color={syncColor} />
        <KpiCard label="Shortage Risk" value={shortageRisk.toUpperCase() || "—"} color={shortageColor} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Deployments */}
        <div className="bg-bg-panel border border-border-DEFAULT p-4" style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-3">PWA Deployments</div>
          {deployments.deployments?.slice(0, 6).map((d, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b border-[rgba(255,255,255,0.05)] last:border-0">
              <div className="flex items-center gap-2">
                <StatusDot status={String(d.data ? (d.data as Record<string,unknown>).status : "")} />
                <span className="text-xs text-[rgba(255,255,255,0.7)] truncate">{String(d.data ? (d.data as Record<string,unknown>).pwa_name ?? "PWA" : "PWA")}</span>
              </div>
              <span className="text-[10px] text-[rgba(255,255,255,0.35)]">v{String(d.data ? (d.data as Record<string,unknown>).version ?? "" : "")}</span>
            </div>
          ))}
          {!deployments.deployments?.length && <div className="text-xs text-[rgba(255,255,255,0.3)]">No deployments yet</div>}
        </div>

        {/* Version Adoption */}
        <div className="bg-bg-panel border border-border-DEFAULT p-4" style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-3">Version Adoption · {fmtN(versionAdoption.total_devices)} Devices</div>
          {versionAdoption.version_adoption?.map(v => (
            <div key={v.version} className="mb-2">
              <div className="flex justify-between text-[11px] mb-0.5">
                <span className="text-[rgba(255,255,255,0.6)]">{v.version}</span>
                <span className="font-semibold text-text-primary">{v.pct}%</span>
              </div>
              <div className="h-1.5 bg-[rgba(255,255,255,0.06)] rounded-full overflow-hidden">
                <motion.div className="h-full rounded-full bg-system-fleet" initial={{ width: 0 }} animate={{ width: `${v.pct}%` }} transition={{ duration: 0.8 }} />
              </div>
            </div>
          ))}
          {!versionAdoption.version_adoption?.length && <div className="text-xs text-[rgba(255,255,255,0.3)]">No version data yet</div>}
        </div>

        {/* Compliance */}
        <div className="bg-bg-panel border border-border-DEFAULT p-4" style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-3">Credential Compliance</div>
          {[
            { label: "Total Credentials", value: fmtN(credCompliance.total_credentials), color: "var(--color-text-primary)" },
            { label: "Compliant", value: fmtN(credCompliance.compliant), color: "var(--color-status-active)" },
            { label: "Expiring Soon", value: fmtN(credCompliance.expiring_soon), color: "var(--color-status-warning)" },
            { label: "Expired", value: fmtN(credCompliance.expired), color: "var(--color-brand-red)" },
          ].map(item => (
            <div key={item.label} className="flex justify-between py-2 border-b border-[rgba(255,255,255,0.05)] last:border-0 text-[11px]">
              <span className="text-[rgba(255,255,255,0.5)]">{item.label}</span>
              <span className="font-bold" style={{ color: item.color }}>{item.value}</span>
            </div>
          ))}
          <div className="mt-3">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-2">Sync Health</div>
            {[
              { label: "Pending Jobs", value: fmtN(syncHealth.pending), color: "var(--color-status-warning)" },
              { label: "Failed Jobs", value: fmtN(syncHealth.failed), color: "var(--color-brand-red)" },
              { label: "Completed", value: fmtN(syncHealth.completed), color: "var(--color-status-active)" },
            ].map(item => (
              <div key={item.label} className="flex justify-between py-1 text-[11px]">
                <span className="text-[rgba(255,255,255,0.5)]">{item.label}</span>
                <span className="font-bold" style={{ color: item.color }}>{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* OCR + Field Mapping */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-bg-panel border border-border-DEFAULT p-4" style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-3">Mobile OCR Capture Engine</div>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "Facesheet Scan", icon: "📋", status: "active" },
              { label: "Vital Sign Detect", icon: "💓", status: "active" },
              { label: "Rhythm Strip Parse", icon: "📈", status: "active" },
              { label: "Vent Settings", icon: "🫁", status: "active" },
              { label: "Infusion Pump", icon: "💉", status: "active" },
              { label: "Medication ID", icon: "💊", status: "active" },
              { label: "Lab Results", icon: "🧪", status: "active" },
              { label: "NEMSIS Mapping", icon: "🗺", status: "active" },
            ].map(item => (
              <div key={item.label} className="flex items-center gap-2 p-2 bg-[rgba(59,130,246,0.05)] border border-[rgba(59,130,246,0.15)] rounded-sm">
                <span className="text-sm">{item.icon}</span>
                <span className="text-[10px] text-text-secondary">{item.label}</span>
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-status-active" />
              </div>
            ))}
          </div>
        </div>

        <div className="bg-bg-panel border border-border-DEFAULT p-4" style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-3">Push Notification Analytics</div>
          {[
            { label: "Total Notifications", value: fmtN(pushAnalytics.total), color: "var(--color-text-primary)" },
            { label: "Sent", value: fmtN(pushAnalytics.sent), color: "var(--color-system-fleet)" },
            { label: "Failed", value: fmtN(pushAnalytics.failed), color: "var(--color-brand-red)" },
            { label: "Read", value: fmtN(pushAnalytics.read), color: "var(--color-status-active)" },
            { label: "Read Rate", value: fmtPct(pushAnalytics.read_rate_pct), color: "var(--color-status-info)" },
          ].map(item => (
            <div key={item.label} className="flex justify-between py-2 border-b border-[rgba(255,255,255,0.05)] last:border-0 text-[11px]">
              <span className="text-[rgba(255,255,255,0.5)]">{item.label}</span>
              <span className="font-bold" style={{ color: item.color }}>{item.value}</span>
            </div>
          ))}
          <div className="mt-3 text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-2">Staffing Shortage Predictor</div>
          <div className="flex items-center gap-3 p-2 bg-[rgba(255,255,255,0.03)] border border-border-subtle rounded-sm">
            <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: shortageColor }} />
            <span className="text-xs text-text-secondary">Shortage Risk: <strong style={{ color: shortageColor }}>{shortageRisk.toUpperCase() || "N/A"}</strong></span>
            <span className="ml-auto text-[10px] text-[rgba(255,255,255,0.35)]">{fmtN(shortage.unfilled_shifts)} unfilled</span>
          </div>
        </div>
      </div>

      <div className="bg-bg-panel border border-border-DEFAULT p-4" style={{ clipPath: "polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)" }}>
        <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-3">100 Active Mobile Features</div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-1.5">
          {FEATURES.map(f => (
            <div key={f} className="flex items-center gap-1.5 text-[10px] text-[rgba(255,255,255,0.5)]">
              <span className="w-1 h-1 rounded-full bg-system-fleet flex-shrink-0" />
              <span className="truncate">{f}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
