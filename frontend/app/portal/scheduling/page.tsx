'use client';

import React, { useState } from 'react';

type SchedTab = 'calendar' | 'requests' | 'coverage' | 'ai_drafts';

const TABS: { id: SchedTab; label: string }[] = [
  { id: 'calendar', label: 'Shift Calendar' },
  { id: 'requests', label: 'Requests' },
  { id: 'coverage', label: 'Coverage' },
  { id: 'ai_drafts', label: 'AI Drafts' },
];

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const HOURS = Array.from({ length: 16 }, (_, i) => `${String(i + 6).padStart(2, '0')}:00`);

type ViewMode = 'day' | 'week' | 'month';

function StatCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: string }) {
  return (
    <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm px-4 py-3">
      <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-1">{label}</div>
      <div className="text-lg font-bold" style={{ color: accent ?? 'white' }}>{value}</div>
      {sub && <div className="text-[10px] text-[rgba(255,255,255,0.35)] mt-0.5">{sub}</div>}
    </div>
  );
}

function WeekView({ weekOffset }: { weekOffset: number }) {
  const today = new Date();
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay() + weekOffset * 7);

  return (
    <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
      <div className="grid grid-cols-8 border-b border-border-subtle">
        <div className="px-3 py-2 text-[10px] text-[rgba(255,255,255,0.3)]">Time</div>
        {DAYS.map((day, i) => {
          const d = new Date(startOfWeek);
          d.setDate(startOfWeek.getDate() + i);
          const isToday = d.toDateString() === today.toDateString();
          return (
            <div key={day} className={`px-3 py-2 text-center border-l border-[rgba(255,255,255,0.05)] ${isToday ? 'bg-[rgba(255,107,26,0.06)]' : ''}`}>
              <div className={`text-[10px] uppercase tracking-wider ${isToday ? 'text-orange' : 'text-[rgba(255,255,255,0.35)]'}`}>{day}</div>
              <div className={`text-sm font-bold mt-0.5 ${isToday ? 'text-orange' : 'text-[rgba(255,255,255,0.7)]'}`}>{d.getDate()}</div>
            </div>
          );
        })}
      </div>
      <div className="overflow-y-auto" style={{ maxHeight: 420 }}>
        {HOURS.map((hour) => (
          <div key={hour} className="grid grid-cols-8 border-b border-[rgba(255,255,255,0.03)] min-h-[40px]">
            <div className="px-3 py-1 text-[10px] text-[rgba(255,255,255,0.2)]">{hour}</div>
            {DAYS.map((day) => (
              <div
                key={day}
                className="border-l border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.02)] transition-colors cursor-pointer"
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function CalendarTab() {
  const [view, setView] = useState<ViewMode>('week');
  const [weekOffset, setWeekOffset] = useState(0);

  const today = new Date();
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay() + weekOffset * 7);
  const endOfWeek = new Date(startOfWeek);
  endOfWeek.setDate(startOfWeek.getDate() + 6);

  const fmt = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-5">
        <StatCard label="Shifts This Week" value="0" />
        <StatCard label="Crew Scheduled" value="0" />
        <StatCard label="Open Slots" value="0" accent="var(--color-status-warning)" />
        <StatCard label="Overtime Risk" value="0" accent="var(--color-brand-red)" sub="crew members" />
      </div>

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setWeekOffset((w) => w - 1)}
            className="h-7 w-7 flex items-center justify-center bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-[rgba(255,255,255,0.6)] hover:text-text-primary rounded-sm transition-colors"
          >
            ‹
          </button>
          <span className="text-xs font-medium text-text-primary min-w-[140px] text-center">
            {fmt(startOfWeek)} — {fmt(endOfWeek)}
          </span>
          <button
            onClick={() => setWeekOffset((w) => w + 1)}
            className="h-7 w-7 flex items-center justify-center bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-[rgba(255,255,255,0.6)] hover:text-text-primary rounded-sm transition-colors"
          >
            ›
          </button>
          <button
            onClick={() => setWeekOffset(0)}
            className="h-7 px-3 bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-[10px] text-[rgba(255,255,255,0.5)] hover:text-text-primary rounded-sm transition-colors"
          >
            Today
          </button>
        </div>
        <div className="flex items-center gap-2">
          {(['day', 'week', 'month'] as ViewMode[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm border transition-colors ${
                view === v
                  ? 'bg-[rgba(255,107,26,0.15)] border-[rgba(255,107,26,0.35)] text-orange'
                  : 'bg-[rgba(255,255,255,0.03)] border-border-DEFAULT text-[rgba(255,255,255,0.4)] hover:text-text-primary'
              }`}
            >
              {v}
            </button>
          ))}
          <button className="h-7 px-3 bg-[rgba(255,107,26,0.1)] border border-[rgba(255,107,26,0.25)] text-[10px] font-semibold uppercase tracking-wider text-orange hover:bg-[rgba(255,107,26,0.18)] transition-colors rounded-sm">
            + Add Shift
          </button>
        </div>
      </div>

      {view === 'week' && <WeekView weekOffset={weekOffset} />}
      {view !== 'week' && (
        <div className="flex items-center justify-center h-64 bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm text-xs text-[rgba(255,255,255,0.3)]">
          {view.charAt(0).toUpperCase() + view.slice(1)} view
        </div>
      )}
    </div>
  );
}

function RequestsTab() {
  const [filter, setFilter] = useState<'all' | 'swap' | 'timeoff' | 'trade'>('all');

  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-5">
        <StatCard label="Pending Requests" value="0" accent="var(--color-status-warning)" />
        <StatCard label="Swap Requests" value="0" />
        <StatCard label="Time Off" value="0" />
        <StatCard label="Trade Requests" value="0" />
      </div>

      <div className="flex gap-1 mb-4">
        {(['all', 'swap', 'timeoff', 'trade'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm border transition-colors ${
              filter === f
                ? 'bg-[rgba(255,107,26,0.15)] border-[rgba(255,107,26,0.35)] text-orange'
                : 'bg-[rgba(255,255,255,0.03)] border-border-DEFAULT text-[rgba(255,255,255,0.4)] hover:text-text-primary'
            }`}
          >
            {f === 'all' ? 'All' : f === 'timeoff' ? 'Time Off' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Crew Member</span><span>Type</span><span>Date / Shift</span><span>Reason</span><span>Submitted</span><span>Action</span>
        </div>
        <div className="flex flex-col items-center justify-center py-16">
          <div className="text-xs text-[rgba(255,255,255,0.3)]">No pending {filter === 'all' ? '' : filter} requests</div>
        </div>
      </div>
    </div>
  );
}

function CoverageTab() {
  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-5">
        <StatCard label="Coverage %" value="—" sub="this week" />
        <StatCard label="Uncovered Shifts" value="0" accent="var(--color-brand-red)" />
        <StatCard label="On-Call Available" value="0" accent="var(--color-status-active)" />
        <StatCard label="Fatigue Flags" value="0" accent="var(--color-status-warning)" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm p-4">
          <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-3">Coverage by Day</div>
          <div className="space-y-2">
            {DAYS.map((day) => (
              <div key={day} className="flex items-center gap-3">
                <span className="text-[10px] text-[rgba(255,255,255,0.4)] w-8">{day}</span>
                <div className="flex-1 h-5 bg-[rgba(255,255,255,0.04)] rounded-sm overflow-hidden">
                  <div className="h-full bg-[rgba(76,175,80,0.3)] rounded-sm" style={{ width: '0%' }} />
                </div>
                <span className="text-[10px] text-[rgba(255,255,255,0.3)] w-8 text-right">0%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm p-4">
          <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-3">Overtime & Fatigue Risk</div>
          <div className="flex flex-col items-center justify-center h-40 text-xs text-[rgba(255,255,255,0.3)]">
            No fatigue flags this week
          </div>
        </div>
      </div>
    </div>
  );
}

function AiDraftsTab() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-xs text-[rgba(255,255,255,0.6)] mb-0.5">AI-generated schedule drafts — review and approve before publishing</div>
          <div className="text-[10px] text-[rgba(255,255,255,0.3)]">Drafts generated by GPT-4o-mini require human approval. What-if simulation is CPU-only.</div>
        </div>
        <button className="h-7 px-3 bg-[rgba(255,107,26,0.1)] border border-[rgba(255,107,26,0.25)] text-[10px] font-semibold uppercase tracking-wider text-orange hover:bg-[rgba(255,107,26,0.18)] transition-colors rounded-sm">
          Generate Draft
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-5">
        <StatCard label="Pending Review" value="0" accent="var(--color-status-warning)" />
        <StatCard label="Approved This Week" value="0" accent="var(--color-status-active)" />
        <StatCard label="AI Draft Accuracy" value="—" />
      </div>

      <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden mb-4">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Draft ID</span><span>Horizon</span><span>Generated</span><span>Shifts</span><span>Status</span><span>Action</span>
        </div>
        <div className="flex flex-col items-center justify-center py-14">
          <div className="text-xs text-[rgba(255,255,255,0.3)]">No AI drafts — generate one to get started</div>
        </div>
      </div>

      <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm p-4">
        <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-2">What-If Simulation</div>
        <div className="text-xs text-[rgba(255,255,255,0.5)] mb-3">CPU-only scenario simulation — predict coverage impact before committing changes.</div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Remove 1 crew member', desc: 'See coverage drop' },
            { label: 'Add weekend shift', desc: 'See overtime impact' },
            { label: 'Shift start +2h', desc: 'See fatigue change' },
          ].map((scenario) => (
            <button
              key={scenario.label}
              className="text-left px-3 py-2.5 bg-[rgba(255,255,255,0.03)] border border-border-DEFAULT rounded-sm hover:border-[rgba(255,107,26,0.3)] transition-colors"
            >
              <div className="text-[11px] font-medium text-[rgba(255,255,255,0.8)] mb-0.5">{scenario.label}</div>
              <div className="text-[10px] text-[rgba(255,255,255,0.4)]">{scenario.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function SchedulingPage() {
  const [activeTab, setActiveTab] = useState<SchedTab>('calendar');

  const content: Record<SchedTab, React.ReactNode> = {
    calendar: <CalendarTab />,
    requests: <RequestsTab />,
    coverage: <CoverageTab />,
    ai_drafts: <AiDraftsTab />,
  };

  return (
    <div className="p-6 max-w-[1400px]">
      <div className="mb-6">
        <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-1">Agency Portal</div>
        <h1 className="text-xl font-bold text-text-primary">Scheduling</h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Shift calendar, swap/trade/time-off requests, coverage monitoring, and AI-assisted drafts</p>
      </div>

      <div className="flex gap-0 mb-6 border-b border-border-DEFAULT">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative px-4 py-2.5 text-xs font-medium transition-colors ${
              activeTab === tab.id ? 'text-text-primary' : 'text-[rgba(255,255,255,0.4)] hover:text-[rgba(255,255,255,0.7)]'
            }`}
          >
            {tab.label}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-orange" />
            )}
          </button>
        ))}
      </div>

      <div>{content[activeTab]}</div>
    </div>
  );
}
