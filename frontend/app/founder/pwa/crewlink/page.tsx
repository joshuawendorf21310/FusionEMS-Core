'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const API = process.env.NEXT_PUBLIC_API_BASE ?? '';

const DOMAIN_COLOR = 'var(--color-system-fleet)';

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="mb-4">
      <div className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: DOMAIN_COLOR }}>
        {number} · {title}
      </div>
      {sub && <p className="text-[11px] text-text-muted">{sub}</p>}
    </div>
  );
}

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-bg-panel border border-border-DEFAULT p-4 ${className}`}
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      {children}
    </div>
  );
}

const badgeColors = {
  ok: { bg: 'rgba(76,175,80,0.15)', color: 'var(--q-green)', label: 'OK' },
  warn: { bg: 'rgba(255,152,0,0.15)', color: 'var(--q-yellow)', label: 'WARN' },
  error: { bg: 'rgba(229,57,53,0.15)', color: 'var(--q-red)', label: 'ERROR' },
  info: { bg: 'rgba(41,182,246,0.15)', color: 'var(--color-status-info)', label: 'INFO' },
};

function Badge({ label, status }: { label: string; status: 'ok' | 'warn' | 'error' | 'info' }) {
  const s = badgeColors[status];
  return (
    <span
      className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-sm"
      style={{ background: s.bg, color: s.color }}
    >
      {label}
    </span>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <Panel>
      <div className="text-[10px] uppercase tracking-widest text-text-muted mb-1">{label}</div>
      <div className="text-2xl font-black" style={{ color: color ?? 'var(--color-text-primary)' }}>{value}</div>
      {sub && <div className="text-[11px] text-text-muted mt-0.5">{sub}</div>}
    </Panel>
  );
}

function ProgressBar({ value, max, color }: { value: number; max: number; color?: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="h-2 rounded-full bg-[rgba(255,255,255,0.07)] overflow-hidden w-full">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${pct}%`, background: color ?? DOMAIN_COLOR }}
      />
    </div>
  );
}

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  visible: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.06, duration: 0.4 } }),
};

const crewActivity = [
  { name: 'J. Martinez', unit: 'M-12', activity: '2min ago', status: 'active', device: 'iPhone 15' },
  { name: 'T. Williams', unit: 'M-07', activity: '4min ago', status: 'active', device: 'Pixel 8' },
  { name: 'R. Chen', unit: 'M-03', activity: '11min ago', status: 'idle', device: 'Galaxy S24' },
  { name: 'A. Patel', unit: 'M-15', activity: '18min ago', status: 'idle', device: 'iPhone 14' },
  { name: 'D. Thompson', unit: 'M-09', activity: '47min ago', status: 'offline', device: 'Pixel 7' },
  { name: 'S. Nguyen', unit: 'M-01', activity: '1hr ago', status: 'offline', device: 'Galaxy A54' },
];

const statusMap: Record<string, 'ok' | 'warn' | 'error'> = {
  active: 'ok',
  idle: 'warn',
  offline: 'error',
};

const syncCategories = [
  { label: 'ePCR Records', synced: 412, max: 420, unit: 'records', color: DOMAIN_COLOR },
  { label: 'Vitals', synced: 1840, max: 1850, unit: 'entries', color: 'var(--color-system-billing)' },
  { label: 'Protocols', synced: 100, max: 100, unit: 'current', color: 'var(--q-green)' },
  { label: 'Maps', synced: 95, max: 100, unit: 'cached', color: 'var(--color-system-compliance)' },
];

const notifications = [
  { id: 1, time: '09:14', type: 'alert', text: 'Unit M-07 entered out-of-coverage zone — GPS signal lost' },
  { id: 2, time: '08:47', type: 'reminder', text: 'Crew certification renewal due in 3 days for R. Chen' },
  { id: 3, time: '08:02', type: 'system', text: 'PWA v2.4.1 successfully deployed to 44/47 devices' },
];

const notifTypeMap: Record<string, 'error' | 'warn' | 'info'> = {
  alert: 'error',
  reminder: 'warn',
  system: 'info',
};

const offlineTypes = [
  'Incident Templates',
  'Drug References',
  'Protocol Library',
  'Local Maps',
  'Patient History',
];

const devices = [
  { name: 'iPhone 15 — J. Martinez', battery: 87, os: 'iOS 17.4', app: 'v2.4.1', status: 'ok' as const },
  { name: 'Pixel 8 — T. Williams', battery: 63, os: 'Android 14', app: 'v2.4.1', status: 'ok' as const },
  { name: 'Galaxy S24 — R. Chen', battery: 41, os: 'Android 13', app: 'v2.4.0', status: 'warn' as const },
  { name: 'iPhone 14 — A. Patel', battery: 92, os: 'iOS 17.3', app: 'v2.4.1', status: 'ok' as const },
  { name: 'Pixel 7 — D. Thompson', battery: 15, os: 'Android 13', app: 'v2.3.9', status: 'error' as const },
  { name: 'Galaxy A54 — S. Nguyen', battery: 78, os: 'Android 12', app: 'v2.4.1', status: 'ok' as const },
];

const batteryColor = (b: number) => b > 50 ? 'var(--color-status-active)' : b > 20 ? 'var(--color-status-warning)' : 'var(--color-brand-red)';

export default function CrewLinkPage() {
  return (
    <div className="p-5 min-h-screen bg-bg-void">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="pb-4 mb-6 border-b border-border-DEFAULT">
        <div className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: DOMAIN_COLOR }}>
          9 · PWA &amp; MOBILE
        </div>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">CrewLink · Mobile Field App</h1>
          <Badge label="LIVE" status="ok" />
        </div>
        <p className="text-xs text-text-muted mt-1">Field crew mobile platform · Device management · Real-time sync</p>
      </motion.div>

      {/* MODULE 1 — Mobile Deployment Status */}
      <motion.div custom={0} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 1" title="Mobile Deployment Status" sub="Live device fleet telemetry" />
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatCard label="Active Devices" value={47} color={DOMAIN_COLOR} />
          <StatCard label="Online Now" value={31} color="var(--color-status-active)" />
          <StatCard label="Offline" value={16} color="var(--color-brand-red)" />
          <StatCard label="PWA Version" value="v2.4.1" color="var(--color-status-info)" />
          <StatCard label="Last Sync" value="2min ago" color="rgba(255,255,255,0.55)" />
        </div>
      </motion.div>

      {/* MODULE 2 — Crew App Activity Feed */}
      <motion.div custom={1} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 2" title="Crew App Activity Feed" sub="Real-time crew app sessions" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-text-muted border-b border-border-subtle">
                  {['Crew Member', 'Unit', 'Last Activity', 'Status', 'Device'].map(h => (
                    <th key={h} className="text-left pb-2 pr-4 font-bold uppercase tracking-widest text-[10px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {crewActivity.map((row, i) => (
                  <tr key={i} className="border-b border-border-subtle last:border-0">
                    <td className="py-2.5 pr-4 text-text-primary font-medium">{row.name}</td>
                    <td className="py-2.5 pr-4 text-[rgba(255,255,255,0.55)]">{row.unit}</td>
                    <td className="py-2.5 pr-4 text-[rgba(255,255,255,0.55)]">{row.activity}</td>
                    <td className="py-2.5 pr-4"><Badge label={row.status} status={statusMap[row.status]} /></td>
                    <td className="py-2.5 text-[rgba(255,255,255,0.55)]">{row.device}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 3 — Field Data Sync Panel */}
      <motion.div custom={2} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 3" title="Field Data Sync Panel" sub="Bidirectional sync health" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {syncCategories.map((cat, i) => (
            <Panel key={i}>
              <div className="flex justify-between items-center mb-2">
                <span className="text-[11px] font-bold text-text-primary uppercase tracking-widest">{cat.label}</span>
                <span className="text-[11px] text-[rgba(255,255,255,0.55)]">{cat.synced.toLocaleString()} {cat.unit}</span>
              </div>
              <ProgressBar value={cat.synced} max={cat.max} color={cat.color} />
              <div className="text-[10px] text-text-muted mt-1.5">{Math.round((cat.synced / cat.max) * 100)}% synced</div>
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 4 — Push Notification Center */}
      <motion.div custom={3} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 4" title="Push Notification Center" sub="Recent dispatches to field crew" />
        <Panel>
          <div className="space-y-3 mb-4">
            {notifications.map((n) => (
              <div key={n.id} className="flex items-start gap-3 border-b border-[rgba(255,255,255,0.05)] pb-3 last:border-0 last:pb-0">
                <span className="text-[10px] text-text-muted mt-0.5 w-10 shrink-0">{n.time}</span>
                <Badge label={n.type} status={notifTypeMap[n.type]} />
                <span className="text-xs text-[rgba(255,255,255,0.7)]">{n.text}</span>
              </div>
            ))}
          </div>
          <button
            className="text-xs font-bold uppercase tracking-widest px-4 py-2 rounded-sm border transition-colors"
            style={{ borderColor: DOMAIN_COLOR, color: DOMAIN_COLOR, background: 'rgba(59,130,246,0.08)' }}
            onClick={() => {}}
          >
            Send Broadcast
          </button>
        </Panel>
      </motion.div>

      {/* MODULE 5 — Offline Capability Report */}
      <motion.div custom={4} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 5" title="Offline Capability Report" sub="Data available without connectivity" />
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {offlineTypes.map((type, i) => (
            <Panel key={i} className="flex flex-col gap-2">
              <div className="text-xs font-bold text-text-primary">{type}</div>
              <Badge label="Available Offline" status="ok" />
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 6 — Device Health Grid */}
      <motion.div custom={5} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 6" title="Device Health Grid" sub="Per-device telemetry snapshot" />
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {devices.map((d, i) => (
            <Panel key={i}>
              <div className="text-xs font-bold text-text-primary mb-2">{d.name}</div>
              <div className="space-y-1.5 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-text-muted">Battery</span>
                  <span style={{ color: batteryColor(d.battery) }} className="font-bold">{d.battery}%</span>
                </div>
                <ProgressBar value={d.battery} max={100} color={batteryColor(d.battery)} />
                <div className="flex justify-between">
                  <span className="text-text-muted">OS</span>
                  <span className="text-[rgba(255,255,255,0.7)]">{d.os}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">App</span>
                  <span className="text-[rgba(255,255,255,0.7)]">{d.app}</span>
                </div>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-text-muted">Status</span>
                  <Badge label={d.status === 'ok' ? 'Healthy' : d.status === 'warn' ? 'Degraded' : 'Critical'} status={d.status} />
                </div>
              </div>
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 7 — App Performance Metrics */}
      <motion.div custom={6} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
        <SectionHeader number="MOD 7" title="App Performance Metrics" sub="Aggregate application health indicators" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Crash Rate" value="0.02%" sub="Last 30 days" color="var(--color-status-active)" />
          <StatCard label="Avg Load Time" value="1.2s" sub="P95 baseline" color={DOMAIN_COLOR} />
          <StatCard label="API Success Rate" value="99.8%" sub="Backend calls" color="var(--color-status-info)" />
          <StatCard label="Session Duration" value="42min" sub="Avg per crew" color="var(--color-system-compliance)" />
        </div>
      </motion.div>

      <Link href="/founder" className="text-xs text-orange-dim hover:text-orange transition-colors">
        &larr; Back to Founder Command OS
      </Link>
    </div>
  );
}
