'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/executive/daily-brief', label: 'Daily AI Brief', desc: 'AI-generated briefing with top action items updated hourly', color: 'var(--q-orange)' },
  { href: '/founder/executive/risk-monitor', label: 'Risk Monitor', desc: 'Churn risk, compliance gaps, revenue risk, infra alerts', color: 'var(--q-orange)' },
];

export default function ExecutivePage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">DOMAIN 1 · EXECUTIVE</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Executive Command</h1>
        <p className="text-xs text-text-muted mt-0.5">Daily AI brief · risk monitor · platform overview</p>
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
