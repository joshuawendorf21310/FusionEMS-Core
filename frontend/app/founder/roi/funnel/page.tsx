'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="border-b border-border-subtle pb-2 mb-4">
      <div className="flex items-baseline gap-3">
        <span className="text-[10px] font-bold text-orange-dim font-mono">MODULE {number}</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-[rgba(255,255,255,0.85)]">{title}</h2>
        {sub && <span className="text-xs text-[rgba(255,255,255,0.35)]">{sub}</span>}
      </div>
    </div>
  );
}

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-bg-panel border border-border-DEFAULT p-4 ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

export default function FunnelPage() {
  const [funnelData, setFunnelData] = useState<any[]>([]);
  const [kpis, setKpis] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;

    Promise.all([
      fetch(`${API}/api/v1/roi-funnel/conversion-funnel`, { headers }).then(r => r.json()),
      fetch(`${API}/api/v1/roi-funnel/conversion-kpis`, { headers }).then(r => r.json())
    ]).then(([funnelRes, kpisRes]) => {
      if (funnelRes.funnel) setFunnelData(funnelRes.funnel);
      if (kpisRes) setKpis(kpisRes);
    }).catch(console.error);
  }, []);

  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-6 space-y-6">
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-bold text-orange-dim font-mono tracking-widest uppercase">
            MODULE 09 · ROI & GROWTH
          </span>
          <Link href="/founder/roi" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-orange transition-colors">
            ← Back to ROI
          </Link>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary" style={{ textShadow: '0 0 24px rgba(255,107,26,0.3)' }}>
          Funnel Intelligence
        </h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Lead tracking · conversion velocity · pipeline stages</p>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Total Events', value: kpis?.total_events ?? '-' },
            { label: 'Total Proposals', value: kpis?.total_proposals ?? '-' },
            { label: 'Active Subs', value: kpis?.active_subscriptions ?? '-' },
            { label: 'Conversion Rate', value: `${kpis?.proposal_to_paid_conversion_pct ?? '-'}%` },
          ].map((s) => (
            <Panel key={s.label} className="flex flex-col gap-1">
              <span className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">{s.label}</span>
              <span className="text-xl font-bold" style={{ color: 'var(--color-status-info)' }}>{s.value}</span>
            </Panel>
          ))}
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Panel>
          <SectionHeader number="2" title="Funnel Stages" />
          <div className="space-y-4">
            {funnelData.length === 0 ? <p className="text-xs text-[rgba(255,255,255,0.35)]">No events logged yet.</p> : null}
            {funnelData.map((s, i) => {
              const maxCount = Math.max(...funnelData.map(d => d.count), 1);
              const width = Math.max((s.count / maxCount) * 100, 5);
              return (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-32 text-xs text-[rgba(255,255,255,0.7)] uppercase tracking-wider">{s.stage}</div>
                  <div className="flex-1 h-3 bg-[rgba(255,255,255,0.05)] rounded-sm overflow-hidden relative">
                    <div 
                      className="absolute top-0 left-0 h-full transition-all duration-1000"
                      style={{ width: `${width}%`, background: 'var(--color-brand-cyan)' }}
                    />
                  </div>
                  <div className="w-16 text-right font-mono text-xs">{s.count}</div>
                </div>
              );
            })}
          </div>
        </Panel>
      </motion.div>

      <div className="pt-2">
        <Link href="/founder/roi" className="text-[11px] text-[rgba(255,255,255,0.35)] hover:text-orange transition-colors">
          ← Back to ROI Overview
        </Link>
      </div>
    </div>
  );
}
