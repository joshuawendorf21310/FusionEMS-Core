'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/comms/inbox', label: 'Unified Inbox', desc: 'All inbound communications: email, SMS, fax in one place', color: '#4caf50' },
  { href: '/founder/comms/phone-system', label: 'Phone System', desc: 'AI voice system, call routing, inbound call management', color: '#4caf50' },
  { href: '/founder/comms/script-builder', label: 'Script Builder', desc: 'Build AI call scripts and response templates', color: '#4caf50' },
  { href: '/founder/comms/broadcast', label: 'Broadcast Manager', desc: 'Send bulk SMS, email or voice broadcasts to agencies', color: '#4caf50' },
];

export default function CommsPage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">DOMAIN 4 · COMMUNICATIONS</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">Communications</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">Unified inbox · AI voice · script builder · broadcast manager</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {LINKS.map((l, i) => (
          <motion.div key={l.href} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
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
