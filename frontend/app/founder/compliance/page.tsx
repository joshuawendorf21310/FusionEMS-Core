'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/compliance/nemsis', label: 'NEMSIS Manager', desc: 'NEMSIS v3.5 validation, element mapping, XML export', color: 'var(--q-yellow)' },
  { href: '/founder/compliance/export-status', label: 'Export Status', desc: '100-module export intelligence and state submission control', color: 'var(--q-yellow)' },
  { href: '/founder/compliance/niers', label: 'NIERS Manager', desc: 'Fire data compliance, crosswalk builder, heatmap', color: 'var(--q-yellow)' },
  { href: '/founder/compliance/certification', label: 'Certification Monitor', desc: 'State certifications, credential tracking, expiry alerts', color: 'var(--q-yellow)' },
];

export default function CompliancePage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">DOMAIN 5 · COMPLIANCE</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Compliance</h1>
        <p className="text-xs text-text-muted mt-0.5">NEMSIS · NIERS · export status · certification</p>
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
