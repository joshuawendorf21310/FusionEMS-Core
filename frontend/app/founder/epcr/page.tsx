'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  {
    href: '/founder/epcr/charts',
    label: 'Charts',
    desc: 'Create and manage patient care reports',
    color: '#22d3ee',
  },
  {
    href: '/founder/epcr/compliance-studio',
    label: 'Compliance Studio',
    desc: 'NEMSIS resource packs, validation, AI fix list',
    color: '#22d3ee',
  },
  {
    href: '/founder/epcr/scenarios',
    label: 'Test Scenarios',
    desc: 'C&S vendor test case browser and runner',
    color: '#22d3ee',
  },
  {
    href: '/founder/epcr/analytics',
    label: 'Analytics',
    desc: 'Completeness scores, validation rates, trends',
    color: '#22d3ee',
  },
  {
    href: '/founder/epcr/patch-tasks',
    label: 'Patch Tasks',
    desc: 'AI-generated fix tasks from validation issues',
    color: '#22d3ee',
  },
  {
    href: '/founder/epcr/settings',
    label: 'Settings',
    desc: 'Resource packs, AI cost controls, form layout',
    color: '#22d3ee',
  },
];

export default function EpcrPage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(34,211,238,0.6)] mb-1">
          DOMAIN · ePCR & NEMSIS
        </div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">ePCR &amp; NEMSIS</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">
          Wisconsin-first charting, compliance, and certification
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {LINKS.map((l) => (
          <motion.div key={l.href} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <Link
              href={l.href}
              className="block bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-5 hover:border-[rgba(34,211,238,0.3)] transition-colors"
              style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
            >
              <div className="text-sm font-bold mb-1" style={{ color: l.color }}>
                {l.label}
              </div>
              <div className="text-xs text-[rgba(255,255,255,0.45)]">{l.desc}</div>
            </Link>
          </motion.div>
        ))}
      </div>
      <Link href="/founder" className="text-xs text-[rgba(34,211,238,0.6)] hover:text-[#22d3ee]">
        ← Back to Founder Command OS
      </Link>
    </div>
  );
}
