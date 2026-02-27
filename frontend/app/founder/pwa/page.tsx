'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/pwa/crewlink', label: 'CrewLink', desc: 'Mobile field app for crew, ePCR entry, and real-time sync', color: '#3b82f6' },
  { href: '/founder/pwa/scheduling', label: 'Scheduling', desc: 'Mobile shift scheduling and crew coverage interface', color: '#3b82f6' },
  { href: '/founder/pwa/deployment', label: 'Deployment Monitor', desc: 'PWA version control, device updates, feature flags', color: '#3b82f6' },
  { href: '/founder/pwa/device-analytics', label: 'Device Analytics', desc: 'Device fleet health, OS distribution, usage heatmap', color: '#3b82f6' },
];

export default function PWAPage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">DOMAIN 9 · PWA & MOBILE</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">PWA & Mobile</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">Field app deployment · crew scheduling · device analytics</p>
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
