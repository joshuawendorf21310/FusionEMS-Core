'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/tools/calendar', label: 'Calendar', desc: 'Meetings, deadlines, compliance events, billing cycles', color: '#ff6b1a' },
  { href: '/founder/tools/documents', label: 'Documents Vault', desc: 'Contracts, BAAs, proposals, certificates, legal docs', color: '#ff6b1a' },
  { href: '/founder/tools/invoice-creator', label: 'Invoice Creator', desc: 'Generate and track invoices for agency clients', color: '#ff6b1a' },
  { href: '/founder/tools/expense-ledger', label: 'Expense Ledger', desc: 'Track and categorize business expenses', color: '#ff6b1a' },
  { href: '/founder/tools/task-center', label: 'Task Center', desc: 'Action items, priorities, delegation, deadlines', color: '#ff6b1a' },
  { href: '/founder/tools/email', label: 'Email Inbox', desc: 'Microsoft Graph mail — inbox, compose, reply, attachments', color: '#29b6f6' },
  { href: '/founder/tools/files', label: 'OneDrive Files', desc: 'Microsoft Graph files — browse, preview, download', color: '#29b6f6' },
];

export default function ToolsPage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">DOMAIN 11 · FOUNDER TOOLS</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">Founder Tools</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">Calendar · documents · invoicing · expenses · tasks</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {LINKS.map((l) => (
          <motion.div key={l.href} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <Link href={l.href} className="block bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-5 hover:border-[rgba(255,255,255,0.18)] transition-colors" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-sm font-bold mb-1" style={{ color: l.color }}>{l.label}</div>
              <div className="text-xs text-[rgba(255,255,255,0.45)]">{l.desc}</div>
            </Link>
          </motion.div>
        ))}
      </div>
      <Link href="/founder" className="text-xs text-[rgba(255,107,26,0.6)] hover:text-[#ff6b1a]">← Back to Founder Command OS</Link>
    </div>
  );
}
