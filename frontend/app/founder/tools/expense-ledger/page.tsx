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

const EXPENSES = [
  { date: 'Jan 25', vendor: 'AWS', category: 'Infrastructure', amount: 1247, description: 'Monthly cloud services', receipt: true },
  { date: 'Jan 24', vendor: 'Stripe', category: 'Software', amount: 0, description: 'Payment processor (usage-based)', receipt: true },
  { date: 'Jan 23', vendor: 'Telnyx', category: 'Communications', amount: 84, description: 'SMS/Voice credits', receipt: true },
  { date: 'Jan 22', vendor: 'LOB.com', category: 'Mailing', amount: 42, description: 'Physical statements', receipt: true },
  { date: 'Jan 20', vendor: 'OpenAI', category: 'AI/ML', amount: 180, description: 'API usage', receipt: true },
  { date: 'Jan 18', vendor: 'GitHub', category: 'Software', amount: 21, description: 'Teams plan', receipt: true },
  { date: 'Jan 15', vendor: 'Linear', category: 'Software', amount: 16, description: 'Project management', receipt: true },
  { date: 'Jan 14', vendor: 'Figma', category: 'Software', amount: 45, description: 'Design tool', receipt: true },
  { date: 'Jan 12', vendor: 'Google Workspace', category: 'Software', amount: 72, description: 'Email/docs', receipt: true },
  { date: 'Jan 10', vendor: 'Legal Counsel', category: 'Legal', amount: 450, description: 'Contract review', receipt: true },
  { date: 'Jan 8', vendor: 'Domain renewal', category: 'Software', amount: 28, description: 'fusionemsquantum.com', receipt: true },
  { date: 'Jan 5', vendor: 'Office supplies', category: 'Other', amount: 84, description: 'Misc supplies', receipt: false },
  { date: 'Jan 3', vendor: 'Marketing ads', category: 'Marketing', amount: 340, description: 'Google/LinkedIn', receipt: true },
  { date: 'Jan 2', vendor: 'Postage / printing', category: 'Other', amount: 38, description: 'Physical mail', receipt: true },
  { date: 'Jan 1', vendor: 'Annual software', category: 'Software', amount: 195, description: 'Zoom annual', receipt: true },
];

const CATEGORY_BREAKDOWN = [
  { label: 'Infrastructure', pct: 32, amount: '$1,247', status: 'error' as const },
  { label: 'Software', pct: 22, amount: '$847', status: 'info' as const },
  { label: 'AI/ML', pct: 14, amount: '$538', status: 'info' as const },
  { label: 'Communications', pct: 11, amount: '$423', status: 'info' as const },
  { label: 'Marketing', pct: 9, amount: '$340', status: 'warn' as const },
  { label: 'Other', pct: 12, amount: '$447', status: 'warn' as const },
];

export default function ExpenseLedgerPage() {
  const [showForm, setShowForm] = useState(false);
  const [expenseForm, setExpenseForm] = useState({
    date: '',
    amount: '',
    category: 'AWS',
    description: '',
    vendor: '',
  });

  return (
    <div className="min-h-screen bg-[#080e16] text-white p-6 space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-bold text-[rgba(255,107,26,0.6)] font-mono tracking-widest uppercase">
            MODULE 11 · FOUNDER TOOLS
          </span>
          <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-[#ff6b1a] transition-colors">
            ← Back to Founder OS
          </Link>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white" style={{ textShadow: '0 0 24px rgba(255,107,26,0.3)' }}>
          Expense Ledger
        </h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Track business expenses · categorize · export for accounting</p>
      </motion.div>

      {/* MODULE 1 — Monthly Summary */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Total MTD', value: '$3,842', status: 'info' as const },
            { label: 'AWS Infrastructure', value: '$1,247', status: 'error' as const },
            { label: 'Software & Tools', value: '$480', status: 'warn' as const },
            { label: 'Marketing', value: '$340', status: 'warn' as const },
          ].map((s) => (
            <Panel key={s.label} className="flex flex-col gap-1">
              <span className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">{s.label}</span>
              <span
                className="text-xl font-bold"
                style={{ color: s.status === 'error' ? '#e53935' : s.status === 'warn' ? '#ff9800' : 'rgba(255,255,255,0.9)' }}
              >
                {s.value}
              </span>
              <Badge label={s.status === 'error' ? 'largest' : s.status} status={s.status} />
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 2 — Add Expense */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Panel>
          <SectionHeader number="2" title="Add Expense" />
          <button
            onClick={() => setShowForm((v) => !v)}
            className="px-4 py-2 text-xs font-bold uppercase tracking-widest rounded-sm transition-all hover:brightness-110"
            style={{ background: '#ff6b1a', color: '#000' }}
          >
            {showForm ? 'Hide Form' : 'Add Expense'}
          </button>
          {showForm && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Date</label>
                <input
                  type="date"
                  value={expenseForm.date}
                  onChange={(e) => setExpenseForm({ ...expenseForm, date: e.target.value })}
                  className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a]"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Amount</label>
                <input
                  type="number"
                  value={expenseForm.amount}
                  onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
                  placeholder="0.00"
                  className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a] placeholder:text-[rgba(255,255,255,0.2)]"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Category</label>
                <select
                  value={expenseForm.category}
                  onChange={(e) => setExpenseForm({ ...expenseForm, category: e.target.value })}
                  className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a]"
                >
                  {['AWS', 'Software', 'Marketing', 'Legal', 'Travel', 'Other'].map((c) => (
                    <option key={c} value={c} className="bg-[#0f1720]">{c}</option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Vendor</label>
                <input
                  type="text"
                  value={expenseForm.vendor}
                  onChange={(e) => setExpenseForm({ ...expenseForm, vendor: e.target.value })}
                  placeholder="Vendor name"
                  className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a] placeholder:text-[rgba(255,255,255,0.2)]"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Description</label>
                <input
                  type="text"
                  value={expenseForm.description}
                  onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
                  placeholder="Description"
                  className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a] placeholder:text-[rgba(255,255,255,0.2)]"
                />
              </div>
              <div className="flex items-end">
                <button
                  className="px-4 py-2 text-xs font-bold uppercase tracking-widest rounded-sm transition-all hover:brightness-110"
                  style={{ background: '#ff6b1a', color: '#000' }}
                  onClick={() => {
                    setExpenseForm({ date: '', amount: '', category: 'AWS', description: '', vendor: '' });
                    setShowForm(false);
                  }}
                >
                  Save
                </button>
              </div>
            </div>
          )}
        </Panel>
      </motion.div>

      {/* MODULE 3 — Expense Log */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <Panel>
          <SectionHeader number="3" title="Expense Log" sub="January 2026" />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.06)]">
                  {['Date', 'Vendor', 'Category', 'Amount', 'Description', 'Receipt'].map((h) => (
                    <th key={h} className="text-left py-1.5 px-2 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {EXPENSES.map((exp, i) => (
                  <tr key={i} className="border-b border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.02)]">
                    <td className="py-1.5 px-2 font-mono text-[rgba(255,107,26,0.7)] text-[11px]">{exp.date}</td>
                    <td className="py-1.5 px-2 text-[rgba(255,255,255,0.8)] font-medium">{exp.vendor}</td>
                    <td className="py-1.5 px-2 text-[rgba(255,255,255,0.45)]">{exp.category}</td>
                    <td className="py-1.5 px-2 font-mono text-[rgba(255,255,255,0.85)] font-semibold">
                      ${exp.amount.toLocaleString()}
                    </td>
                    <td className="py-1.5 px-2 text-[rgba(255,255,255,0.45)]">{exp.description}</td>
                    <td className="py-1.5 px-2 text-center">
                      {exp.receipt ? (
                        <span className="text-[#4caf50] font-bold">&#10003;</span>
                      ) : (
                        <span className="text-[rgba(255,255,255,0.25)]">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 4 — Category Breakdown */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Panel>
          <SectionHeader number="4" title="Category Breakdown" sub="% of total spend" />
          <div className="space-y-3">
            {CATEGORY_BREAKDOWN.map((cat) => (
              <div key={cat.label} className="flex items-center gap-3">
                <span className="text-xs text-[rgba(255,255,255,0.6)] w-32 shrink-0">{cat.label}</span>
                <div className="flex-1 h-2 bg-[rgba(255,255,255,0.05)] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${cat.pct}%`,
                      background:
                        cat.status === 'error'
                          ? '#e53935'
                          : cat.status === 'warn'
                          ? '#ff9800'
                          : '#29b6f6',
                    }}
                  />
                </div>
                <span className="text-[10px] font-mono text-[rgba(255,255,255,0.5)] w-8 text-right">{cat.pct}%</span>
                <span className="text-[11px] font-mono font-semibold text-[rgba(255,255,255,0.7)] w-16 text-right">{cat.amount}</span>
              </div>
            ))}
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 5 — Export Options */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <Panel>
          <SectionHeader number="5" title="Export Options" />
          <div className="flex flex-wrap gap-3">
            {[
              { label: 'Export CSV', style: { background: 'rgba(76,175,80,0.12)', color: '#4caf50', border: '1px solid rgba(76,175,80,0.3)' } },
              { label: 'Export PDF', style: { background: 'rgba(255,107,26,0.12)', color: '#ff6b1a', border: '1px solid rgba(255,107,26,0.3)' } },
              { label: 'Download Receipts ZIP', style: { background: 'rgba(41,182,246,0.1)', color: '#29b6f6', border: '1px solid rgba(41,182,246,0.25)' } },
            ].map((btn) => (
              <button
                key={btn.label}
                className="px-4 py-2 text-xs font-bold uppercase tracking-widest rounded-sm transition-all hover:brightness-110"
                style={btn.style}
              >
                {btn.label}
              </button>
            ))}
            <div className="flex items-center gap-2">
              <button
                className="px-4 py-2 text-xs font-bold uppercase tracking-widest rounded-sm opacity-60 cursor-not-allowed"
                style={{ background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.4)', border: '1px solid rgba(255,255,255,0.1)' }}
                disabled
              >
                Sync to QuickBooks
              </button>
              <Badge label="QuickBooks" status="info" />
            </div>
          </div>
        </Panel>
      </motion.div>

      <div className="pt-2">
        <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.35)] hover:text-[#ff6b1a] transition-colors">
          ← Back to Founder OS
        </Link>
      </div>
    </div>
  );
}
