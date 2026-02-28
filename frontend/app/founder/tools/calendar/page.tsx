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
  const c = { ok: '#4caf50', warn: '#ff9800', error: '#e53935', info: '#29b6f6' };
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-semibold uppercase tracking-wider border"
      style={{ borderColor: `${c[status]}40`, color: c[status], background: `${c[status]}12` }}
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

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const TODAY_INDEX = 0; // Mon is today for demo

const WEEK_EVENTS: Record<number, string[]> = {
  0: ['Agency Demo Call 2pm'],
  1: ['Stripe billing cycle'],
  2: [],
  3: ['NEMSIS deadline TX'],
  4: ['Team sync 10am'],
  5: [],
  6: [],
};

const WEEK_DATES = [27, 28, 29, 30, 31, 1, 2];

const UPCOMING_EVENTS = [
  { date: 'Feb 3', event: 'Agency B onboarding call', category: 'Sales', priority: 'high' as const },
  { date: 'Feb 5', event: 'Stripe invoice cycle', category: 'Billing', priority: 'warn' as const },
  { date: 'Feb 7', event: 'NEMSIS submission deadline (TX)', category: 'Compliance', priority: 'high' as const },
  { date: 'Feb 10', event: 'Credential expiry: Paramedic-04', category: 'Compliance', priority: 'high' as const },
  { date: 'Feb 12', event: 'Q1 investor update', category: 'Executive', priority: 'warn' as const },
  { date: 'Feb 14', event: 'Platform audit review', category: 'Compliance', priority: 'high' as const },
  { date: 'Feb 18', event: 'Agency C renewal', category: 'Revenue', priority: 'warn' as const },
  { date: 'Feb 20', event: 'State API maintenance window', category: 'Infra', priority: 'info' as const },
  { date: 'Feb 25', event: 'Board meeting prep', category: 'Executive', priority: 'high' as const },
  { date: 'Mar 1', event: 'Q1 compliance report', category: 'Compliance', priority: 'warn' as const },
];

const RECURRING = [
  { freq: 'Daily', label: 'AI briefing', time: '07:00 UTC', note: 'auto-generated' },
  { freq: 'Weekly', label: 'Export health summary', time: 'Mon 08:00', note: 'auto-sent email' },
  { freq: 'Monthly', label: 'Stripe billing cycle', time: '1st', note: 'auto-processed' },
  { freq: 'Monthly', label: 'AR aging report', time: '5th', note: 'auto-generated' },
  { freq: 'Quarterly', label: 'Compliance review', time: '—', note: 'manual reminder' },
];

const COMPLIANCE_DEADLINES = [
  { label: 'NEMSIS TX submission', days: 5, status: 'warn' as const },
  { label: 'DEA renewal (Provider-02)', days: 28, status: 'ok' as const },
  { label: 'HIPAA audit window', days: 45, status: 'ok' as const },
];

export default function FounderCalendarPage() {
  const [selectedDay, setSelectedDay] = useState<number>(TODAY_INDEX);
  const [form, setForm] = useState({ title: '', date: '', category: 'Compliance', priority: 'high' });

  const priorityStatus = (p: string): 'ok' | 'warn' | 'error' | 'info' => {
    if (p === 'high') return 'error';
    if (p === 'warn') return 'warn';
    if (p === 'low') return 'info';
    return 'warn';
  };

  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-6 space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-bold text-orange-dim font-mono tracking-widest uppercase">
            MODULE 11 · FOUNDER TOOLS
          </span>
          <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-orange transition-colors">
            ← Back to Founder OS
          </Link>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary" style={{ textShadow: '0 0 24px rgba(255,107,26,0.3)' }}>
          Founder Calendar
        </h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Meetings · deadlines · billing cycles · compliance events</p>
      </motion.div>

      {/* MODULE 1 — This Week */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Panel>
          <SectionHeader number="1" title="This Week" sub="Mon 27 Jan – Sun 2 Feb" />
          <div className="grid grid-cols-7 gap-2">
            {DAYS.map((day, i) => (
              <button
                key={day}
                onClick={() => setSelectedDay(i)}
                className="flex flex-col items-center p-2 rounded-sm transition-all"
                style={{
                  background: selectedDay === i ? 'rgba(255,107,26,0.1)' : 'rgba(255,255,255,0.02)',
                  border: i === TODAY_INDEX
                    ? '1px solid #ff6b1a'
                    : selectedDay === i
                    ? '1px solid rgba(255,107,26,0.4)'
                    : '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <span className="text-[10px] font-semibold text-[rgba(255,255,255,0.4)] uppercase tracking-widest">{day}</span>
                <span
                  className="text-lg font-bold mt-0.5"
                  style={{ color: i === TODAY_INDEX ? '#ff6b1a' : 'rgba(255,255,255,0.85)' }}
                >
                  {WEEK_DATES[i]}
                </span>
                <div className="mt-1 flex flex-col items-center gap-0.5 w-full">
                  {WEEK_EVENTS[i].length > 0 ? (
                    <>
                      <span className="w-1.5 h-1.5 rounded-full bg-orange" />
                      <span className="text-[8px] text-[rgba(255,255,255,0.45)] text-center leading-tight mt-0.5 line-clamp-2">
                        {WEEK_EVENTS[i][0]}
                      </span>
                    </>
                  ) : (
                    <span className="text-[9px] text-[rgba(255,255,255,0.2)]">clear</span>
                  )}
                </div>
              </button>
            ))}
          </div>
          {WEEK_EVENTS[selectedDay].length > 0 && (
            <div className="mt-3 p-2 bg-[rgba(255,107,26,0.06)] border border-[rgba(255,107,26,0.15)] rounded-sm">
              <span className="text-[10px] text-orange font-semibold">{DAYS[selectedDay]} selected: </span>
              <span className="text-[11px] text-[rgba(255,255,255,0.7)]">{WEEK_EVENTS[selectedDay].join(', ')}</span>
            </div>
          )}
        </Panel>
      </motion.div>

      {/* MODULE 2 — Upcoming Events */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <Panel>
          <SectionHeader number="2" title="Upcoming Events" />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border-subtle">
                  {['Date', 'Event', 'Category', 'Priority'].map((h) => (
                    <th key={h} className="text-left py-1.5 px-2 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {UPCOMING_EVENTS.map((ev, i) => (
                  <tr key={i} className="border-b border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.02)]">
                    <td className="py-2 px-2 font-mono text-[rgba(255,107,26,0.8)]">{ev.date}</td>
                    <td className="py-2 px-2 text-[rgba(255,255,255,0.75)]">{ev.event}</td>
                    <td className="py-2 px-2 text-[rgba(255,255,255,0.45)]">{ev.category}</td>
                    <td className="py-2 px-2">
                      <Badge
                        label={ev.priority === 'warn' ? 'medium' : ev.priority === 'info' ? 'low' : ev.priority}
                        status={priorityStatus(ev.priority)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 3 — Add Event */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Panel>
          <SectionHeader number="3" title="Add Event" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Event Title</label>
              <input
                type="text"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Event title"
                className="bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-xs text-text-primary px-3 py-2 rounded-sm outline-none focus:border-orange placeholder:text-[rgba(255,255,255,0.2)]"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Date</label>
              <input
                type="date"
                value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
                className="bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-xs text-text-primary px-3 py-2 rounded-sm outline-none focus:border-orange"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Category</label>
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-xs text-text-primary px-3 py-2 rounded-sm outline-none focus:border-orange"
              >
                {['Compliance', 'Sales', 'Billing', 'Executive', 'Infra'].map((c) => (
                  <option key={c} value={c} className="bg-bg-panel">{c}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Priority</label>
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
                className="bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-xs text-text-primary px-3 py-2 rounded-sm outline-none focus:border-orange"
              >
                {['high', 'medium', 'low'].map((p) => (
                  <option key={p} value={p} className="bg-bg-panel">{p}</option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                className="px-4 py-2 text-xs font-bold uppercase tracking-widest rounded-sm transition-all hover:brightness-110"
                style={{ background: '#ff6b1a', color: '#000' }}
                onClick={() => setForm({ title: '', date: '', category: 'Compliance', priority: 'high' })}
              >
                Add Event
              </button>
            </div>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 4 — Recurring Events */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <Panel>
          <SectionHeader number="4" title="Recurring Events" />
          <div className="space-y-2">
            {RECURRING.map((r, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-border-subtle last:border-0">
                <div className="flex items-center gap-3">
                  <span
                    className="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-sm"
                    style={{ background: 'rgba(255,107,26,0.12)', color: 'var(--q-orange)', border: '1px solid rgba(255,107,26,0.25)' }}
                  >
                    {r.freq}
                  </span>
                  <span className="text-xs text-[rgba(255,255,255,0.75)]">{r.label}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono text-[rgba(255,255,255,0.35)]">{r.time}</span>
                  <span className="text-[10px] text-[rgba(255,255,255,0.3)] italic">{r.note}</span>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 5 — Compliance Deadlines */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
        <Panel>
          <SectionHeader number="5" title="Compliance Deadlines" sub="upcoming" />
          <div className="space-y-3">
            {COMPLIANCE_DEADLINES.map((cd, i) => (
              <div key={i} className="flex items-center justify-between py-2 px-3 rounded-sm" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <span className="text-xs text-[rgba(255,255,255,0.75)]">{cd.label}</span>
                <div className="flex items-center gap-3">
                  <span className="text-[11px] font-mono text-[rgba(255,255,255,0.5)]">{cd.days} days</span>
                  <Badge label={`${cd.days}d`} status={cd.status} />
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </motion.div>

      <div className="pt-2">
        <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.35)] hover:text-orange transition-colors">
          ← Back to Founder OS
        </Link>
      </div>
    </div>
  );
}
