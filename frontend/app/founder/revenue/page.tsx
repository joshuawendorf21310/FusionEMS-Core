'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/revenue/billing-intelligence', label: 'Billing Intelligence', desc: 'Clean claim rate, denial patterns, revenue optimization', color: 'var(--color-system-billing)' },
  { href: '/founder/revenue/stripe', label: 'Stripe Dashboard', desc: 'MRR, ARR, subscription management, payment health', color: 'var(--color-system-billing)' },
  { href: '/founder/revenue/ar-aging', label: 'AR Aging', desc: 'Outstanding claims by bucket, collection rates, aging trends', color: 'var(--color-system-billing)' },
  { href: '/founder/revenue/forecast', label: 'Revenue Forecast', desc: 'Growth projections, scenario modeling, ARR targets', color: 'var(--color-system-billing)' },
];

export default function RevenuePage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">DOMAIN 2 · REVENUE & BILLING</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Revenue & Billing</h1>
        <p className="text-xs text-text-muted mt-0.5">Billing intelligence · Stripe · AR aging · forecasting</p>
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
