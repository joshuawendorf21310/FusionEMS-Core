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

const scheduleRows = [
  { unit: 'M-01', lead: 'J. Martinez', partner: 'T. Williams', start: '06:00', end: '18:00', status: 'active' },
  { unit: 'M-03', lead: 'R. Chen', partner: 'A. Patel', start: '06:00', end: '18:00', status: 'active' },
  { unit: 'M-07', lead: 'D. Thompson', partner: 'S. Nguyen', start: '06:00', end: '18:00', status: 'active' },
  { unit: 'M-09', lead: 'K. Okafor', partner: 'L. Rivera', start: '12:00', end: '00:00', status: 'standby' },
  { unit: 'M-12', lead: 'P. Vasquez', partner: 'M. Brooks', start: '12:00', end: '00:00', status: 'active' },
  { unit: 'M-15', lead: 'E. Hoffman', partner: 'C. Tanaka', start: '18:00', end: '06:00', status: 'standby' },
  { unit: 'M-18', lead: 'N. Davis', partner: 'TBD', start: '18:00', end: '06:00', status: 'open' },
  { unit: 'M-21', lead: 'B. Reyes', partner: 'TBD', start: '00:00', end: '12:00', status: 'open' },
];

const schedStatusMap: Record<string, 'ok' | 'warn' | 'error' | 'info'> = {
  active: 'ok',
  standby: 'info',
  open: 'error',
};

const complianceBars = [
  { label: 'Minimum Staffing', value: 100, max: 100, color: '#4caf50', display: '100%' },
  { label: 'Credential Compliance', value: 97, max: 100, color: DOMAIN_COLOR, display: '97%' },
  { label: 'Fatigue Score Avg', value: 2.1, max: 10, color: '#ff9800', display: '2.1 / 10' },
  { label: 'Coverage Rate', value: 93, max: 100, color: '#22d3ee', display: '93%' },
];

const openShifts = [
  { station: 'Station 4 — North', time: '18:00 – 06:00', cert: 'Paramedic (ALS)', id: 1 },
  { station: 'Station 7 — Downtown', time: '00:00 – 12:00', cert: 'AEMT', id: 2 },
];

const fatigueRoster = [
  { name: 'T. Williams', kss: 3, hours: 10 },
  { name: 'J. Martinez', kss: 2, hours: 9 },
  { name: 'D. Thompson', kss: 5, hours: 12 },
  { name: 'A. Patel', kss: 4, hours: 11 },
  { name: 'K. Okafor', kss: 7, hours: 14 },
  { name: 'P. Vasquez', kss: 8, hours: 16 },
];

const kssColor = (k: number) => k < 4 ? '#4caf50' : k <= 6 ? '#ff9800' : '#e53935';
const kssBadge = (k: number): 'ok' | 'warn' | 'error' => k < 4 ? 'ok' : k <= 6 ? 'warn' : 'error';

const appFeatures = [
  { name: 'Mobile Clock-In', enabled: true },
  { name: 'Shift Swap Requests', enabled: true },
  { name: 'OT Notifications', enabled: true },
  { name: 'Coverage Alerts', enabled: true },
  { name: 'Calendar Sync', enabled: true },
  { name: 'Crew Messaging', enabled: true },
];

export default function SchedulingPage() {
  return (
    <div className="p-5 min-h-screen bg-[#07090d]">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="pb-4 mb-6 border-b border-[rgba(255,255,255,0.08)]">
        <div className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: DOMAIN_COLOR }}>
          9 · PWA &amp; MOBILE
        </div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">Mobile Scheduling Interface</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-1">Shift management · Coverage monitoring · Fatigue tracking</p>
      </motion.div>

      {/* MODULE 1 — Shift Coverage Overview */}
      <motion.div custom={0} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 1" title="Shift Coverage Overview" sub="Current operational staffing state" />
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatCard label="Current Shifts" value={8} color={DOMAIN_COLOR} />
          <StatCard label="Covered Units" value={12} color="#4caf50" />
          <StatCard label="Open Shifts" value={2} color="#e53935" />
          <StatCard label="On-Call" value={4} color="#ff9800" />
          <StatCard label="Overtime Hours" value={14} color="#a855f7" sub="Today" />
        </div>
      </motion.div>

      {/* MODULE 2 — Today's Schedule Table */}
      <motion.div custom={1} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 2" title="Today's Schedule" sub="Active and upcoming unit assignments" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[rgba(255,255,255,0.38)] border-b border-[rgba(255,255,255,0.06)]">
                  {['Unit', 'Crew Lead', 'Partner', 'Shift Start', 'Shift End', 'Status'].map(h => (
                    <th key={h} className="text-left pb-2 pr-4 font-bold uppercase tracking-widest text-[10px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {scheduleRows.map((row, i) => (
                  <tr key={i} className="border-b border-[rgba(255,255,255,0.04)] last:border-0">
                    <td className="py-2.5 pr-4 text-white font-bold">{row.unit}</td>
                    <td className="py-2.5 pr-4 text-[rgba(255,255,255,0.7)]">{row.lead}</td>
                    <td className="py-2.5 pr-4 text-[rgba(255,255,255,0.55)]">{row.partner}</td>
                    <td className="py-2.5 pr-4 text-[rgba(255,255,255,0.55)] font-mono">{row.start}</td>
                    <td className="py-2.5 pr-4 text-[rgba(255,255,255,0.55)] font-mono">{row.end}</td>
                    <td className="py-2.5"><Badge label={row.status} status={schedStatusMap[row.status]} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 3 — Schedule Compliance */}
      <motion.div custom={2} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 3" title="Schedule Compliance" sub="Regulatory and operational benchmarks" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {complianceBars.map((item, i) => (
            <Panel key={i}>
              <div className="flex justify-between items-center mb-2">
                <span className="text-[11px] font-bold text-white uppercase tracking-widest">{item.label}</span>
                <span className="text-[11px] font-bold" style={{ color: item.color }}>{item.display}</span>
              </div>
              <ProgressBar value={item.value} max={item.max} color={item.color} />
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 4 — Open Shift Alerts */}
      <motion.div custom={3} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 4" title="Open Shift Alerts" sub="Unfilled shifts requiring immediate coverage" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {openShifts.map((shift) => (
            <Panel key={shift.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs font-bold text-white mb-1">{shift.station}</div>
                  <div className="text-[11px] text-[rgba(255,255,255,0.55)] mb-1 font-mono">{shift.time}</div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-[rgba(255,255,255,0.38)] uppercase tracking-widest">Required:</span>
                    <Badge label={shift.cert} status="info" />
                  </div>
                </div>
                <button
                  className="text-[10px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-sm border shrink-0 transition-colors"
                  style={{ borderColor: '#4caf50', color: '#4caf50', background: 'rgba(76,175,80,0.08)' }}
                  onClick={() => {}}
                >
                  Fill Shift
                </button>
              </div>
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 5 — Fatigue Risk Monitor */}
      <motion.div custom={4} variants={fadeUp} initial="hidden" animate="visible" className="mb-6">
        <SectionHeader number="MOD 5" title="Fatigue Risk Monitor" sub="KSS fatigue scoring — green &lt;4 | yellow 4-6 | red &gt;6" />
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {fatigueRoster.map((crew, i) => (
            <Panel key={i}>
              <div className="flex justify-between items-start mb-2">
                <div className="text-xs font-bold text-white">{crew.name}</div>
                <Badge label={`KSS ${crew.kss}`} status={kssBadge(crew.kss)} />
              </div>
              <div className="mb-2">
                <ProgressBar value={crew.kss} max={10} color={kssColor(crew.kss)} />
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[rgba(255,255,255,0.38)]">Hours on duty</span>
                <span style={{ color: crew.hours >= 14 ? '#e53935' : 'rgba(255,255,255,0.55)' }} className="font-bold">{crew.hours}h</span>
              </div>
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 6 — Scheduling App Features */}
      <motion.div custom={5} variants={fadeUp} initial="hidden" animate="visible" className="mb-8">
        <SectionHeader number="MOD 6" title="Scheduling App Features" sub="Mobile feature availability status" />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {appFeatures.map((feat, i) => (
            <Panel key={i} className="flex items-center justify-between">
              <span className="text-xs font-medium text-[rgba(255,255,255,0.7)]">{feat.name}</span>
              <Badge label={feat.enabled ? 'Enabled' : 'Disabled'} status={feat.enabled ? 'ok' : 'error'} />
            </Panel>
          ))}
        </div>
      </motion.div>

      <Link href="/founder" className="text-xs text-[rgba(255,107,26,0.6)] hover:text-[#ff6b1a] transition-colors">
        &larr; Back to Founder Command OS
      </Link>
    </div>
  );
}
