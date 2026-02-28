'use client';
import Link from 'next/link';
import { QuantumEmptyState } from '@/components/ui';

export default function FieldMaskingPage() {
  return (
    <div className="p-5 min-h-screen">
      <div className="hud-rail pb-3 mb-6">
        <div className="micro-caps mb-1">Security</div>
        <h1 className="text-h2 font-bold text-text-primary">Field Masking</h1>
        <p className="text-body text-text-muted mt-1">Configure PHI field masking rules by role and data classification.</p>
      </div>
      <div className="bg-bg-panel border border-border-DEFAULT chamfer-8 shadow-elevation-1">
        <QuantumEmptyState
          title="Not Yet Configured"
          description="This module is scheduled for an upcoming release. Contact your account manager for early access."
          icon={
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="6" y="10" width="36" height="28" rx="2" />
              <path d="M6 18h36M16 10V6M32 10V6" />
              <circle cx="24" cy="30" r="4" />
            </svg>
          }
          action={
            <Link
              href="/founder"
              className="inline-flex items-center gap-2 px-4 py-2 text-label font-label uppercase tracking-[var(--tracking-label)] text-orange hover:text-orange-bright transition-colors duration-fast"
            >
              &larr; Back to Command Center
            </Link>
          }
        />
      </div>
    </div>
  );
}
