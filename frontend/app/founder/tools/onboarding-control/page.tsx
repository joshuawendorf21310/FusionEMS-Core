'use client';
import { QuantumTableSkeleton, QuantumCardSkeleton } from '@/components/ui';

import { useState, useEffect, useRef, useCallback } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return 'Bearer ' + (localStorage.getItem('qs_token') || '');
}

// ─── Types ────────────────────────────────────────────────────────────────────

type AppStatus =
  | 'pending'
  | 'legal_signed'
  | 'paid'
  | 'provisioning'
  | 'active'
  | 'failed'
  | 'revoked';

interface OnboardingApp {
  id: string;
  agency_name: string;
  contact_email: string;
  state: string;
  plan: string;
  status: AppStatus;
  legal_status: 'not_sent' | 'sent' | 'signed';
  created_at: string;
  [key: string]: unknown;
}

interface SignEvent {
  id: string;
  event_type: string;
  occurred_at: string;
  signer_name?: string;
  signer_email?: string;
}

// ─── Toast ────────────────────────────────────────────────────────────────────

interface ToastItem {
  id: number;
  msg: string;
  type: 'success' | 'error';
}

function Toast({ items }: { items: ToastItem[] }) {
  if (!items.length) return null;
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
      {items.map((t) => (
        <div
          key={t.id}
          className="px-4 py-2.5 rounded-sm text-xs font-semibold shadow-lg"
          style={{
            background: t.type === 'success' ? 'rgba(76,175,80,0.18)' : 'rgba(229,57,53,0.18)',
            border: `1px solid ${t.type === 'success' ? 'rgba(76,175,80,0.4)' : 'rgba(229,57,53,0.4)'}`,
            color: t.type === 'success' ? '#4caf50' : '#e53935',
          }}
        >
          {t.msg}
        </div>
      ))}
    </div>
  );
}

function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const counter = useRef(0);
  const push = useCallback((msg: string, type: 'success' | 'error' = 'success') => {
    const id = ++counter.current;
    setToasts((prev) => [...prev, { id, msg, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3000);
  }, []);
  return { toasts, push };
}

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_MAP: Record<AppStatus, { label: string; color: string; bg: string; pulse?: boolean }> = {
  pending:       { label: 'PENDING',       color: 'rgba(255,255,255,0.5)', bg: 'rgba(255,255,255,0.07)' },
  legal_signed:  { label: 'LEGAL SIGNED',  color: 'var(--color-system-billing)',               bg: 'rgba(34,211,238,0.12)' },
  paid:          { label: 'PAID',          color: 'var(--color-status-info)',               bg: 'rgba(41,182,246,0.12)' },
  provisioning:  { label: 'PROVISIONING',  color: 'var(--q-yellow)',               bg: 'rgba(255,152,0,0.12)',  pulse: true },
  active:        { label: 'ACTIVE',        color: 'var(--q-green)',               bg: 'rgba(76,175,80,0.12)' },
  failed:        { label: 'FAILED',        color: 'var(--q-red)',               bg: 'rgba(229,57,53,0.12)' },
  revoked:       { label: 'REVOKED',       color: '#b71c1c',               bg: 'rgba(183,28,28,0.18)' },
};

const LEGAL_MAP: Record<string, { label: string; color: string; bg: string }> = {
  not_sent: { label: 'NOT SENT', color: 'rgba(255,255,255,0.35)', bg: 'rgba(255,255,255,0.05)' },
  sent:     { label: 'SENT',     color: 'var(--q-yellow)',                bg: 'rgba(255,152,0,0.12)' },
  signed:   { label: 'SIGNED',   color: 'var(--q-green)',               bg: 'rgba(76,175,80,0.12)' },
};

function StatusBadge({ status }: { status: AppStatus }) {
  const s = STATUS_MAP[status] ?? STATUS_MAP.pending;
  return (
    <span
      className={`px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-sm whitespace-nowrap${s.pulse ? ' animate-pulse' : ''}`}
      style={{ color: s.color, background: s.bg }}
    >
      {s.label}
    </span>
  );
}

function LegalBadge({ legalStatus }: { legalStatus: string }) {
  const s = LEGAL_MAP[legalStatus] ?? LEGAL_MAP.not_sent;
  return (
    <span
      className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-sm whitespace-nowrap"
      style={{ color: s.color, background: s.bg }}
    >
      {s.label}
    </span>
  );
}

// ─── Confirm Modal ────────────────────────────────────────────────────────────

interface ConfirmModalProps {
  title: string;
  message: string;
  confirmLabel: string;
  confirmColor?: string;
  children?: React.ReactNode;
  onConfirm: (extra?: string) => void;
  onCancel: () => void;
}

function ConfirmModal({
  title,
  message,
  confirmLabel,
  confirmColor = '#ff6b1a',
  children,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const [extra, setExtra] = useState('');
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }}>
      <div
        className="bg-bg-base border border-[rgba(255,255,255,0.12)] rounded-sm p-5 w-full max-w-sm shadow-2xl"
        style={{ boxShadow: '0 0 40px rgba(0,0,0,0.7)' }}
      >
        <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary mb-2">{title}</h3>
        <p className="text-[11px] text-[rgba(255,255,255,0.55)] mb-4 leading-relaxed">{message}</p>
        {children && <div className="mb-4">{children}</div>}
        {title.toLowerCase().includes('revoke') && (
          <div className="mb-4">
            <label className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.4)] block mb-1">
              Reason (required)
            </label>
            <input
              value={extra}
              onChange={(e) => setExtra(e.target.value)}
              placeholder="Enter revocation reason…"
              className="w-full bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-xs text-text-primary px-3 py-2 rounded-sm outline-none focus:border-[rgba(255,107,26,0.4)] placeholder:text-[rgba(255,255,255,0.2)]"
            />
          </div>
        )}
        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            className="h-8 px-4 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
            style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.5)' }}
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(extra || undefined)}
            className="h-8 px-4 text-[10px] font-bold uppercase tracking-wider rounded-sm transition-all hover:brightness-110"
            style={{ background: confirmColor, color: confirmColor === '#e53935' || confirmColor === '#b71c1c' ? '#fff' : '#000' }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Detail Drawer ────────────────────────────────────────────────────────────

function DetailDrawer({
  app,
  signEvents,
  loadingEvents,
  onClose,
  onResendLegal,
  onResendCheckout,
  onManualProvision,
  onRevoke,
}: {
  app: OnboardingApp;
  signEvents: SignEvent[];
  loadingEvents: boolean;
  onClose: () => void;
  onResendLegal: (app: OnboardingApp) => void;
  onResendCheckout: (app: OnboardingApp) => void;
  onManualProvision: (app: OnboardingApp) => void;
  onRevoke: (app: OnboardingApp) => void;
}) {
  const fields: { label: string; value: string }[] = [
    { label: 'Application ID', value: app.id },
    { label: 'Agency Name', value: app.agency_name },
    { label: 'Contact Email', value: app.contact_email },
    { label: 'State', value: app.state },
    { label: 'Plan', value: app.plan },
    { label: 'Created At', value: new Date(app.created_at).toLocaleString() },
  ];

  return (
    <div
      className="fixed inset-0 z-40 flex justify-end"
      style={{ background: 'rgba(0,0,0,0.4)' }}
      onClick={onClose}
    >
      <div
        className="bg-bg-base border-l border-border-DEFAULT h-full overflow-y-auto flex flex-col"
        style={{ width: 400 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer header */}
        <div className="px-5 py-4 border-b border-border-DEFAULT flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Application Detail</h2>
            <p className="text-[10px] text-text-muted mt-0.5">{app.agency_name}</p>
          </div>
          <button
            onClick={onClose}
            className="text-[rgba(255,255,255,0.4)] hover:text-text-primary transition-colors text-lg leading-none"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 px-5 py-4 space-y-5">
          {/* Fields */}
          <div>
            <p className="text-[9px] uppercase tracking-[0.18em] text-orange-dim mb-3">
              Application Data
            </p>
            <div className="space-y-2.5">
              {fields.map(({ label, value }) => (
                <div key={label} className="flex items-start justify-between gap-3">
                  <span className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] flex-shrink-0 mt-0.5">
                    {label}
                  </span>
                  <span className="text-xs text-[rgba(255,255,255,0.8)] text-right font-mono break-all">
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Status */}
          <div className="flex items-center justify-between py-3 border-y border-border-subtle">
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)]">Status</span>
              <StatusBadge status={app.status} />
            </div>
            <div className="flex flex-col gap-1.5 items-end">
              <span className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)]">Legal</span>
              <LegalBadge legalStatus={app.legal_status} />
            </div>
          </div>

          {/* Sign Events Timeline */}
          <div>
            <p className="text-[9px] uppercase tracking-[0.18em] text-orange-dim mb-3">
              Legal Packet Sign Events
            </p>
            {loadingEvents ? (
              <p className="text-[11px] text-[rgba(255,255,255,0.3)]">Loading events…</p>
            ) : signEvents.length === 0 ? (
              <p className="text-[11px] text-[rgba(255,255,255,0.3)]">No sign events recorded</p>
            ) : (
              <div className="space-y-2">
                {signEvents.map((ev, i) => (
                  <div
                    key={ev.id}
                    className="flex gap-3 items-start"
                  >
                    <div className="flex flex-col items-center pt-1">
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ background: i === 0 ? '#ff6b1a' : 'rgba(255,255,255,0.2)' }}
                      />
                      {i < signEvents.length - 1 && (
                        <span
                          className="w-px flex-1 mt-1"
                          style={{ background: 'rgba(255,255,255,0.08)', minHeight: 16 }}
                        />
                      )}
                    </div>
                    <div className="pb-1">
                      <p className="text-[11px] font-semibold text-[rgba(255,255,255,0.8)] uppercase tracking-wide">
                        {ev.event_type}
                      </p>
                      {ev.signer_name && (
                        <p className="text-[10px] text-[rgba(255,255,255,0.45)]">
                          {ev.signer_name}{ev.signer_email ? ` · ${ev.signer_email}` : ''}
                        </p>
                      )}
                      <p className="text-[10px] font-mono text-[rgba(255,255,255,0.3)]">
                        {new Date(ev.occurred_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Action buttons repeated */}
          <div>
            <p className="text-[9px] uppercase tracking-[0.18em] text-orange-dim mb-3">
              Actions
            </p>
            <div className="flex flex-wrap gap-2">
              {app.legal_status === 'not_sent' && (
                <button
                  onClick={() => onResendLegal(app)}
                  className="h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
                  style={{ background: 'rgba(255,152,0,0.12)', border: '1px solid rgba(255,152,0,0.3)', color: 'var(--q-yellow)' }}
                >
                  Send Legal
                </button>
              )}
              {app.legal_status === 'sent' && app.status === 'legal_signed' && (
                <button
                  onClick={() => onResendCheckout(app)}
                  className="h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
                  style={{ background: 'rgba(41,182,246,0.1)', border: '1px solid rgba(41,182,246,0.25)', color: 'var(--color-status-info)' }}
                >
                  Resend Checkout
                </button>
              )}
              {app.status === 'paid' && (
                <button
                  onClick={() => onManualProvision(app)}
                  className="h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
                  style={{ background: 'rgba(255,107,26,0.12)', border: '1px solid rgba(255,107,26,0.3)', color: 'var(--q-orange)' }}
                >
                  Manual Provision
                </button>
              )}
              {app.status === 'active' && (
                <button
                  onClick={() => onRevoke(app)}
                  className="h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
                  style={{ background: 'rgba(229,57,53,0.12)', border: '1px solid rgba(229,57,53,0.3)', color: 'var(--q-red)' }}
                >
                  Revoke
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

type StatusFilter = 'all' | AppStatus;

type ConfirmAction =
  | { type: 'provision'; app: OnboardingApp }
  | { type: 'revoke'; app: OnboardingApp };

export default function OnboardingControlPage() {
  const [apps, setApps] = useState<OnboardingApp[]>([]);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  const [detailApp, setDetailApp] = useState<OnboardingApp | null>(null);
  const [signEvents, setSignEvents] = useState<SignEvent[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);

  const [confirm, setConfirm] = useState<ConfirmAction | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const { toasts, push: pushToast } = useToast();

  // ── Fetch apps ─────────────────────────────────────────────────────────────
  const fetchApps = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.set('status', statusFilter);
      if (search.trim()) params.set('q', search.trim());
      const res = await fetch(
        `${API}/api/v1/founder/documents/onboarding-applications?${params.toString()}`,
        { headers: { Authorization: getToken() } }
      );
      if (!res.ok) throw new Error();
      const data = await res.json();
      setApps(Array.isArray(data) ? data : data.applications ?? []);
    } catch {
      pushToast('Failed to load applications', 'error');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search, pushToast]);

  useEffect(() => {
    fetchApps();
  }, [fetchApps]);

  // ── Fetch sign events when detail opens ────────────────────────────────────
  useEffect(() => {
    if (!detailApp) return;
    setSignEvents([]);
    setLoadingEvents(true);
    fetch(`${API}/api/v1/founder/documents/sign-events?application_id=${detailApp.id}`, {
      headers: { Authorization: getToken() },
    })
      .then((r) => r.json())
      .then((d) => setSignEvents(Array.isArray(d) ? d : d.events ?? []))
      .catch((e: unknown) => { console.warn("[fetch error]", e); })
      .finally(() => setLoadingEvents(false));
  }, [detailApp]);

  // ── Actions ────────────────────────────────────────────────────────────────
  async function doResendLegal(app: OnboardingApp) {
    try {
      const r = await fetch(
        `${API}/api/v1/founder/documents/onboarding-applications/${app.id}/resend-legal`,
        { method: 'POST', headers: { Authorization: getToken() } }
      );
      if (!r.ok) throw new Error();
      pushToast('Legal packet sent', 'success');
      fetchApps();
    } catch {
      pushToast('Failed to send legal', 'error');
    }
  }

  async function doResendCheckout(app: OnboardingApp) {
    try {
      const r = await fetch(
        `${API}/api/v1/founder/documents/onboarding-applications/${app.id}/resend-checkout`,
        { method: 'POST', headers: { Authorization: getToken() } }
      );
      if (!r.ok) throw new Error();
      pushToast('Checkout link resent', 'success');
      fetchApps();
    } catch {
      pushToast('Failed to resend checkout', 'error');
    }
  }

  async function doManualProvision(app: OnboardingApp) {
    setConfirm({ type: 'provision', app });
  }

  async function doRevoke(app: OnboardingApp) {
    setConfirm({ type: 'revoke', app });
  }

  async function handleConfirm(reason?: string) {
    if (!confirm) return;
    setActionLoading(true);
    try {
      if (confirm.type === 'provision') {
        const r = await fetch(
          `${API}/api/v1/founder/documents/onboarding-applications/${confirm.app.id}/manual-provision`,
          {
            method: 'POST',
            headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ confirm: true }),
          }
        );
        if (!r.ok) throw new Error();
        pushToast('Provision initiated', 'success');
      } else {
        if (!reason?.trim()) {
          pushToast('Reason is required to revoke', 'error');
          setActionLoading(false);
          return;
        }
        const r = await fetch(
          `${API}/api/v1/founder/documents/onboarding-applications/${confirm.app.id}/revoke`,
          {
            method: 'POST',
            headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason }),
          }
        );
        if (!r.ok) throw new Error();
        pushToast('Application revoked', 'success');
      }
      fetchApps();
      setConfirm(null);
      if (detailApp?.id === confirm.app.id) setDetailApp(null);
    } catch {
      pushToast('Action failed', 'error');
    } finally {
      setActionLoading(false);
    }
  }

  // ── Derived stats ──────────────────────────────────────────────────────────
  const stats = {
    total: apps.length,
    pendingPayment: apps.filter((a) => a.status === 'pending' || a.status === 'legal_signed').length,
    provisioned: apps.filter((a) => a.status === 'active').length,
    revoked: apps.filter((a) => a.status === 'revoked').length,
  };

  const STATUS_OPTS: { value: StatusFilter; label: string }[] = [
    { value: 'all', label: 'All Statuses' },
    { value: 'pending', label: 'Pending' },
    { value: 'legal_signed', label: 'Legal Signed' },
    { value: 'paid', label: 'Paid' },
    { value: 'provisioning', label: 'Provisioning' },
    { value: 'active', label: 'Active' },
    { value: 'failed', label: 'Failed' },
    { value: 'revoked', label: 'Revoked' },
  ];

  return (
    <div className="min-h-screen bg-bg-void text-text-primary p-5">
      <Toast items={toasts} />

      {/* Confirm modal */}
      {confirm && (
        <ConfirmModal
          title={confirm.type === 'provision' ? 'Manual Provision' : 'Revoke Application'}
          message={
            confirm.type === 'provision'
              ? `Manually provision "${confirm.app.agency_name}"? This will trigger the full provisioning pipeline.`
              : `Permanently revoke access for "${confirm.app.agency_name}"? This action cannot be undone.`
          }
          confirmLabel={confirm.type === 'provision' ? 'Provision' : 'Revoke'}
          confirmColor={confirm.type === 'provision' ? '#ff6b1a' : '#e53935'}
          onCancel={() => setConfirm(null)}
          onConfirm={(extra) => {
            if (!actionLoading) handleConfirm(extra);
          }}
        />
      )}

      {/* Detail drawer */}
      {detailApp && (
        <DetailDrawer
          app={detailApp}
          signEvents={signEvents}
          loadingEvents={loadingEvents}
          onClose={() => setDetailApp(null)}
          onResendLegal={doResendLegal}
          onResendCheckout={doResendCheckout}
          onManualProvision={doManualProvision}
          onRevoke={doRevoke}
        />
      )}

      {/* Page header */}
      <div className="mb-5">
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">
          FOUNDER TOOLS · ONBOARDING
        </div>
        <h1 className="text-lg font-black uppercase tracking-wider text-text-primary">
          ONBOARDING CONTROL
        </h1>
        <p className="text-xs text-text-muted mt-0.5">
          Application management · provisioning · legal · status control
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        {[
          { label: 'Total Applications', value: stats.total, color: 'rgba(255,255,255,0.85)' },
          { label: 'Pending Payment', value: stats.pendingPayment, color: 'var(--q-yellow)' },
          { label: 'Provisioned', value: stats.provisioned, color: 'var(--q-green)' },
          { label: 'Revoked', value: stats.revoked, color: 'var(--q-red)' },
        ].map((s) => (
          <div
            key={s.label}
            className="bg-bg-base border border-border-DEFAULT rounded-sm p-3"
          >
            <div className="text-[9px] uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-1">
              {s.label}
            </div>
            <div className="text-2xl font-bold" style={{ color: s.color }}>
              {loading ? '—' : s.value}
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          className="bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-xs text-text-primary px-3 py-2 rounded-sm outline-none focus:border-[rgba(255,107,26,0.4)]"
          style={{ minWidth: 150 }}
        >
          {STATUS_OPTS.map((o) => (
            <option key={o.value} value={o.value} className="bg-bg-base">
              {o.label}
            </option>
          ))}
        </select>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by email or agency…"
          className="bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-xs text-text-primary px-3 py-2 rounded-sm outline-none focus:border-[rgba(255,107,26,0.4)] placeholder:text-text-disabled"
          style={{ minWidth: 220 }}
        />
        <span className="text-[10px] text-[rgba(255,255,255,0.3)] ml-auto">
          {apps.length} application{apps.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div className="bg-bg-base border border-border-DEFAULT rounded-sm overflow-x-auto">
        <table className="w-full text-xs min-w-[860px]">
          <thead>
            <tr className="border-b border-[rgba(255,255,255,0.07)]">
              {[
                'Agency Name',
                'Contact Email',
                'State',
                'Plan',
                'Status',
                'Legal',
                'Created At',
                'Actions',
              ].map((h) => (
                <th
                  key={h}
                  className="text-left py-2.5 px-3 text-[9px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] font-semibold whitespace-nowrap"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={8} className="py-10 text-center text-[11px] text-[rgba(255,255,255,0.3)]">
                  Loading…
                </td>
              </tr>
            )}
            {!loading && apps.length === 0 && (
              <tr>
                <td colSpan={8} className="py-10 text-center text-[11px] text-[rgba(255,255,255,0.3)]">
                  No applications found
                </td>
              </tr>
            )}
            {!loading &&
              apps.map((app) => (
                <tr
                  key={app.id}
                  className="border-b border-border-subtle hover:bg-[rgba(255,255,255,0.02)] transition-colors"
                >
                  <td className="py-2.5 px-3 font-medium text-[rgba(255,255,255,0.85)] whitespace-nowrap">
                    {app.agency_name}
                  </td>
                  <td className="py-2.5 px-3 text-[rgba(255,255,255,0.5)] font-mono">
                    {app.contact_email}
                  </td>
                  <td className="py-2.5 px-3 text-[rgba(255,255,255,0.5)] uppercase">
                    {app.state}
                  </td>
                  <td className="py-2.5 px-3 text-[rgba(255,255,255,0.6)] whitespace-nowrap">
                    {app.plan}
                  </td>
                  <td className="py-2.5 px-3">
                    <StatusBadge status={app.status} />
                  </td>
                  <td className="py-2.5 px-3">
                    <LegalBadge legalStatus={app.legal_status} />
                  </td>
                  <td className="py-2.5 px-3 font-mono text-text-muted whitespace-nowrap">
                    {new Date(app.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {/* Resend Legal */}
                      {app.legal_status === 'not_sent' && (
                        <Tooltip label="Send Legal">
                          <IconBtn
                            onClick={() => doResendLegal(app)}
                            color="#ff9800"
                            bg="rgba(255,152,0,0.1)"
                            border="rgba(255,152,0,0.25)"
                          >
                            &#9993;
                          </IconBtn>
                        </Tooltip>
                      )}
                      {/* Resend Checkout */}
                      {app.legal_status === 'signed' && app.status !== 'paid' && app.status !== 'active' && app.status !== 'provisioning' && (
                        <Tooltip label="Resend Checkout">
                          <IconBtn
                            onClick={() => doResendCheckout(app)}
                            color="#29b6f6"
                            bg="rgba(41,182,246,0.1)"
                            border="rgba(41,182,246,0.25)"
                          >
                            $
                          </IconBtn>
                        </Tooltip>
                      )}
                      {/* Manual Provision */}
                      {app.status === 'paid' && (
                        <Tooltip label="Manual Provision">
                          <IconBtn
                            onClick={() => doManualProvision(app)}
                            color="#ff6b1a"
                            bg="rgba(255,107,26,0.1)"
                            border="rgba(255,107,26,0.25)"
                          >
                            &#9654;
                          </IconBtn>
                        </Tooltip>
                      )}
                      {/* Revoke */}
                      {app.status === 'active' && (
                        <Tooltip label="Revoke">
                          <IconBtn
                            onClick={() => doRevoke(app)}
                            color="#e53935"
                            bg="rgba(229,57,53,0.1)"
                            border="rgba(229,57,53,0.25)"
                          >
                            &#215;
                          </IconBtn>
                        </Tooltip>
                      )}
                      {/* View Detail */}
                      <Tooltip label="View Detail">
                        <IconBtn
                          onClick={() => setDetailApp(app)}
                          color="rgba(255,255,255,0.6)"
                          bg="rgba(255,255,255,0.05)"
                          border="rgba(255,255,255,0.1)"
                        >
                          &#9776;
                        </IconBtn>
                      </Tooltip>
                    </div>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Icon button + tooltip helpers ───────────────────────────────────────────

function IconBtn({
  children,
  onClick,
  color,
  bg,
  border,
}: {
  children: React.ReactNode;
  onClick: () => void;
  color: string;
  bg: string;
  border: string;
}) {
  return (
    <button
      onClick={onClick}
      className="w-7 h-7 flex items-center justify-center rounded-sm text-xs font-bold transition-all hover:brightness-125"
      style={{ color, background: bg, border: `1px solid ${border}` }}
    >
      {children}
    </button>
  );
}

function Tooltip({ label, children }: { label: string; children: React.ReactNode }) {
  const [show, setShow] = useState(false);
  return (
    <div
      className="relative inline-flex"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <div
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2 py-1 rounded-sm text-[9px] font-semibold uppercase tracking-wider whitespace-nowrap pointer-events-none z-10"
          style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.12)', color: 'rgba(255,255,255,0.7)' }}
        >
          {label}
        </div>
      )}
    </div>
  );
}
