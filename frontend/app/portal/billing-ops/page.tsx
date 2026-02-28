'use client';

import React, { useState } from 'react';

type TabId = 'statements' | 'payments' | 'disputes' | 'placement' | 'trip_candidates' | 'trip_rejects' | 'trip_postings';

const TABS: { id: TabId; label: string; color: string }[] = [
  { id: 'statements', label: 'Statements Due', color: 'var(--q-orange)' },
  { id: 'payments', label: 'Payments Posted', color: 'var(--q-green)' },
  { id: 'disputes', label: 'Disputes', color: 'var(--q-yellow)' },
  { id: 'placement', label: 'Placement Eligible', color: 'var(--q-red)' },
  { id: 'trip_candidates', label: 'TRIP Candidates', color: 'var(--color-system-billing)' },
  { id: 'trip_rejects', label: 'TRIP Rejects', color: 'var(--q-yellow)' },
  { id: 'trip_postings', label: 'TRIP Postings', color: 'var(--q-green)' },
];

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm px-4 py-3">
      <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-1">{label}</div>
      <div className="text-xl font-bold text-text-primary">{value}</div>
      {sub && <div className="text-[10px] text-[rgba(255,255,255,0.35)] mt-0.5">{sub}</div>}
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-xs text-[rgba(255,255,255,0.3)]">No {label} found</div>
    </div>
  );
}

function ActionBtn({ label, variant = 'default' }: { label: string; variant?: 'default' | 'danger' | 'success' }) {
  const cls =
    variant === 'danger'
      ? 'bg-[rgba(229,57,53,0.12)] border-red-ghost text-red hover:bg-[rgba(229,57,53,0.2)]'
      : variant === 'success'
      ? 'bg-[rgba(76,175,80,0.12)] border-[rgba(76,175,80,0.3)] text-status-active hover:bg-[rgba(76,175,80,0.2)]'
      : 'bg-[rgba(255,107,26,0.1)] border-[rgba(255,107,26,0.25)] text-orange hover:bg-[rgba(255,107,26,0.18)]';
  return (
    <button className={`h-6 px-3 border text-[10px] font-semibold uppercase tracking-wider rounded-sm transition-colors ${cls}`}>
      {label}
    </button>
  );
}

function StatementsTab() {
  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Due Today" value="0" sub="statements" />
        <StatCard label="Overdue" value="0" sub="> 15 days" />
        <StatCard label="Sent This Month" value="0" />
        <StatCard label="Failed Delivery" value="0" />
      </div>
      <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Account</span><span>Patient</span><span>Balance</span><span>Day</span><span>Channel</span><span>Action</span>
        </div>
        <EmptyState label="statements due" />
      </div>
    </div>
  );
}

function PaymentsTab() {
  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Posted Today" value="$0.00" />
        <StatCard label="Pending Review" value="0" />
        <StatCard label="Failed" value="0" />
        <StatCard label="MTD Collected" value="$0.00" />
      </div>
      <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Account</span><span>Amount</span><span>Source</span><span>Ref</span><span>Posted At</span><span>Status</span>
        </div>
        <EmptyState label="payments" />
      </div>
    </div>
  );
}

function DisputesTab() {
  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Open Disputes" value="0" />
        <StatCard label="Resolved This Month" value="0" />
        <StatCard label="Paused Dunning" value="0" sub="accounts" />
        <StatCard label="Avg Resolution" value="—" sub="days" />
      </div>
      <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Account</span><span>Reason</span><span>Amount</span><span>Opened</span><span>Status</span><span>Action</span>
        </div>
        <EmptyState label="disputes" />
      </div>
    </div>
  );
}

function PlacementTab() {
  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Eligible Accounts" value="0" sub=">= 90 days" />
        <StatCard label="Total Balance" value="$0.00" />
        <StatCard label="Active Placements" value="0" />
        <StatCard label="Last Export" value="—" />
      </div>
      <div className="flex justify-end mb-3">
        <ActionBtn label="Generate Export ZIP" />
      </div>
      <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Account</span><span>Patient</span><span>Balance</span><span>Days Out</span><span>Vendor</span><span>Action</span>
        </div>
        <EmptyState label="placement-eligible accounts" />
      </div>
    </div>
  );
}

function TripCandidatesTab() {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4 px-4 py-3 bg-[rgba(34,211,238,0.06)] border border-[rgba(34,211,238,0.2)] rounded-sm">
        <span className="w-1.5 h-1.5 rounded-full bg-system-billing flex-shrink-0" />
        <span className="text-xs text-[rgba(34,211,238,0.9)]">Wisconsin TRIP — available to enrolled government agencies only</span>
      </div>
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Eligible Debts" value="0" />
        <StatCard label="Total Balance" value="$0.00" />
        <StatCard label="Last XML Export" value="—" />
        <StatCard label="Accepted by DOR" value="0" />
      </div>
      <div className="flex justify-end mb-3">
        <ActionBtn label="Build Candidate Queue" />
      </div>
      <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Account</span><span>Debtor</span><span>ID Type</span><span>Balance</span><span>Status</span><span>Action</span>
        </div>
        <EmptyState label="TRIP candidates" />
      </div>
    </div>
  );
}

function TripRejectsTab() {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4 px-4 py-3 bg-[rgba(245,158,11,0.06)] border border-[rgba(245,158,11,0.2)] rounded-sm">
        <span className="w-1.5 h-1.5 rounded-full bg-status-warning flex-shrink-0" />
        <span className="text-xs text-[rgba(245,158,11,0.9)]">Rejected debts require correction before re-submission to DOR</span>
      </div>
      <div className="grid grid-cols-3 gap-3 mb-6">
        <StatCard label="Open Rejects" value="0" />
        <StatCard label="Fixed This Month" value="0" />
        <StatCard label="Re-submitted" value="0" />
      </div>
      <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-5 px-4 py-2 border-b border-border-subtle text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Account</span><span>Reject Code</span><span>Reason</span><span>Rejected At</span><span>Action</span>
        </div>
        <EmptyState label="TRIP rejects" />
      </div>
    </div>
  );
}

function TripPostingsTab() {
  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Postings Reconciled" value="0" />
        <StatCard label="Unmatched" value="0" />
        <StatCard label="Total Posted" value="$0.00" />
        <StatCard label="Last Import" value="—" />
      </div>
      <div className="flex justify-end mb-3">
        <ActionBtn label="Import Posting File" />
      </div>
      <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Account</span><span>Amount</span><span>Tax Year</span><span>Matched</span><span>Posted At</span><span>Status</span>
        </div>
        <EmptyState label="TRIP postings" />
      </div>
    </div>
  );
}

const TAB_CONTENT: Record<TabId, React.ReactNode> = {
  statements: <StatementsTab />,
  payments: <PaymentsTab />,
  disputes: <DisputesTab />,
  placement: <PlacementTab />,
  trip_candidates: <TripCandidatesTab />,
  trip_rejects: <TripRejectsTab />,
  trip_postings: <TripPostingsTab />,
};

export default function BillingOpsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('statements');

  return (
    <div className="p-6 max-w-[1400px]">
      <div className="mb-6">
        <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-1">Agency Portal</div>
        <h1 className="text-xl font-bold text-text-primary">Billing Ops Today</h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">AR queue, dunning schedule, collections placement, and Wisconsin TRIP</p>
      </div>

      <div className="flex gap-0 mb-6 border-b border-border-DEFAULT">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative px-4 py-2.5 text-xs font-medium transition-colors whitespace-nowrap ${
              activeTab === tab.id ? 'text-text-primary' : 'text-[rgba(255,255,255,0.4)] hover:text-[rgba(255,255,255,0.7)]'
            }`}
          >
            {tab.label}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px]" style={{ backgroundColor: tab.color }} />
            )}
          </button>
        ))}
      </div>

      <div>{TAB_CONTENT[activeTab]}</div>
    </div>
  );
}
