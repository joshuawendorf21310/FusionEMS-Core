'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/security/role-builder', label: 'Role Builder', desc: 'Define RBAC roles, permissions, and module access controls', color: '#e53935' },
  { href: '/founder/security/field-masking', label: 'Field Masking', desc: 'Configure PHI field masking rules by role and context', color: '#e53935' },
  { href: '/founder/security/access-logs', label: 'Access Logs', desc: 'Immutable audit log of all PHI access and export events', color: '#e53935' },
  { href: '/founder/security/policy-sandbox', label: 'Policy Sandbox', desc: 'Test OPA policy rules before deploying to production', color: '#e53935' },
];

export default function SecurityPage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">DOMAIN 6 · VISIBILITY & SECURITY</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">Visibility & Security</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">Role builder · field masking · access logs · OPA policy sandbox</p>
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
