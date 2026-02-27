'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const API = process.env.NEXT_PUBLIC_API_BASE ?? '';

const DOMAIN_COLOR = '#3b82f6';

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="mb-4">
      <div className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: DOMAIN_COLOR }}>
        {number} · {title}
      </div>
      {sub && <p className="text-[11px] text-[rgba(255,255,255,0.38)]">{sub}</p>}
    </div>
  );
}

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4 ${className}`}
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      {children}
    </div>
  );
}

const badgeColors = {
  ok: { bg: 'rgba(76,175,80,0.15)', color: '#4caf50' },
  warn: { bg: 'rgba(255,152,0,0.15)', color: '#ff9800' },
  error: { bg: 'rgba(229,57,53,0.15)', color: '#e53935' },
  info: { bg: 'rgba(41,182,246,0.15)', color: '#29b6f6' },
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
      <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-1">{label}</div>
      <div className="text-2xl font-black" style={{ color: color ?? '#fff' }}>{value}</div>
      {sub && <div className="text-[11px] text-[rgba(255,255,255,0.38)] mt-0.5">{sub}</div>}
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

const versionDist = [
  { version: 'v2.4.1', devices: 44, pct: '93.6%', status: 'ok' as const },
  { version: 'v2.4.0', devices: 2, pct: '4.3%', status: 'warn' as const },
  { version: 'v2.3.9', devices: 1, pct: '2.1%', status: 'error' as const },
];

const pipeline = [
  { stage: 'Build', status: 'ok' as const, ts: '2026-02-27 07:14', note: 'Webpack 5.91 · 2m 14s' },
  { stage: 'Test', status: 'ok' as const, ts: '2026-02-27 07:16', note: '214 tests passed · 0 failed' },
  { stage: 'Stage', status: 'ok' as const, ts: '2026-02-27 07:19', note: 'Staging smoke tests passed' },
  { stage: 'Deploy', status: 'ok' as const, ts: '2026-02-27 07:23', note: 'CDN invalidation complete' },
  { stage: 'Verify', status: 'ok' as const, ts: '2026-02-27 07:25', note: '44/47 devices confirmed' },
];

const deviceUpdates = [
  { id: 'DEV-001', version: 'v2.4.1', lastSeen: '2min ago', updateStatus: 'ok' as const },
  { id: 'DEV-007', version: 'v2.4.1', lastSeen: '4min ago', updateStatus: 'ok' as const },
  { id: 'DEV-012', version: 'v2.4.0', lastSeen: '18min ago', updateStatus: 'warn' as const },
  { id: 'DEV-019', version: 'v2.4.0', lastSeen: '1hr ago', updateStatus: 'warn' as const },
  { id: 'DEV-031', version: 'v2.3.9', lastSeen: '3hr ago', updateStatus: 'error' as const },
];

const featureFlags = [
  { name: 'Offline Mode', enabled: true },
  { name: 'Push Notifications', enabled: true },
  { name: 'Background Sync', enabled: true },
  { name: 'Biometric Auth', enabled: false },
  { name: 'Dark Mode Auto', enabled: true },
  { name: 'GPS Tracking', enabled: true },
];

export default function DeploymentPage() {
  return (
    <div className="p-5 min-h-screen bg-[#07090d]">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="pb-4 mb-6 border-b border-[rgba(255,255,255,0.08)]">
        <div className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: DOMAIN_COLOR }}>
          9 · PWA &amp; MOBILE
        </div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">PWA Deployment Monitor</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-1">Release pipeline · Version distribution · Device update tracking</p>
      </motion.div>

      {/* MODULE 1 — Deployment Status */}
      <motion.div custom={0} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 1" title="Deployment Status" sub="Current release health across fleet" />
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <StatCard label="Current Version" value="v2.4.1" color={DOMAIN_COLOR} />
          <StatCard label="Last Deploy" value="2h ago" color="rgba(255,255,255,0.55)" />
          <StatCard label="Total Devices" value={47} color="rgba(255,255,255,0.7)" />
          <StatCard label="Updated" value={44} color="#4caf50" />
          <StatCard label="Pending" value={3} color="#ff9800" />
          <StatCard label="Deploy Success" value="99.1%" color="#22d3ee" />
        </div>
      </motion.div>

      {/* MODULE 2 — Version Distribution */}
      <motion.div custom={1} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 2" title="Version Distribution" sub="App version spread across device fleet" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[rgba(255,255,255,0.38)] border-b border-[rgba(255,255,255,0.06)]">
                  {['Version', 'Device Count', 'Percentage', 'Status'].map(h => (
                    <th key={h} className="text-left pb-2 pr-6 font-bold uppercase tracking-widest text-[10px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {versionDist.map((row, i) => (
                  <tr key={i} className="border-b border-[rgba(255,255,255,0.04)] last:border-0">
                    <td className="py-3 pr-6 text-white font-bold font-mono">{row.version}</td>
                    <td className="py-3 pr-6 text-[rgba(255,255,255,0.7)]">{row.devices} devices</td>
                    <td className="py-3 pr-6">
                      <div className="flex items-center gap-3">
                        <div className="w-24">
                          <ProgressBar value={parseFloat(row.pct)} max={100} color={badgeColors[row.status].color} />
                        </div>
                        <span className="text-[rgba(255,255,255,0.55)]">{row.pct}</span>
                      </div>
                    </td>
                    <td className="py-3"><Badge label={row.status === 'ok' ? 'Current' : row.status === 'warn' ? 'Outdated' : 'Legacy'} status={row.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 3 — Deployment Pipeline */}
      <motion.div custom={2} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 3" title="Deployment Pipeline" sub="Last release — v2.4.1 · 2026-02-27" />
        <Panel>
          <div className="relative">
            {/* connector line */}
            <div className="absolute left-[15px] top-4 bottom-4 w-px bg-[rgba(255,255,255,0.08)]" />
            <div className="space-y-0">
              {pipeline.map((step, i) => (
                <div key={i} className="flex items-start gap-4 py-3 border-b border-[rgba(255,255,255,0.04)] last:border-0">
                  <div
                    className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-[10px] font-black border-2 z-10"
                    style={{
                      background: '#0f1720',
                      borderColor: badgeColors[step.status].color,
                      color: badgeColors[step.status].color,
                    }}
                  >
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-0.5">
                      <span className="text-xs font-bold text-white uppercase tracking-widest">{step.stage}</span>
                      <Badge label={step.status === 'ok' ? 'Passed' : step.status === 'warn' ? 'Warning' : 'Failed'} status={step.status} />
                    </div>
                    <div className="text-[10px] text-[rgba(255,255,255,0.38)]">{step.note}</div>
                    <div className="text-[10px] text-[rgba(255,255,255,0.25)] font-mono mt-0.5">{step.ts}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 4 — Device Update Status */}
      <motion.div custom={3} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 4" title="Device Update Status" sub="Per-device update rollout tracking" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[rgba(255,255,255,0.38)] border-b border-[rgba(255,255,255,0.06)]">
                  {['Device ID', 'Version', 'Last Seen', 'Update Status'].map(h => (
                    <th key={h} className="text-left pb-2 pr-6 font-bold uppercase tracking-widest text-[10px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {deviceUpdates.map((d, i) => (
                  <tr key={i} className="border-b border-[rgba(255,255,255,0.04)] last:border-0">
                    <td className="py-2.5 pr-6 text-white font-mono font-bold">{d.id}</td>
                    <td className="py-2.5 pr-6 text-[rgba(255,255,255,0.7)] font-mono">{d.version}</td>
                    <td className="py-2.5 pr-6 text-[rgba(255,255,255,0.55)]">{d.lastSeen}</td>
                    <td className="py-2.5">
                      <Badge
                        label={d.updateStatus === 'ok' ? 'Up to date' : d.updateStatus === 'warn' ? 'Update available' : 'Needs update'}
                        status={d.updateStatus}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 5 — PWA Feature Flags */}
      <motion.div custom={4} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 5" title="PWA Feature Flags" sub="Runtime feature toggle state" />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {featureFlags.map((flag, i) => (
            <Panel key={i} className="flex items-center justify-between">
              <span className="text-xs font-medium text-[rgba(255,255,255,0.7)]">{flag.name}</span>
              <Badge label={flag.enabled ? 'Enabled' : 'Disabled'} status={flag.enabled ? 'ok' : 'error'} />
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 6 — CDN & Cache Health */}
      <motion.div custom={5} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
        <SectionHeader number="MOD 6" title="CDN &amp; Cache Health" sub="Edge delivery and bundle performance" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <StatCard label="Cache Hit Rate" value="94%" sub="Last 24h avg" color="#4caf50" />
          <StatCard label="CDN Latency" value="18ms" sub="P50 global avg" color={DOMAIN_COLOR} />
          <StatCard label="Bundle Size" value="2.1 MB" sub="Gzipped: 618 KB" color="#22d3ee" />
        </div>
      </motion.div>

      <Link href="/founder" className="text-xs text-[rgba(255,107,26,0.6)] hover:text-[#ff6b1a] transition-colors">
        &larr; Back to Founder Command OS
      </Link>
    </div>
  );
}
