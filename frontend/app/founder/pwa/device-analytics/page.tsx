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
  ok: { bg: 'rgba(76,175,80,0.15)', color: 'var(--q-green)' },
  warn: { bg: 'rgba(255,152,0,0.15)', color: 'var(--q-yellow)' },
  error: { bg: 'rgba(229,57,53,0.15)', color: 'var(--q-red)' },
  info: { bg: 'rgba(41,182,246,0.15)', color: 'var(--color-status-info)' },
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

const osDistribution = [
  { os: 'iOS 17', count: 12, pct: 25.5, color: 'var(--color-status-info)' },
  { os: 'Android 13', count: 18, pct: 38.3, color: 'var(--q-green)' },
  { os: 'Android 14', count: 13, pct: 27.7, color: DOMAIN_COLOR },
  { os: 'Other', count: 4, pct: 8.5, color: 'rgba(255,255,255,0.3)' },
];

const perfByType = [
  { type: 'iPhone (iOS)', avgLoad: 820, crashRate: '0.01%', sessions: 14, rating: '4.9' },
  { type: 'Android Flagship', avgLoad: 940, crashRate: '0.02%', sessions: 21, rating: '4.8' },
  { type: 'Android Mid-range', avgLoad: 1380, crashRate: '0.04%', sessions: 10, rating: '4.6' },
  { type: 'Tablet', avgLoad: 1100, crashRate: '0.00%', sessions: 4, rating: '4.7' },
];

const batteryEntries = [
  { name: 'iPhone 15 — J. Martinez', battery: 87, charge: 'discharging', health: 'good' as const },
  { name: 'Pixel 8 — T. Williams', battery: 63, charge: 'discharging', health: 'good' as const },
  { name: 'Galaxy S24 — R. Chen', battery: 41, charge: 'charging', health: 'good' as const },
  { name: 'iPhone 14 — A. Patel', battery: 92, charge: 'charging', health: 'good' as const },
  { name: 'Pixel 7 — D. Thompson', battery: 15, charge: 'discharging', health: 'fair' as const },
  { name: 'Galaxy A54 — S. Nguyen', battery: 78, charge: 'discharging', health: 'good' as const },
  { name: 'iPad Air — Station 4', battery: 55, charge: 'charging', health: 'good' as const },
  { name: 'Pixel 6 — K. Okafor', battery: 28, charge: 'discharging', health: 'poor' as const },
];

const healthStatusMap: Record<string, 'ok' | 'warn' | 'error'> = {
  good: 'ok',
  fair: 'warn',
  poor: 'error',
};

const batteryColor = (b: number) => b > 50 ? 'var(--color-status-active)' : b > 20 ? 'var(--color-status-warning)' : 'var(--color-brand-red)';

const connectivity = [
  { type: 'WiFi', devices: 24, color: 'var(--q-green)', total: 47 },
  { type: '4G LTE', devices: 18, color: DOMAIN_COLOR, total: 47 },
  { type: '5G', devices: 5, color: 'var(--color-system-compliance)', total: 47 },
];

const crashLog = [
  { ts: '2026-02-26 14:22', device: 'Pixel 7 — D. Thompson', error: 'NullPointerException', version: 'v2.3.9' },
  { ts: '2026-02-25 09:47', device: 'Galaxy A54 — S. Nguyen', error: 'NetworkTimeoutError', version: 'v2.4.0' },
  { ts: '2026-02-24 18:03', device: 'Pixel 7 — D. Thompson', error: 'OutOfMemoryError', version: 'v2.3.9' },
];

// Usage heat data (0-23h): realistic EMS usage pattern
const heatData = [
  2, 1, 1, 2, 4, 8, 18, 28, 35, 40, 42, 38,
  36, 34, 37, 39, 41, 45, 48, 43, 31, 18, 10, 5,
];
const maxHeat = Math.max(...heatData);

const heatColor = (v: number, max: number) => {
  const intensity = v / max;
  if (intensity < 0.15) return 'rgba(59,130,246,0.08)';
  if (intensity < 0.35) return 'rgba(59,130,246,0.22)';
  if (intensity < 0.55) return 'rgba(59,130,246,0.42)';
  if (intensity < 0.75) return 'rgba(59,130,246,0.65)';
  return 'rgba(59,130,246,0.90)';
};

export default function DeviceAnalyticsPage() {
  return (
    <div className="p-5 min-h-screen bg-bg-void">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="pb-4 mb-6 border-b border-border-DEFAULT">
        <div className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: DOMAIN_COLOR }}>
          9 · PWA &amp; MOBILE
        </div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Device Analytics</h1>
        <p className="text-xs text-text-muted mt-1">Fleet telemetry · OS distribution · Performance &amp; health monitoring</p>
      </motion.div>

      {/* MODULE 1 — Fleet Overview */}
      <motion.div custom={0} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 1" title="Fleet Overview" sub="Complete device inventory snapshot" />
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <StatCard label="Total Devices" value={47} color={DOMAIN_COLOR} />
          <StatCard label="iOS" value={12} color="var(--color-status-info)" />
          <StatCard label="Android" value={31} color="var(--color-status-active)" />
          <StatCard label="Tablets" value={4} color="var(--color-system-compliance)" />
          <StatCard label="Avg Battery" value="78%" color="var(--color-status-warning)" />
          <StatCard label="Active Sessions" value={31} color="var(--color-status-info)" />
        </div>
      </motion.div>

      {/* MODULE 2 — OS Distribution */}
      <motion.div custom={1} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 2" title="OS Distribution" sub="Operating system spread across fleet" />
        <Panel>
          <div className="space-y-4">
            {osDistribution.map((os, i) => (
              <div key={i}>
                <div className="flex justify-between items-center mb-1.5">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ background: os.color }} />
                    <span className="text-xs font-bold text-text-primary">{os.os}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[11px] text-[rgba(255,255,255,0.55)]">{os.count} devices</span>
                    <span className="text-[11px] font-bold w-10 text-right" style={{ color: os.color }}>{os.pct}%</span>
                  </div>
                </div>
                <ProgressBar value={os.pct} max={100} color={os.color} />
              </div>
            ))}
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 3 — App Performance by Device Type */}
      <motion.div custom={2} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 3" title="App Performance by Device Type" sub="Load time · crash rate · session counts" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-text-muted border-b border-border-subtle">
                  {['Device Type', 'Avg Load (ms)', 'Crash Rate', 'Sessions Today', 'Rating'].map(h => (
                    <th key={h} className="text-left pb-2 pr-5 font-bold uppercase tracking-widest text-[10px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {perfByType.map((row, i) => (
                  <tr key={i} className="border-b border-border-subtle last:border-0">
                    <td className="py-2.5 pr-5 text-text-primary font-medium">{row.type}</td>
                    <td className="py-2.5 pr-5 font-mono" style={{ color: row.avgLoad < 1000 ? 'var(--color-status-active)' : row.avgLoad < 1200 ? 'var(--color-status-warning)' : 'var(--color-brand-red)' }}>
                      {row.avgLoad}ms
                    </td>
                    <td className="py-2.5 pr-5 text-[rgba(255,255,255,0.7)] font-mono">{row.crashRate}</td>
                    <td className="py-2.5 pr-5 text-[rgba(255,255,255,0.55)]">{row.sessions}</td>
                    <td className="py-2.5 font-bold" style={{ color: DOMAIN_COLOR }}>{row.rating}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 4 — Battery Health Monitor */}
      <motion.div custom={3} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 4" title="Battery Health Monitor" sub="Real-time charge levels and health status" />
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          {batteryEntries.map((d, i) => (
            <Panel key={i}>
              <div className="text-[11px] font-bold text-text-primary mb-2 leading-tight">{d.name}</div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-[10px] text-text-muted">{d.charge}</span>
                <span className="text-sm font-black" style={{ color: batteryColor(d.battery) }}>{d.battery}%</span>
              </div>
              <ProgressBar value={d.battery} max={100} color={batteryColor(d.battery)} />
              <div className="mt-2">
                <Badge label={d.health} status={healthStatusMap[d.health]} />
              </div>
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 5 — Network Connectivity */}
      <motion.div custom={4} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 5" title="Network Connectivity" sub="Connection type distribution across active devices" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {connectivity.map((conn, i) => (
            <Panel key={i}>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-3 h-3 rounded-full" style={{ background: conn.color }} />
                <span className="text-xs font-bold text-text-primary uppercase tracking-widest">{conn.type}</span>
              </div>
              <div className="text-3xl font-black mb-1" style={{ color: conn.color }}>{conn.devices}</div>
              <div className="text-[10px] text-text-muted mb-2">
                devices ({Math.round((conn.devices / conn.total) * 100)}% of fleet)
              </div>
              <ProgressBar value={conn.devices} max={conn.total} color={conn.color} />
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 6 — Crash & Error Log */}
      <motion.div custom={5} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 6" title="Crash &amp; Error Log" sub="Last 5 recorded crash events" />
        <Panel>
          {crashLog.length === 0 ? (
            <div className="text-center py-8 text-[rgba(255,255,255,0.25)] text-xs uppercase tracking-widest">
              No crashes in last 7 days
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-text-muted border-b border-border-subtle">
                    {['Timestamp', 'Device', 'Error Type', 'Version'].map(h => (
                      <th key={h} className="text-left pb-2 pr-5 font-bold uppercase tracking-widest text-[10px]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {crashLog.map((row, i) => (
                    <tr key={i} className="border-b border-border-subtle last:border-0">
                      <td className="py-2.5 pr-5 text-text-muted font-mono text-[10px]">{row.ts}</td>
                      <td className="py-2.5 pr-5 text-[rgba(255,255,255,0.7)]">{row.device}</td>
                      <td className="py-2.5 pr-5"><span className="font-mono text-red">{row.error}</span></td>
                      <td className="py-2.5"><Badge label={row.version} status={row.version === 'v2.4.1' ? 'ok' : row.version === 'v2.4.0' ? 'warn' : 'error'} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </motion.div>

      {/* MODULE 7 — Usage Heatmap by Hour */}
      <motion.div custom={6} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
        <SectionHeader number="MOD 7" title="Usage Heatmap by Hour" sub="Active sessions per hour (0–23) · darker = higher load" />
        <Panel>
          <div className="grid grid-cols-12 gap-1.5">
            {heatData.map((v, hour) => (
              <div key={hour} className="flex flex-col items-center gap-1">
                <div
                  className="w-full h-10 rounded-sm border border-border-subtle flex items-center justify-center"
                  style={{ background: heatColor(v, maxHeat) }}
                  title={`${hour}:00 — ${v} sessions`}
                >
                  <span className="text-[9px] font-bold text-text-primary opacity-80">{v}</span>
                </div>
                <span className="text-[9px] text-[rgba(255,255,255,0.25)] font-mono leading-none">{String(hour).padStart(2, '0')}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-3 mt-4">
            <span className="text-[10px] text-text-muted">Low</span>
            {[0.08, 0.22, 0.42, 0.65, 0.90].map((op, i) => (
              <div key={i} className="w-6 h-3 rounded-sm" style={{ background: `rgba(59,130,246,${op})` }} />
            ))}
            <span className="text-[10px] text-text-muted">High</span>
          </div>
        </Panel>
      </motion.div>

      <Link href="/founder" className="text-xs text-orange-dim hover:text-orange transition-colors">
        &larr; Back to Founder Command OS
      </Link>
    </div>
  );
}
