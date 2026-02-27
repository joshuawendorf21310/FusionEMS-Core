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

const INVOICES = [
  { num: 'INV-2024-008', client: 'Agency A', amount: '$1,440', date: 'Jan 25', due: 'Feb 24', status: 'Paid' as const },
  { num: 'INV-2024-007', client: 'Agency B', amount: '$2,880', date: 'Jan 20', due: 'Feb 19', status: 'Outstanding' as const },
  { num: 'INV-2024-006', client: 'Agency C', amount: '$1,440', date: 'Jan 15', due: 'Feb 14', status: 'Paid' as const },
  { num: 'INV-2024-005', client: 'Agency D', amount: '$720', date: 'Jan 10', due: 'Feb 9', status: 'Outstanding' as const },
  { num: 'INV-2024-004', client: 'Agency A', amount: '$1,440', date: 'Dec 25', due: 'Jan 24', status: 'Paid' as const },
  { num: 'INV-2024-003', client: 'Agency B', amount: '$2,880', date: 'Dec 20', due: 'Jan 19', status: 'Paid' as const },
  { num: 'INV-2024-002', client: 'Agency C', amount: '$1,440', date: 'Dec 15', due: 'Jan 14', status: 'Paid' as const },
  { num: 'INV-2024-001', client: 'Agency D', amount: '$720', date: 'Dec 10', due: 'Jan 9', status: 'Paid' as const },
];

const OUTSTANDING = INVOICES.filter((inv) => inv.status === 'Outstanding');

export default function InvoiceCreatorPage() {
  const [invoiceForm, setInvoiceForm] = useState({
    client: '',
    invoiceDate: '2026-01-27',
    dueDate: '2026-02-26',
    description: '',
  });
  const [lineItems, setLineItems] = useState([
    { desc: 'Base Platform Fee', amount: 1200 },
    { desc: 'Export Service Fee', amount: 240 },
  ]);
  const [settings, setSettings] = useState({
    company: 'FusionEMS Quantum LLC',
    address: '123 Founder St, Austin, TX 78701',
    terms: 'Net 30',
    lateFee: '1.5% per month after due date',
  });

  const subtotal = lineItems.reduce((s, l) => s + l.amount, 0);

  function addLineItem() {
    setLineItems([...lineItems, { desc: '', amount: 0 }]);
  }

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
          Invoice Creator
        </h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Generate professional invoices · track payment status · revenue</p>
      </motion.div>

      {/* MODULE 1 — Quick Stats */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Invoices This Month', value: '8', status: 'info' as const },
            { label: 'Total Invoiced', value: '$24,800', status: 'info' as const },
            { label: 'Paid', value: '$19,200', status: 'ok' as const },
            { label: 'Outstanding', value: '$5,600', status: 'warn' as const },
          ].map((s) => (
            <Panel key={s.label} className="flex flex-col gap-1">
              <span className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">{s.label}</span>
              <span
                className="text-xl font-bold"
                style={{ color: s.status === 'ok' ? '#4caf50' : s.status === 'warn' ? '#ff9800' : 'rgba(255,255,255,0.9)' }}
              >
                {s.value}
              </span>
              <Badge label={s.status} status={s.status} />
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 2 — Create Invoice */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Panel>
          <SectionHeader number="2" title="Create Invoice" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Client / Agency</label>
              <input
                type="text"
                value={invoiceForm.client}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, client: e.target.value })}
                placeholder="Agency name"
                className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a] placeholder:text-[rgba(255,255,255,0.2)]"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Invoice Date</label>
              <input
                type="date"
                value={invoiceForm.invoiceDate}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, invoiceDate: e.target.value })}
                className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a]"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Due Date</label>
              <input
                type="date"
                value={invoiceForm.dueDate}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, dueDate: e.target.value })}
                className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a]"
              />
            </div>
            <div className="flex flex-col gap-1 md:col-span-2 lg:col-span-3">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Service Description</label>
              <textarea
                value={invoiceForm.description}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, description: e.target.value })}
                placeholder="Describe services rendered..."
                rows={2}
                className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a] placeholder:text-[rgba(255,255,255,0.2)] resize-none"
              />
            </div>
          </div>

          {/* Line Items */}
          <div className="mb-3">
            <p className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider mb-2">Line Items</p>
            <div className="space-y-2">
              {lineItems.map((item, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    type="text"
                    value={item.desc}
                    onChange={(e) => {
                      const updated = [...lineItems];
                      updated[i].desc = e.target.value;
                      setLineItems(updated);
                    }}
                    placeholder="Description"
                    className="flex-1 bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a] placeholder:text-[rgba(255,255,255,0.2)]"
                  />
                  <input
                    type="number"
                    value={item.amount}
                    onChange={(e) => {
                      const updated = [...lineItems];
                      updated[i].amount = Number(e.target.value);
                      setLineItems(updated);
                    }}
                    className="w-28 bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a]"
                  />
                </div>
              ))}
            </div>
            <button
              onClick={addLineItem}
              className="mt-2 text-[10px] font-semibold px-3 py-1.5 rounded-sm transition-all hover:brightness-110"
              style={{ background: 'rgba(41,182,246,0.1)', color: '#29b6f6', border: '1px solid rgba(41,182,246,0.25)' }}
            >
              + Add Line Item
            </button>
          </div>

          {/* Totals */}
          <div className="border-t border-[rgba(255,255,255,0.06)] pt-3 flex flex-col items-end gap-1 mb-4">
            <div className="flex gap-8 text-xs">
              <span className="text-[rgba(255,255,255,0.4)]">Subtotal</span>
              <span className="font-mono text-[rgba(255,255,255,0.7)]">${subtotal.toLocaleString()}</span>
            </div>
            <div className="flex gap-8 text-xs">
              <span className="text-[rgba(255,255,255,0.4)]">Tax (0%)</span>
              <span className="font-mono text-[rgba(255,255,255,0.7)]">$0</span>
            </div>
            <div className="flex gap-8 text-sm font-bold border-t border-[rgba(255,255,255,0.08)] pt-1 mt-1">
              <span className="text-[rgba(255,255,255,0.7)]">Total</span>
              <span className="font-mono text-[#ff6b1a]">${subtotal.toLocaleString()}</span>
            </div>
          </div>

          <button
            className="px-5 py-2 text-xs font-bold uppercase tracking-widest rounded-sm transition-all hover:brightness-110"
            style={{ background: '#ff6b1a', color: '#000' }}
          >
            Generate Invoice
          </button>
        </Panel>
      </motion.div>

      {/* MODULE 3 — Recent Invoices */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <Panel>
          <SectionHeader number="3" title="Recent Invoices" />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.06)]">
                  {['Invoice #', 'Client', 'Amount', 'Date', 'Due', 'Status'].map((h) => (
                    <th key={h} className="text-left py-1.5 px-2 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {INVOICES.map((inv, i) => (
                  <tr key={i} className="border-b border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.02)]">
                    <td className="py-2 px-2 font-mono text-[rgba(255,107,26,0.8)] text-[11px]">{inv.num}</td>
                    <td className="py-2 px-2 text-[rgba(255,255,255,0.75)]">{inv.client}</td>
                    <td className="py-2 px-2 font-mono text-[rgba(255,255,255,0.85)] font-semibold">{inv.amount}</td>
                    <td className="py-2 px-2 text-[rgba(255,255,255,0.45)]">{inv.date}</td>
                    <td className="py-2 px-2 text-[rgba(255,255,255,0.45)]">{inv.due}</td>
                    <td className="py-2 px-2">
                      <Badge
                        label={inv.status}
                        status={inv.status === 'Paid' ? 'ok' : 'warn'}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 4 — Payment Tracking */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Panel>
          <SectionHeader number="4" title="Payment Tracking" sub="outstanding invoices" />
          <div className="space-y-3">
            {OUTSTANDING.map((inv, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-sm" style={{ background: 'rgba(255,152,0,0.06)', border: '1px solid rgba(255,152,0,0.2)' }}>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[rgba(255,255,255,0.85)]">{inv.num}</span>
                    <span className="text-[10px] text-[rgba(255,255,255,0.45)]">{inv.client}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="font-mono text-sm font-bold text-[#ff9800]">{inv.amount}</span>
                    <span className="text-[10px] text-[rgba(255,255,255,0.35)]">Due {inv.due}</span>
                    <Badge label="8 days overdue" status="warn" />
                  </div>
                </div>
                <button
                  className="text-[10px] font-bold px-3 py-1.5 rounded-sm uppercase tracking-wider transition-all hover:brightness-110"
                  style={{ background: 'rgba(255,152,0,0.15)', color: '#ff9800', border: '1px solid rgba(255,152,0,0.35)' }}
                >
                  Send Reminder
                </button>
              </div>
            ))}
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 5 — Invoice Settings */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <Panel>
          <SectionHeader number="5" title="Invoice Settings" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              { label: 'Company Name', key: 'company' as const },
              { label: 'Address', key: 'address' as const },
              { label: 'Payment Terms', key: 'terms' as const },
              { label: 'Late Fee Policy', key: 'lateFee' as const },
            ].map((field) => (
              <div key={field.key} className="flex flex-col gap-1">
                <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">{field.label}</label>
                <input
                  type="text"
                  value={settings[field.key]}
                  onChange={(e) => setSettings({ ...settings, [field.key]: e.target.value })}
                  className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a]"
                />
              </div>
            ))}
          </div>
          <div className="mt-4">
            <button
              className="px-4 py-2 text-xs font-bold uppercase tracking-widest rounded-sm transition-all hover:brightness-110"
              style={{ background: '#ff6b1a', color: '#000' }}
            >
              Save Settings
            </button>
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
