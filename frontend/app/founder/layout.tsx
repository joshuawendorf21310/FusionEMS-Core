'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_DOMAINS = [
  {
    id: 'executive',
    label: '1 · Executive',
    icon: '◈',
    color: '#ff6b1a',
    links: [
      { href: '/founder', label: 'Overview' },
      { href: '/founder/executive/daily-brief', label: 'Daily AI Brief' },
      { href: '/founder/executive/risk-monitor', label: 'Risk Monitor' },
      { href: '/founder/executive/events-feed', label: 'Events Feed' },
    ],
  },
  {
    id: 'revenue',
    label: '2 · Revenue',
    icon: '◈',
    color: '#22d3ee',
    links: [
      { href: '/founder/revenue/billing-intelligence', label: 'Billing Intelligence' },
      { href: '/founder/revenue/stripe', label: 'Stripe Dashboard' },
      { href: '/founder/revenue/ar-aging', label: 'AR Aging' },
      { href: '/founder/revenue/forecast', label: 'Revenue Forecast' },
    ],
  },
  {
    id: 'ai-governance',
    label: '3 · AI Governance',
    icon: '◈',
    color: '#a855f7',
    links: [
      { href: '/founder/ai/policies', label: 'AI Policies' },
      { href: '/founder/ai/prompt-editor', label: 'Prompt Editor' },
      { href: '/founder/ai/thresholds', label: 'Confidence Thresholds' },
      { href: '/founder/ai/review-queue', label: 'AI Review Queue' },
    ],
  },
  {
    id: 'communications',
    label: '4 · Communications',
    icon: '◈',
    color: '#4caf50',
    links: [
      { href: '/founder/comms/inbox', label: 'Support Inbox' },
      { href: '/founder/comms/phone-system', label: 'Phone System' },
      { href: '/founder/comms/script-builder', label: 'Script Builder' },
      { href: '/founder/comms/broadcast', label: 'Broadcast Manager' },
    ],
  },
  {
    id: 'compliance',
    label: '5 · Compliance',
    icon: '◈',
    color: '#f59e0b',
    links: [
      { href: '/founder/compliance/nemsis', label: 'NEMSIS Manager' },
      { href: '/founder/compliance/export-status', label: 'Export Status' },
      { href: '/founder/compliance/certification', label: 'Certification Monitor' },
      { href: '/founder/compliance/niers', label: 'NIERS Manager' },
      { href: '/founder/compliance/neris', label: 'NERIS Compliance Studio' },
      { href: '/founder/compliance/hems', label: 'HEMS Safety Audit' },
      { href: '/founder/compliance/packs', label: 'Compliance Packs' },
      { href: '/founder/compliance/cms-gate', label: 'CMS Gate Monitor' },
    ],
  },
  {
    id: 'security',
    label: '6 · Visibility & Security',
    icon: '◈',
    color: '#e53935',
    links: [
      { href: '/founder/security/role-builder', label: 'Role Builder' },
      { href: '/founder/security/field-masking', label: 'Field Masking' },
      { href: '/founder/security/access-logs', label: 'Access Logs' },
      { href: '/founder/security/policy-sandbox', label: 'Policy Sandbox' },
    ],
  },
  {
    id: 'templates',
    label: '7 · Templates',
    icon: '◈',
    color: '#29b6f6',
    links: [
      { href: '/founder/templates/proposals', label: 'Proposal Templates' },
      { href: '/founder/templates/invoices', label: 'Invoice Templates' },
      { href: '/founder/templates/contracts', label: 'Contract Builder' },
      { href: '/founder/templates/reports', label: 'Report Templates' },
    ],
  },
  {
    id: 'roi-sales',
    label: '8 · ROI & Sales',
    icon: '◈',
    color: '#ff9800',
    links: [
      { href: '/founder/roi/analytics', label: 'ROI Analytics' },
      { href: '/founder/roi/funnel', label: 'Funnel Dashboard' },
      { href: '/founder/roi/pricing-simulator', label: 'Pricing Simulator' },
      { href: '/founder/roi/proposals', label: 'Proposal Tracker' },
    ],
  },
  {
    id: 'pwa-mobile',
    label: '9 · PWA & Mobile',
    icon: '◈',
    color: '#3b82f6',
    links: [
      { href: '/founder/pwa/crewlink', label: 'CrewLink' },
      { href: '/founder/pwa/scheduling', label: 'Scheduling' },
      { href: '/founder/pwa/deployment', label: 'Deployment Monitor' },
      { href: '/founder/pwa/device-analytics', label: 'Device Analytics' },
    ],
  },
  {
    id: 'infrastructure',
    label: '10 · Infrastructure',
    icon: '◈',
    color: '#94a3b8',
    links: [
      { href: '/founder/infra/ecs', label: 'ECS Health' },
      { href: '/founder/infra/rds', label: 'RDS Health' },
      { href: '/founder/infra/ai-gpu', label: 'AI GPU Monitor' },
      { href: '/founder/infra/cost', label: 'Cost Dashboard' },
      { href: '/founder/infra/incident', label: 'Incident Control' },
    ],
  },
  {
    id: 'founder-tools',
    label: '11 · Founder Tools',
    icon: '◈',
    color: '#ff6b1a',
    links: [
      { href: '/founder/tools/calendar', label: 'Calendar' },
      { href: '/founder/tools/documents', label: 'Documents' },
      { href: '/founder/tools/onboarding-control', label: 'Onboarding Control' },
      { href: '/founder/tools/invoice-creator', label: 'Invoice Creator' },
      { href: '/founder/tools/expense-ledger', label: 'Expense Ledger' },
      { href: '/founder/tools/task-center', label: 'Task Center' },
      { href: '/founder/copilot', label: 'Copilot Chat' },
    ],
  },
  {
    id: 'operations',
    label: '12 · Operations',
    icon: '◈',
    color: '#22d3ee',
    links: [
      { href: '/portal/cases', label: 'Cases (Cross-Portal)' },
      { href: '/founder/ops/fleet-intelligence', label: 'Fleet Intelligence' },
      { href: '/founder/ops/readiness', label: 'Readiness Monitor' },
      { href: '/founder/ops/hems', label: 'HEMS Overview' },
      { href: '/founder/ops/scheduling-ai', label: 'AI Scheduling Studio' },
    ],
  },
  {
    id: 'pricing',
    label: '13 · Pricing',
    icon: '◈',
    color: '#ff6b1a',
    links: [
      { href: '/founder/pricing/studio', label: 'Pricing Studio' },
      { href: '/founder/revenue/stripe', label: 'Stripe Dashboard' },
    ],
  },
];

function SidebarSection({
  domain,
  isOpen,
  onToggle,
  currentPath,
}: {
  domain: typeof NAV_DOMAINS[0];
  isOpen: boolean;
  onToggle: () => void;
  currentPath: string;
}) {
  const hasActive = domain.links.some((l) => currentPath === l.href);
  return (
    <div className="mb-1">
      <button
        onClick={onToggle}
        className={`w-full flex items-center justify-between px-3 py-2 text-xs font-semibold uppercase tracking-widest transition-colors ${
          hasActive ? 'text-white' : 'text-[rgba(255,255,255,0.42)] hover:text-[rgba(255,255,255,0.72)]'
        }`}
        style={{ letterSpacing: '0.1em' }}
      >
        <div className="flex items-center gap-2">
          <span style={{ color: domain.color, fontSize: 10 }}>▣</span>
          <span>{domain.label}</span>
        </div>
        <span className={`text-[10px] transition-transform ${isOpen ? 'rotate-90' : ''}`}>▶</span>
      </button>
      {isOpen && (
        <div className="pl-5 pb-1 space-y-0.5">
          {domain.links.map((link) => {
            const active = currentPath === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`block px-3 py-1.5 text-xs rounded transition-colors ${
                  active
                    ? 'text-white bg-[rgba(255,107,26,0.15)] border-l-2 border-orange-DEFAULT pl-2'
                    : 'text-[rgba(255,255,255,0.5)] hover:text-white hover:bg-[rgba(255,255,255,0.05)]'
                }`}
                style={active ? { borderLeftColor: domain.color } : {}}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TopBar({ sidebarOpen, setSidebarOpen }: { sidebarOpen: boolean; setSidebarOpen: (v: boolean) => void }) {
  const [search, setSearch] = useState('');
  const [aiInput, setAiInput] = useState('');
  return (
    <header className="sticky top-0 z-50 flex items-center gap-3 px-4 h-12 border-b border-[rgba(255,255,255,0.08)] bg-[rgba(7,9,13,0.96)] backdrop-blur-sm">
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="flex flex-col gap-[4px] justify-center w-7 h-7 flex-shrink-0"
        aria-label="Toggle sidebar"
      >
        <span className="h-[2px] w-5 bg-[rgba(255,255,255,0.5)]" />
        <span className="h-[2px] w-3 bg-[rgba(255,255,255,0.5)]" />
        <span className="h-[2px] w-5 bg-[rgba(255,255,255,0.5)]" />
      </button>

      <Link href="/founder" className="flex items-center gap-2 flex-shrink-0">
        <div className="w-7 h-7 bg-[#ff6b1a] flex items-center justify-center text-[10px] font-black text-black" style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}>
          FQ
        </div>
        <span className="text-xs font-semibold text-[rgba(255,255,255,0.9)] hidden sm:block">FOUNDER OS</span>
      </Link>

      <div className="flex-1 flex items-center gap-2 max-w-xl">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Global search — claims, tenants, exports, invoices..."
          className="flex-1 h-7 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.08)] px-3 text-xs text-white placeholder-[rgba(255,255,255,0.25)] focus:outline-none focus:border-[#ff6b1a] rounded-sm"
        />
        <input
          value={aiInput}
          onChange={(e) => setAiInput(e.target.value)}
          placeholder="Ask Quantum..."
          className="w-48 h-7 bg-[rgba(255,107,26,0.08)] border border-[rgba(255,107,26,0.25)] px-3 text-xs text-white placeholder-[rgba(255,107,26,0.45)] focus:outline-none focus:border-[#ff6b1a] rounded-sm"
        />
      </div>

      <div className="flex items-center gap-3 ml-auto flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-[#4caf50] animate-pulse" />
          <span className="text-[10px] text-[#4caf50] font-semibold uppercase tracking-wider">LIVE</span>
        </div>
        <div className="text-xs text-[rgba(255,255,255,0.55)] hidden md:block">
          <span className="text-[rgba(255,255,255,0.3)]">REV TODAY</span>{' '}
          <span className="text-white font-semibold">—</span>
        </div>
        <button className="relative w-7 h-7 flex items-center justify-center text-[rgba(255,255,255,0.5)] hover:text-white">
          <span className="text-sm">🔔</span>
          <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-[#ff6b1a]" />
        </button>
        <div className="w-7 h-7 rounded-full bg-[rgba(255,107,26,0.2)] border border-[rgba(255,107,26,0.4)] flex items-center justify-center text-[10px] font-bold text-[#ff6b1a]">
          FD
        </div>
        <button className="h-6 px-2 bg-[#e53935] text-[10px] font-bold uppercase tracking-widest text-white rounded-sm hover:bg-[#ff5252] transition-colors">
          INCIDENT
        </button>
      </div>
    </header>
  );
}

function AIContextPanel() {
  const [collapsed, setCollapsed] = useState(false);
  if (collapsed) {
    return (
      <aside className="w-8 border-l border-[rgba(255,255,255,0.06)] bg-[#0b0f14] flex flex-col items-center pt-3">
        <button onClick={() => setCollapsed(false)} className="text-[rgba(255,107,26,0.6)] hover:text-[#ff6b1a] text-xs">
          ◁
        </button>
      </aside>
    );
  }
  return (
    <aside className="w-64 flex-shrink-0 border-l border-[rgba(255,255,255,0.06)] bg-[#0b0f14] flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[rgba(255,255,255,0.06)]">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,107,26,0.8)]">Quantum AI</span>
        <button onClick={() => setCollapsed(true)} className="text-[rgba(255,255,255,0.3)] hover:text-white text-xs">▷</button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.3)] mb-1.5">Suggested Actions</div>
          {[
            { text: 'Review 3 pending denial appeals', urgency: 'warning' },
            { text: 'Approve 1 AI review queue item', urgency: 'info' },
            { text: 'Check export failures (0 today)', urgency: 'ok' },
            { text: '2 credential expirations in 30d', urgency: 'warning' },
          ].map((item, i) => (
            <div key={i} className={`flex items-start gap-2 py-1.5 border-b border-[rgba(255,255,255,0.04)] last:border-0`}>
              <span className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                item.urgency === 'warning' ? 'bg-[#ff9800]' : item.urgency === 'info' ? 'bg-[#29b6f6]' : 'bg-[#4caf50]'
              }`} />
              <span className="text-xs text-[rgba(255,255,255,0.65)]">{item.text}</span>
            </div>
          ))}
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.3)] mb-1.5">Risk Alerts</div>
          {[
            { text: 'Churn risk: 0 tenants flagged', level: 'ok' },
            { text: 'Revenue risk: AR aging stable', level: 'ok' },
            { text: 'Compliance: NEMSIS v3.5 current', level: 'ok' },
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-2 py-1.5 border-b border-[rgba(255,255,255,0.04)] last:border-0">
              <span className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${item.level === 'ok' ? 'bg-[#4caf50]' : 'bg-[#e53935]'}`} />
              <span className="text-xs text-[rgba(255,255,255,0.55)]">{item.text}</span>
            </div>
          ))}
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.3)] mb-1.5">Recent AI Decisions</div>
          {[
            'Auto-resolved billing inquiry (Tenant A)',
            'Escalated compliance question to queue',
            'Scheduled callback for Export issue',
          ].map((item, i) => (
            <div key={i} className="py-1.5 border-b border-[rgba(255,255,255,0.04)] last:border-0">
              <span className="text-xs text-[rgba(255,255,255,0.45)]">{item}</span>
            </div>
          ))}
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.3)] mb-1.5">Quick Fix</div>
          <button className="w-full text-left px-2 py-1.5 bg-[rgba(255,107,26,0.08)] border border-[rgba(255,107,26,0.2)] text-xs text-[#ff6b1a] rounded-sm hover:bg-[rgba(255,107,26,0.14)] transition-colors">
            View top denial fix recommendations →
          </button>
        </div>
      </div>
    </aside>
  );
}

export default function FounderLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [openDomains, setOpenDomains] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    NAV_DOMAINS.forEach((d) => {
      initial[d.id] = d.links.some((l) => pathname === l.href);
    });
    if (!Object.values(initial).some(Boolean)) initial['executive'] = true;
    return initial;
  });

  const toggleDomain = (id: string) => {
    setOpenDomains((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="flex flex-col h-screen bg-[#07090d] text-white overflow-hidden">
      <TopBar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="flex flex-1 overflow-hidden">
        {sidebarOpen && (
          <aside className="w-52 flex-shrink-0 border-r border-[rgba(255,255,255,0.06)] bg-[#07090d] overflow-y-auto">
            <div className="px-2 py-3">
              {NAV_DOMAINS.map((domain) => (
                <SidebarSection
                  key={domain.id}
                  domain={domain}
                  isOpen={openDomains[domain.id] ?? false}
                  onToggle={() => toggleDomain(domain.id)}
                  currentPath={pathname}
                />
              ))}
            </div>
          </aside>
        )}
        <main className="flex-1 overflow-y-auto bg-[#0b0f14]">
          {children}
        </main>
        <AIContextPanel />
      </div>
    </div>
  );
}
