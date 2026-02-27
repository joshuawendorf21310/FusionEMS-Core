'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/infra/ecs', label: 'ECS Health', desc: 'Fargate cluster, task health, ALB metrics, auto scaling', color: '#94a3b8' },
  { href: '/founder/infra/rds', label: 'RDS Health', desc: 'PostgreSQL status, connection pools, backups, slow queries', color: '#94a3b8' },
  { href: '/founder/infra/ai-gpu', label: 'AI GPU Monitor', desc: 'Model inference jobs, memory allocation, throughput', color: '#94a3b8' },
  { href: '/founder/infra/cost', label: 'Cost Dashboard', desc: 'AWS spend by service, budget tracking, optimization tips', color: '#94a3b8' },
  { href: '/founder/infra/incident', label: 'Incident Control', desc: 'System status, incident history, playbooks, on-call', color: '#94a3b8' },
];

export default function InfraPage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">DOMAIN 10 · INFRASTRUCTURE</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">Infrastructure</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">ECS · RDS · AI GPU · AWS costs · incident control</p>
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
