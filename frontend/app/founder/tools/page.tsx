'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/tools/calendar', label: 'Calendar', desc: 'Meetings, deadlines, compliance events, billing cycles', color: 'var(--q-orange)' },
  { href: '/founder/tools/documents', label: 'Documents Vault', desc: 'Contracts, BAAs, proposals, certificates, legal docs', color: 'var(--q-orange)' },
  { href: '/founder/tools/invoice-creator', label: 'Invoice Creator', desc: 'Generate and track invoices for agency clients', color: 'var(--q-orange)' },
  { href: '/founder/tools/expense-ledger', label: 'Expense Ledger', desc: 'Track and categorize business expenses', color: 'var(--q-orange)' },
  { href: '/founder/tools/task-center', label: 'Task Center', desc: 'Action items, priorities, delegation, deadlines', color: 'var(--q-orange)' },
  { href: '/founder/tools/email', label: 'Email Inbox', desc: 'Microsoft Graph mail — inbox, compose, reply, attachments', color: 'var(--color-status-info)' },
  { href: '/founder/tools/files', label: 'OneDrive Files', desc: 'Microsoft Graph files — browse, preview, download', color: 'var(--color-status-info)' },
];

export default function ToolsPage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">DOMAIN 11 · FOUNDER TOOLS</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Founder Tools</h1>
        <p className="text-xs text-text-muted mt-0.5">Calendar · documents · invoicing · expenses · tasks</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {LINKS.map((l) => (
          <motion.div key={l.href} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <Link href={l.href} className="block bg-bg-panel border border-border-DEFAULT p-5 hover:border-[rgba(255,255,255,0.18)] transition-colors" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-sm font-bold mb-1" style={{ color: l.color }}>{l.label}</div>
              <div className="text-xs text-[rgba(255,255,255,0.45)]">{l.desc}</div>
            </Link>
          </motion.div>
        ))}
      </div>
      <Link href="/founder" className="text-xs text-orange-dim hover:text-orange">← Back to Founder Command OS</Link>
    </div>
  );
}
