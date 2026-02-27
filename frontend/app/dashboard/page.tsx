'use client';

import React, { useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import { MetricPlate, PlateCard } from '@/components/ui/PlateCard';
import { StatusChip } from '@/components/ui/StatusChip';
import { LiveEventFeed } from '@/components/LiveEventFeed';
import { getExecutiveSummary } from '@/services/api';

// ─── Types ───────────────────────────────────────────────────────────────────

interface ExecutiveSummary {
  mrr:             number;
  clients:         number;
  system_status:   string;
  active_units:    number;
  open_incidents:  number;
  pending_claims:  number;
  collection_rate: number;
}

type ModuleStatus = 'active' | 'warning' | 'critical' | 'info' | 'neutral';

interface SystemModule {
  name:   string;
  status: ModuleStatus;
  detail: string;
}

// ─── Static module list (status would be API-driven in production) ────────────

const SYSTEM_MODULES: SystemModule[] = [
  { name: 'Billing Engine',    status: 'active',   detail: 'Operational'      },
  { name: 'Compliance Layer',  status: 'active',   detail: 'Monitoring'       },
  { name: 'CAD Integration',   status: 'warning',  detail: 'Latency elevated' },
  { name: 'Fleet Tracking',    status: 'active',   detail: 'Operational'      },
  { name: 'Auth System',       status: 'active',   detail: 'Operational'      },
  { name: 'NEMSIS Export',     status: 'info',     detail: 'Batch pending'    },
];

// ─── Skeleton ────────────────────────────────────────────────────────────────

function SkeletonPlate() {
  return (
    <div
      className="chamfer-8 border animate-pulse"
      style={{
        height:          96,
        backgroundColor: 'var(--color-bg-panel)',
        borderColor:     'var(--color-border-subtle)',
      }}
    />
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year:    'numeric',
    month:   'long',
    day:     'numeric',
  });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    Promise.all([getExecutiveSummary()])
      .then(([summaryData]) => {
        if (cancelled) return;
        setSummary(summaryData as ExecutiveSummary);
      })
      .catch(() => {
        if (cancelled) return;
        setError('Failed to load dashboard data. Check your connection and try again.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  return (
    <AppShell>
      {/* ── Page header ────────────────────────────────────────────────── */}
      <div
        className="hud-rail mb-6 flex items-center justify-between pb-4"
        style={{ borderBottom: '1px solid var(--color-border-default)' }}
      >
        <div>
          <h1
            className="label-caps"
            style={{
              fontSize:  'var(--text-h2)',
              color:     'var(--color-text-primary)',
            }}
          >
            Operations Dashboard
          </h1>
          <p
            className="micro-caps mt-1"
            style={{ color: 'var(--color-text-muted)' }}
          >
            {today}
          </p>
        </div>

        <div
          className="chamfer-4 px-3 py-1.5"
          style={{
            backgroundColor: 'var(--color-brand-orange-ghost)',
            border:          '1px solid var(--color-brand-orange-glow)',
          }}
        >
          <span
            className="micro-caps"
            style={{ color: 'var(--color-brand-orange)' }}
          >
            Live
          </span>
        </div>
      </div>

      {/* ── Error state ────────────────────────────────────────────────── */}
      {error && (
        <PlateCard critical padding="md" className="mb-6">
          <p
            className="micro-caps"
            style={{ color: 'var(--color-brand-red)' }}
          >
            {error}
          </p>
        </PlateCard>
      )}

      {/* ── KPI row ────────────────────────────────────────────────────── */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => <SkeletonPlate key={i} />)
        ) : summary ? (
          <>
            <MetricPlate
              label="MRR"
              value={`$${(summary.mrr / 1000).toFixed(0)}K`}
              accent="billing"
            />
            <MetricPlate
              label="Active Clients"
              value={summary.clients}
              accent="compliance"
            />
            <MetricPlate
              label="Active Units"
              value={summary.active_units}
              accent="fleet"
            />
            <MetricPlate
              label="Open Incidents"
              value={summary.open_incidents}
              accent="cad"
              trendDirection={summary.open_incidents > 0 ? 'up' : 'neutral'}
              trendPositive={false}
              trend={summary.open_incidents > 0 ? `${summary.open_incidents} open` : undefined}
            />
            <MetricPlate
              label="Pending Claims"
              value={summary.pending_claims}
              accent="billing"
            />
            <MetricPlate
              label="Collection Rate"
              value={`${summary.collection_rate}%`}
              accent="active"
              trendDirection="up"
              trendPositive
              trend="vs prior period"
            />
          </>
        ) : null}
      </div>

      {/* ── Main content: two-column ────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">

        {/* Left 2/3 — Live event feed */}
        <div className="lg:col-span-2">
          <PlateCard
            header="Live Event Feed"
            accent="cad"
            padding="md"
          >
            {loading ? (
              <div className="flex flex-col gap-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div
                    key={i}
                    className="chamfer-4 animate-pulse"
                    style={{
                      height:          48,
                      backgroundColor: 'var(--color-bg-input)',
                    }}
                  />
                ))}
              </div>
            ) : (
              <LiveEventFeed maxEvents={20} />
            )}
          </PlateCard>
        </div>

        {/* Right 1/3 — System Status */}
        <div className="lg:col-span-1">
          <PlateCard
            header="System Status"
            accent="compliance"
            padding="none"
          >
            <div className="flex flex-col divide-y" style={{ borderColor: 'var(--color-border-subtle)' }}>
              {SYSTEM_MODULES.map((mod) => (
                <div
                  key={mod.name}
                  className="flex items-center justify-between px-4 py-3 gap-3"
                >
                  <div className="min-w-0">
                    <p
                      className="truncate"
                      style={{
                        fontFamily: 'var(--font-sans)',
                        fontSize:   'var(--text-body)',
                        color:      'var(--color-text-primary)',
                      }}
                    >
                      {mod.name}
                    </p>
                    <p
                      className="micro-caps mt-0.5"
                      style={{ color: 'var(--color-text-muted)' }}
                    >
                      {mod.detail}
                    </p>
                  </div>
                  <StatusChip status={mod.status} size="sm">
                    {mod.status}
                  </StatusChip>
                </div>
              ))}
            </div>
          </PlateCard>
        </div>

      </div>
    </AppShell>
  );
}
