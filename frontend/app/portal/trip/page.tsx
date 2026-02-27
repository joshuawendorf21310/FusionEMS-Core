'use client';

import React, { useState } from 'react';

type TripTab = 'overview' | 'exports' | 'rejects' | 'postings';

const TABS: { id: TripTab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'exports', label: 'DOR Exports' },
  { id: 'rejects', label: 'Rejects' },
  { id: 'postings', label: 'Postings' },
];

function StatCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: string }) {
  return (
    <div className="bg-[#0b0f14] border border-[rgba(255,255,255,0.07)] rounded-sm px-4 py-3">
      <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-1">{label}</div>
      <div className="text-xl font-bold" style={{ color: accent ?? 'white' }}>{value}</div>
      {sub && <div className="text-[10px] text-[rgba(255,255,255,0.35)] mt-0.5">{sub}</div>}
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="text-xs text-[rgba(255,255,255,0.3)]">No {label}</div>
    </div>
  );
}

function OverviewTab() {
  return (
    <div className="space-y-6">
      <div className="px-4 py-3 bg-[rgba(34,211,238,0.06)] border border-[rgba(34,211,238,0.2)] rounded-sm flex items-start gap-3">
        <span className="mt-1 w-1.5 h-1.5 rounded-full bg-[#22d3ee] flex-shrink-0" />
        <div>
          <div className="text-xs font-semibold text-[#22d3ee] mb-0.5">Wisconsin Tax Refund Intercept Program (TRIP)</div>
          <div className="text-[11px] text-[rgba(255,255,255,0.5)]">
            Eligible government agencies may submit qualifying delinquent debts to the Wisconsin DOR for interception of state tax refunds. Minimum debt age: 90 days. Required fields: Debtor name, SSN/DL/FEIN, balance, Agency Debt ID.
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Total Enrolled Debts" value="0" />
        <StatCard label="Total Balance" value="$0.00" accent="#22d3ee" />
        <StatCard label="Collected via TRIP" value="$0.00" accent="#4caf50" />
        <StatCard label="Open Rejects" value="0" accent="#f59e0b" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[#0b0f14] border border-[rgba(255,255,255,0.07)] rounded-sm p-4">
          <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-3">Workflow Steps</div>
          {[
            { step: '1', label: 'Build Candidate Queue', desc: 'Identify debts >= 90 days, not disputed, not previously submitted', color: '#22d3ee' },
            { step: '2', label: 'Generate DOR XML Export', desc: 'Produces TRIPSubmission XML per DOR schema v1, zipped for upload', color: '#ff6b1a' },
            { step: '3', label: 'Handle Rejects', desc: 'Import DOR reject file, flag accounts, queue fix tasks', color: '#f59e0b' },
            { step: '4', label: 'Import Posting Notifications', desc: 'Reconcile DOR posting file, auto-post payments to AR ledger', color: '#4caf50' },
          ].map((item) => (
            <div key={item.step} className="flex items-start gap-3 py-3 border-b border-[rgba(255,255,255,0.05)] last:border-0">
              <div
                className="w-5 h-5 rounded-sm flex items-center justify-center text-[10px] font-bold flex-shrink-0"
                style={{ backgroundColor: `${item.color}18`, color: item.color }}
              >
                {item.step}
              </div>
              <div>
                <div className="text-xs font-medium text-white mb-0.5">{item.label}</div>
                <div className="text-[11px] text-[rgba(255,255,255,0.4)]">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-[#0b0f14] border border-[rgba(255,255,255,0.07)] rounded-sm p-4">
          <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-3">Recent Activity</div>
          <EmptyState label="recent TRIP activity" />
        </div>
      </div>
    </div>
  );
}

function ExportsTab() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs text-[rgba(255,255,255,0.5)]">DOR XML export history</div>
        <div className="flex gap-2">
          <button className="h-7 px-3 bg-[rgba(255,107,26,0.1)] border border-[rgba(255,107,26,0.25)] text-[10px] font-semibold uppercase tracking-wider text-[#ff6b1a] hover:bg-[rgba(255,107,26,0.18)] transition-colors rounded-sm">
            Build Candidates
          </button>
          <button className="h-7 px-3 bg-[rgba(34,211,238,0.1)] border border-[rgba(34,211,238,0.25)] text-[10px] font-semibold uppercase tracking-wider text-[#22d3ee] hover:bg-[rgba(34,211,238,0.18)] transition-colors rounded-sm">
            Generate XML Export
          </button>
        </div>
      </div>
      <div className="bg-[#0b0f14] border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-[rgba(255,255,255,0.06)] text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Export ID</span><span>Debt Count</span><span>Total Balance</span><span>Generated</span><span>Status</span><span>Download</span>
        </div>
        <EmptyState label="DOR exports" />
      </div>
    </div>
  );
}

function RejectsTab() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs text-[rgba(255,255,255,0.5)]">Import and review DOR reject files</div>
        <button className="h-7 px-3 bg-[rgba(245,158,11,0.1)] border border-[rgba(245,158,11,0.25)] text-[10px] font-semibold uppercase tracking-wider text-[#f59e0b] hover:bg-[rgba(245,158,11,0.18)] transition-colors rounded-sm">
          Import Reject File
        </button>
      </div>
      <div className="px-4 py-3 bg-[rgba(245,158,11,0.06)] border border-[rgba(245,158,11,0.15)] rounded-sm mb-4 text-[11px] text-[rgba(245,158,11,0.8)]">
        Rejected debts are automatically flagged and removed from active TRIP status. Review each reject code and correct the underlying data before re-submitting.
      </div>
      <div className="bg-[#0b0f14] border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-[rgba(255,255,255,0.06)] text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Account</span><span>Debtor</span><span>Reject Code</span><span>Reason</span><span>Imported</span><span>Action</span>
        </div>
        <EmptyState label="TRIP rejects" />
      </div>
    </div>
  );
}

function PostingsTab() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs text-[rgba(255,255,255,0.5)]">DOR Posting Notification reconciliation</div>
        <button className="h-7 px-3 bg-[rgba(76,175,80,0.1)] border border-[rgba(76,175,80,0.25)] text-[10px] font-semibold uppercase tracking-wider text-[#4caf50] hover:bg-[rgba(76,175,80,0.18)] transition-colors rounded-sm">
          Import Posting File
        </button>
      </div>
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Reconciled" value="0" accent="#4caf50" />
        <StatCard label="Unmatched" value="0" accent="#f59e0b" />
        <StatCard label="Total Amount" value="$0.00" />
        <StatCard label="Last Import" value="—" />
      </div>
      <div className="bg-[#0b0f14] border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-[rgba(255,255,255,0.06)] text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Account</span><span>Amount</span><span>Tax Year</span><span>Agency Debt ID</span><span>Reconciled</span><span>Status</span>
        </div>
        <EmptyState label="TRIP postings" />
      </div>
    </div>
  );
}

export default function TripDashboardPage() {
  const [activeTab, setActiveTab] = useState<TripTab>('overview');

  const content: Record<TripTab, React.ReactNode> = {
    overview: <OverviewTab />,
    exports: <ExportsTab />,
    rejects: <RejectsTab />,
    postings: <PostingsTab />,
  };

  return (
    <div className="p-6 max-w-[1200px]">
      <div className="mb-6">
        <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-1">Agency Portal — Government Only</div>
        <h1 className="text-xl font-bold text-white">Wisconsin TRIP</h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Tax Refund Intercept Program — DOR XML exports, reject handling, and posting reconciliation</p>
      </div>

      <div className="flex gap-0 mb-6 border-b border-[rgba(255,255,255,0.08)]">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative px-4 py-2.5 text-xs font-medium transition-colors ${
              activeTab === tab.id ? 'text-white' : 'text-[rgba(255,255,255,0.4)] hover:text-[rgba(255,255,255,0.7)]'
            }`}
          >
            {tab.label}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#22d3ee]" />
            )}
          </button>
        ))}
      </div>

      <div>{content[activeTab]}</div>
    </div>
  );
}
