'use client';
import Link from 'next/link';

export default function NemsisPage() {
  return (
    <div className="p-5 min-h-screen">
      <div className="hud-rail pb-3 mb-6">
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">5 · COMPLIANCE</div>
        <h1 className="text-lg font-black uppercase tracking-wider text-white">NEMSIS Version Manager</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">Dataset schema viewer · Version compatibility · Required field tracker</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
        {['Configuration', 'Analytics', 'Audit Log'].map((f) => (
          <div key={f} className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
            <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-2">{f}</div>
            <div className="h-16 flex items-center justify-center text-[rgba(255,255,255,0.2)] text-xs">Module panel · coming next release</div>
          </div>
        ))}
      </div>
      <Link href="/founder" className="text-xs text-[rgba(255,107,26,0.6)] hover:text-[#ff6b1a]">← Back to Founder Command OS</Link>
    </div>
  );
}
