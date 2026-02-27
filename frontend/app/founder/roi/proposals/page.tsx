'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE ?? '';

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="border-b border-[rgba(255,255,255,0.06)] pb-2 mb-4">
      <div className="flex items-baseline gap-3">
        <span className="text-[10px] font-bold text-[rgba(255,107,26,0.6)] font-mono">MODULE {number}</span>
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
      className={`bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4 ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div
      className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4"
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      <div className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-1">{label}</div>
      <div className="text-xl font-bold" style={{ color: color ?? '#fff' }}>{value}</div>
      {sub && <div className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">{sub}</div>}
    </div>
  );
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-1.5 bg-[rgba(255,255,255,0.06)] rounded-full overflow-hidden">
      <motion.div
        className="h-full rounded-full"
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.8 }}
      />
    </div>
  );
}

const ACTIVE_PROPOSALS = [
  { agency: 'Agency B', sent: 'Jan 22', value: '$34,560', statusLabel: 'Viewed', statusKey: 'info' as const, days: 8, action: 'Follow Up' },
  { agency: 'Agency C', sent: 'Jan 20', value: '$17,280', statusLabel: 'Sent', statusKey: 'warn' as const, days: 10, action: 'Resend' },
  { agency: 'Agency D', sent: 'Jan 15', value: '$17,280', statusLabel: 'In Negotiation', statusKey: 'info' as const, days: 15, action: 'Schedule Call' },
  { agency: 'Agency E', sent: 'Jan 10', value: '$8,640', statusLabel: 'Sent', statusKey: 'warn' as const, days: 20, action: 'Send Reminder' },
  { agency: 'Agency F', sent: 'Jan 5', value: '$17,280', statusLabel: 'Viewed', statusKey: 'info' as const, days: 25, action: 'Follow Up' },
  { agency: 'Agency G', sent: 'Jan 2', value: '$8,640', statusLabel: 'Declined', statusKey: 'error' as const, days: 28, action: 'Archive' },
];

const ACCEPTED_PROPOSALS = [
  { agency: 'Agency A', date: 'Oct 2023', value: '$17,280', closed: 'Converted', mrr: '$1,440' },
  { agency: 'Agency B (pilot)', date: 'Aug 2023', value: '$8,640', closed: 'Converted', mrr: '$720' },
  { agency: 'Agency C', date: 'Dec 2023', value: '$8,640', closed: 'Converted', mrr: '$720' },
  { agency: 'Agency D', date: 'Jan 2024', value: '$17,280', closed: 'Converted', mrr: '$1,440' },
];

const FOLLOW_UP_QUEUE = [
  { agency: 'Agency B', sent: 'Jan 22', lastContact: 'Jan 24', value: '$34,560', status: 'Viewed' },
  { agency: 'Agency E', sent: 'Jan 10', lastContact: 'Jan 12', value: '$8,640', status: 'Sent' },
  { agency: 'Agency F', sent: 'Jan 5', lastContact: 'Jan 8', value: '$17,280', status: 'Viewed' },
];

const ALL_FILTERS = ['All', 'Open', 'Accepted', 'Declined'] as const;
type FilterType = typeof ALL_FILTERS[number];

export default function ProposalTrackerPage() {
  const [filter, setFilter] = useState<FilterType>('All');
  const [newAgency, setNewAgency] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newVolume, setNewVolume] = useState('');

  return (
    <div className="min-h-screen bg-[#080e14] text-white p-6 space-y-6">
      {/* Page Header */}
      <div className="border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold tracking-widest font-mono mb-1" style={{ color: 'rgba(255,152,0,0.6)' }}>
              MODULE 8 · ROI &amp; SALES
            </p>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: '#ff9800' }}>Proposal Tracker</h1>
            <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Track sent proposals · follow up · conversion analytics</p>
          </div>
          <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-[#ff9800] transition-colors font-mono">
            ← Back to Founder OS
          </Link>
        </div>
      </div>

      {/* MODULE 1 — Proposal Stats */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Total Sent (all time)" value={18} color="#fff" />
        <StatCard label="Open (awaiting)" value={4} color="#ff9800" />
        <StatCard label="Accepted" value={12} color="#4caf50" />
        <StatCard label="Declined" value={2} color="#e53935" />
      </div>

      {/* MODULE 2 — Active Proposals */}
      <Panel>
        <SectionHeader number="2" title="Active Proposals" sub="6 proposals in flight" />
        <div className="flex gap-2 mb-3">
          {ALL_FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="text-[10px] font-semibold px-3 py-1 rounded-sm transition-all"
              style={{
                background: filter === f ? '#ff980018' : 'transparent',
                color: filter === f ? '#ff9800' : 'rgba(255,255,255,0.4)',
                border: `1px solid ${filter === f ? '#ff980040' : 'rgba(255,255,255,0.08)'}`,
              }}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.06)]">
                {['Agency', 'Sent Date', 'Value/yr', 'Status', 'Days Open', 'Action'].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ACTIVE_PROPOSALS
                .filter((p) =>
                  filter === 'All' ? true :
                  filter === 'Open' ? (p.statusKey === 'info' || p.statusKey === 'warn') :
                  filter === 'Accepted' ? false :
                  filter === 'Declined' ? p.statusKey === 'error' : true
                )
                .map((p, i) => (
                  <tr key={i} className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)]">
                    <td className="py-2 pr-4 font-semibold text-[rgba(255,255,255,0.8)]">{p.agency}</td>
                    <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{p.sent}</td>
                    <td className="py-2 pr-4 font-mono text-[#ff9800]">{p.value}</td>
                    <td className="py-2 pr-4"><Badge label={p.statusLabel} status={p.statusKey} /></td>
                    <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{p.days} days</td>
                    <td className="py-2 pr-4">
                      <button
                        className="text-[10px] font-semibold px-2 py-0.5 rounded-sm"
                        style={{
                          background: p.statusKey === 'error' ? '#e5393510' : '#ff980010',
                          color: p.statusKey === 'error' ? '#e53935' : '#ff9800',
                          border: `1px solid ${p.statusKey === 'error' ? '#e5393525' : '#ff980025'}`,
                        }}
                      >
                        {p.action}
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* MODULE 3 — Accepted Proposals History */}
      <Panel>
        <SectionHeader number="3" title="Accepted Proposals History" sub="4 converted deals" />
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.06)]">
                {['Agency', 'Date', 'Value/yr', 'Closed', 'MRR'].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ACCEPTED_PROPOSALS.map((p, i) => (
                <tr key={i} className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)]">
                  <td className="py-2 pr-4 font-semibold text-[rgba(255,255,255,0.8)]">{p.agency}</td>
                  <td className="py-2 pr-4 text-[rgba(255,255,255,0.5)]">{p.date}</td>
                  <td className="py-2 pr-4 font-mono text-[rgba(255,255,255,0.6)]">{p.value}</td>
                  <td className="py-2 pr-4"><Badge label={p.closed} status="ok" /></td>
                  <td className="py-2 pr-4 font-mono font-bold text-[#4caf50]">{p.mrr}/mo</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* MODULE 4 — Proposal Analytics */}
      <Panel>
        <SectionHeader number="4" title="Proposal Analytics" sub="Conversion performance" />
        <div className="grid grid-cols-4 gap-3">
          <StatCard label="Avg Time to View" value="1.8 days" color="#29b6f6" />
          <StatCard label="Avg Time to Decision" value="12.4 days" color="#ff9800" />
          <StatCard label="Accept Rate" value="66.7%" color="#4caf50" />
          <StatCard label="Avg Deal Value" value="$19,200/yr" color="#fff" />
        </div>
        <div className="mt-4 space-y-3">
          <div>
            <div className="flex justify-between mb-1.5">
              <span className="text-[11px] text-[rgba(255,255,255,0.6)]">Accept Rate</span>
              <span className="text-[11px] font-bold text-[#4caf50]">66.7%</span>
            </div>
            <ProgressBar value={66.7} max={100} color="#4caf50" />
          </div>
          <div>
            <div className="flex justify-between mb-1.5">
              <span className="text-[11px] text-[rgba(255,255,255,0.6)]">Pipeline Coverage (ARR target)</span>
              <span className="text-[11px] font-bold text-[#ff9800]">43%</span>
            </div>
            <ProgressBar value={43} max={100} color="#ff9800" />
          </div>
        </div>
      </Panel>

      {/* MODULE 5 — Follow-Up Queue */}
      <Panel>
        <SectionHeader number="5" title="Follow-Up Queue" sub="3 proposals flagged" />
        <div className="space-y-2">
          {FOLLOW_UP_QUEUE.map((f, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-[#0a1219] border border-[rgba(255,152,0,0.1)] rounded-sm">
              <div>
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-[12px] font-semibold text-[rgba(255,255,255,0.85)]">{f.agency}</span>
                  <Badge label={f.status} status="warn" />
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-[rgba(255,255,255,0.35)]">Sent {f.sent}</span>
                  <span className="text-[10px] text-[rgba(255,255,255,0.35)]">·</span>
                  <span className="text-[10px] text-[rgba(255,255,255,0.35)]">Last contact: {f.lastContact}</span>
                  <span className="text-[10px] font-mono text-[#ff9800]">{f.value}/yr</span>
                </div>
              </div>
              <button
                className="text-[10px] font-semibold px-3 py-1.5 rounded-sm"
                style={{ background: '#ff980018', color: '#ff9800', border: '1px solid #ff980030' }}
              >
                Send Email
              </button>
            </div>
          ))}
        </div>
      </Panel>

      {/* MODULE 6 — Create Proposal */}
      <Panel>
        <SectionHeader number="6" title="Create Proposal" sub="Quick ROI proposal generator" />
        <div className="grid grid-cols-3 gap-3 mb-3">
          <div>
            <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Agency Name</label>
            <input
              value={newAgency}
              onChange={(e) => setNewAgency(e.target.value)}
              placeholder="Agency H"
              className="w-full bg-[#0a1219] border border-[rgba(255,255,255,0.08)] text-[11px] text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff980040]"
            />
          </div>
          <div>
            <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Contact Email</label>
            <input
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder="contact@agencyh.com"
              className="w-full bg-[#0a1219] border border-[rgba(255,255,255,0.08)] text-[11px] text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff980040]"
            />
          </div>
          <div>
            <label className="text-[10px] text-[rgba(255,255,255,0.4)] block mb-1">Monthly Call Volume</label>
            <input
              type="number"
              value={newVolume}
              onChange={(e) => setNewVolume(e.target.value)}
              placeholder="200"
              className="w-full bg-[#0a1219] border border-[rgba(255,255,255,0.08)] text-[11px] text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff980040]"
            />
          </div>
        </div>
        <button
          disabled={!newAgency || !newEmail}
          className="text-[11px] font-bold px-6 py-2.5 rounded-sm transition-all disabled:opacity-30 hover:opacity-90"
          style={{ background: '#ff9800', color: '#000' }}
        >
          Generate ROI Proposal
        </button>
      </Panel>
    </div>
  );
}
