'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/roi/analytics', label: 'ROI Analytics', desc: 'MRR, ARR, agency breakdown, payer mix, churn risk', color: '#ff9800' },
  { href: '/founder/roi/funnel', label: 'Funnel Dashboard', desc: 'Lead pipeline, conversion rates, deal velocity', color: '#ff9800' },
  { href: '/founder/roi/pricing-simulator', label: 'Pricing Simulator', desc: 'Compare FusionEMS vs % billing model ROI', color: '#ff9800' },
  { href: '/founder/roi/proposals', label: 'Proposal Tracker', desc: 'Track sent proposals, follow-ups, acceptance rate', color: '#ff9800' },
];

export default function ROIPage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">DOMAIN 8 · ROI & SALES</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">ROI & Sales</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">Pipeline · simulator · proposals · analytics</p>
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
