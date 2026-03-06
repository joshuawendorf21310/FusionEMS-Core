'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { QuantumEmptyState } from '@/components/ui';
import { QuantumCardSkeleton } from '@/components/ui';

interface PortalMetadata {
  stat_cards?: Array<{ label: string; value: number | string; href: string }>;
}

export default function PortalDashboardPage() {
  const [data, setData] = useState<PortalMetadata | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const API = process.env.NEXT_PUBLIC_API_URL || '';
    fetch(`${API}/api/v1/metrics`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('qs_token') || ''}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error('API down');
        return res.json();
      })
      .then((json) => {
        setData(json.portal || { stat_cards: [] });
      })
      .catch((e) => {
        console.warn('Failed to fetch agency dashboard', e);
        setData({ stat_cards: [] });
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-text-primary">Agency Dashboard</h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-0.5">Live real-time operational data</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <QuantumCardSkeleton />
          <QuantumCardSkeleton />
          <QuantumCardSkeleton />
        </div>
      ) : (!data?.stat_cards || data.stat_cards.length === 0) ? (
        <QuantumEmptyState
          title="No operational data available"
          description="Your agency currently has no active incidents or claims. Data will appear once the API populates metrics."
          icon="activity"
          action={<button onClick={() => window.location.reload()} className="quantum-btn mt-4">Refresh Data</button>}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.stat_cards.map((card) => (
            <Link
              key={card.href}
              href={card.href}
              className="group block bg-bg-void border border-border-DEFAULT rounded-sm p-5 hover:border-[rgba(255,107,26,0.35)] transition-colors"
            >
              <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.4)] mb-3 group-hover:text-[rgba(255,107,26,0.7)] transition-colors">
                {card.label}
              </div>
              <div className="text-3xl font-bold text-text-primary">{card.value}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
