'use client';
import { QuantumTableSkeleton, QuantumCardSkeleton } from '@/components/ui';

import { useState, useEffect, useCallback, useRef } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return 'Bearer ' + (localStorage.getItem('qs_token') || '');
}

// ─── Types ────────────────────────────────────────────────────────────────────

type TabId = 'overview' | 'alerts' | 'workorders' | 'inspections';

interface UnitScore {
  unit_id: string;
  readiness_score: number;
  alert_count: number;
  mdt_online: boolean;
  open_maintenance: number;
  [key: string]: unknown;
}

interface FleetReadiness {
  units?: UnitScore[];
  fleet_count?: number;
  avg_readiness?: number;
  units_ready?: number;
  units_limited?: number;
  units_no_go?: number;
  [key: string]: unknown;
}

interface UnitDetail {
  unit_id: string;
  [key: string]: unknown;
}

type AlertSeverity = 'critical' | 'warning' | 'info';

interface FleetAlert {
  alert_id: string;
  severity: AlertSeverity;
  unit_id: string;
  message: string;
  detected_at: string;
  resolved?: boolean;
  [key: string]: unknown;
}

type WOStatus = 'open' | 'in_progress' | 'completed';

interface WorkOrder {
  work_order_id: string;
  unit_id: string;
  title: string;
  description?: string;
  priority: string;
  status: WOStatus;
  due_date?: string;
  [key: string]: unknown;
}

interface InspectionTemplate {
  template_id: string;
  name: string;
  vehicle_type: string;
  frequency: string;
  [key: string]: unknown;
}

// ─── Toast ────────────────────────────────────────────────────────────────────

interface ToastItem { id: number; msg: string; type: 'success' | 'error' }

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

// ─── Helpers ──────────────────────────────────────────────────────────────────

function readinessColor(score: number): string {
  if (score >= 80) return '#4caf50';
  if (score >= 40) return '#ff9800';
  return '#e53935';
}

function fmtTs(ts: string): string {
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

const ALERT_STYLE: Record<AlertSeverity, { color: string; bg: string; label: string }> = {
  critical: { color: 'var(--q-red)', bg: 'rgba(229,57,53,0.12)', label: 'CRITICAL' },
  warning:  { color: 'var(--q-yellow)', bg: 'rgba(255,152,0,0.12)',  label: 'WARNING'  },
  info:     { color: '#42a5f5', bg: 'rgba(66,165,245,0.12)', label: 'INFO'     },
};

const WO_STATUS_STYLE: Record<WOStatus, { color: string; bg: string; label: string }> = {
  open:        { color: 'var(--q-yellow)', bg: 'rgba(255,152,0,0.12)',   label: 'OPEN'        },
  in_progress: { color: '#42a5f5', bg: 'rgba(66,165,245,0.12)', label: 'IN PROGRESS' },
  completed:   { color: 'var(--q-green)', bg: 'rgba(76,175,80,0.12)',   label: 'COMPLETED'   },
};

function Badge({
  label, color, bg,
}: { label: string; color: string; bg: string }) {
  return (
    <span
      className="px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider rounded-sm whitespace-nowrap"
      style={{ color, background: bg, border: `1px solid ${color}33` }}
    >
      {label}
    </span>
  );
}

function ReadinessBar({ score }: { score: number }) {
  const color = readinessColor(score);
  return (
    <div className="flex items-center gap-2">
      <div
        className="h-1.5 rounded-full"
        style={{ width: 60, background: 'rgba(255,255,255,0.08)' }}
      >
        <div
          className="h-full rounded-full"
          style={{ width: `${Math.min(score, 100)}%`, background: color }}
        />
      </div>
      <span className="text-xs tabular-nums" style={{ color }}>{score}</span>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function FleetPage() {
  const { toasts, push } = useToast();
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  // ── Overview ──
  const [fleet, setFleet] = useState<FleetReadiness | null>(null);
  const [fleetBusy, setFleetBusy] = useState(false);
  const [selectedUnit, setSelectedUnit] = useState<string | null>(null);
  const [unitDetail, setUnitDetail] = useState<UnitDetail | null>(null);
  const [unitDetailBusy, setUnitDetailBusy] = useState(false);

  // ── Alerts ──
  const [alerts, setAlerts] = useState<FleetAlert[]>([]);
  const [alertsBusy, setAlertsBusy] = useState(false);
  const [resolveNote, setResolveNote] = useState<Record<string, string>>({});
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  // ── Work Orders ──
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [woBusy, setWoBusy] = useState(false);
  const [woForm, setWoForm] = useState({
    unit_id: '', title: '', description: '', priority: 'routine', due_date: '',
  });
  const [woSubmitBusy, setWoSubmitBusy] = useState(false);

  // ── Inspections ──
  const [templates, setTemplates] = useState<InspectionTemplate[]>([]);
  const [inspBusy, setInspBusy] = useState(false);
  const [inspForm, setInspForm] = useState({
    name: '', vehicle_type: 'ground', frequency: 'daily',
  });
  const [inspSubmitBusy, setInspSubmitBusy] = useState(false);

  // ── Fetchers ──

  const fetchFleet = useCallback(async () => {
    setFleetBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/fleet-intelligence/readiness/fleet`, {
        headers: { Authorization: getToken() },
      });
      if (!r.ok) throw new Error(await r.text());
      setFleet(await r.json());
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to load fleet readiness', 'error');
    } finally {
      setFleetBusy(false);
    }
  }, [push]);

  const fetchUnitDetail = useCallback(async (unitId: string) => {
    setUnitDetailBusy(true);
    setUnitDetail(null);
    try {
      const r = await fetch(`${API}/api/v1/fleet-intelligence/readiness/units/${unitId}`, {
        headers: { Authorization: getToken() },
      });
      if (!r.ok) throw new Error(await r.text());
      setUnitDetail(await r.json());
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to load unit detail', 'error');
    } finally {
      setUnitDetailBusy(false);
    }
  }, [push]);

  const fetchAlerts = useCallback(async () => {
    setAlertsBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/fleet-intelligence/alerts?unresolved_only=true`, {
        headers: { Authorization: getToken() },
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setAlerts(Array.isArray(data) ? data : (data.alerts ?? []));
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to load alerts', 'error');
    } finally {
      setAlertsBusy(false);
    }
  }, [push]);

  const fetchWorkOrders = useCallback(async () => {
    setWoBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/fleet-intelligence/maintenance/work-orders`, {
        headers: { Authorization: getToken() },
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setWorkOrders(Array.isArray(data) ? data : (data.work_orders ?? []));
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to load work orders', 'error');
    } finally {
      setWoBusy(false);
    }
  }, [push]);

  const fetchTemplates = useCallback(async () => {
    setInspBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/fleet-intelligence/inspections/templates`, {
        headers: { Authorization: getToken() },
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setTemplates(Array.isArray(data) ? data : (data.templates ?? []));
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to load inspection templates', 'error');
    } finally {
      setInspBusy(false);
    }
  }, [push]);

  // Load on mount and on tab switch
  useEffect(() => {
    if (activeTab === 'overview') fetchFleet();
    if (activeTab === 'alerts') fetchAlerts();
    if (activeTab === 'workorders') fetchWorkOrders();
    if (activeTab === 'inspections') fetchTemplates();
  }, [activeTab, fetchFleet, fetchAlerts, fetchWorkOrders, fetchTemplates]);

  // ── Unit click ──
  function handleUnitClick(unitId: string) {
    setSelectedUnit(unitId);
    fetchUnitDetail(unitId);
  }

  // ── Resolve alert ──
  async function resolveAlert(alertId: string) {
    setResolvingId(alertId);
    try {
      const r = await fetch(`${API}/api/v1/fleet-intelligence/alerts/${alertId}/resolve`, {
        method: 'PATCH',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: resolveNote[alertId] || '' }),
      });
      if (!r.ok) throw new Error(await r.text());
      setAlerts((prev) => prev.filter((a) => a.alert_id !== alertId));
      push('Alert resolved');
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to resolve alert', 'error');
    } finally {
      setResolvingId(null);
    }
  }

  // ── Create work order ──
  async function createWorkOrder() {
    if (!woForm.unit_id.trim() || !woForm.title.trim()) {
      push('Unit ID and title are required', 'error'); return;
    }
    setWoSubmitBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/fleet-intelligence/maintenance/work-orders`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          unit_id: woForm.unit_id.trim(),
          title: woForm.title.trim(),
          description: woForm.description || undefined,
          priority: woForm.priority,
          due_date: woForm.due_date || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      push('Work order created');
      setWoForm({ unit_id: '', title: '', description: '', priority: 'routine', due_date: '' });
      fetchWorkOrders();
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to create work order', 'error');
    } finally {
      setWoSubmitBusy(false);
    }
  }

  // ── Update work order status ──
  async function updateWOStatus(woId: string, status: WOStatus) {
    try {
      const r = await fetch(`${API}/api/v1/fleet-intelligence/maintenance/work-orders/${woId}`, {
        method: 'PATCH',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (!r.ok) throw new Error(await r.text());
      setWorkOrders((prev) => prev.map((w) => w.work_order_id === woId ? { ...w, status } : w));
      push('Status updated');
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to update status', 'error');
    }
  }

  // ── Create inspection template ──
  async function createTemplate() {
    if (!inspForm.name.trim()) { push('Name is required', 'error'); return; }
    setInspSubmitBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/fleet-intelligence/inspections/templates`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: inspForm.name.trim(),
          vehicle_type: inspForm.vehicle_type,
          frequency: inspForm.frequency,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      push('Template created');
      setInspForm({ name: '', vehicle_type: 'ground', frequency: 'daily' });
      fetchTemplates();
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to create template', 'error');
    } finally {
      setInspSubmitBusy(false);
    }
  }

  const TABS: { id: TabId; label: string }[] = [
    { id: 'overview',     label: 'Fleet Overview' },
    { id: 'alerts',       label: 'Alerts' },
    { id: 'workorders',   label: 'Work Orders' },
    { id: 'inspections',  label: 'Inspections' },
  ];

  const units: UnitScore[] = fleet?.units ?? [];

  return (
    <div className="min-h-screen bg-bg-void text-text-primary">
      <Toast items={toasts} />

      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
        <h1 className="text-sm font-semibold tracking-wide">Fleet Intelligence Dashboard</h1>
        <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>
          Unit readiness, alerts, maintenance, and inspections
        </p>
      </div>

      {/* Tab Bar */}
      <div className="flex border-b px-6" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className="px-4 py-2.5 text-xs font-semibold transition-colors"
            style={{
              color: activeTab === tab.id ? '#ff6b1a' : 'rgba(255,255,255,0.4)',
              borderBottom: activeTab === tab.id ? '2px solid #ff6b1a' : '2px solid transparent',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="px-6 py-5">

        {/* ══ FLEET OVERVIEW TAB ══ */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {fleetBusy && (
              <div className="p-6"><QuantumCardSkeleton /></div>
            )}

            {fleet && (
              <>
                {/* Summary cards */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  {(
                    [
                      { label: 'Fleet Count',   value: fleet.fleet_count ?? units.length, color: 'rgba(255,255,255,0.8)' },
                      { label: 'Avg Readiness', value: fleet.avg_readiness != null ? fleet.avg_readiness : (units.length ? Math.round(units.reduce((s,u)=>s+u.readiness_score,0)/units.length) : 0), color: readinessColor(fleet.avg_readiness ?? 0) },
                      { label: 'Units Ready',   value: fleet.units_ready   ?? units.filter((u) => u.readiness_score >= 80).length, color: 'var(--q-green)' },
                      { label: 'Units Limited', value: fleet.units_limited ?? units.filter((u) => u.readiness_score >= 40 && u.readiness_score < 80).length, color: 'var(--q-yellow)' },
                      { label: 'Units No-Go',   value: fleet.units_no_go   ?? units.filter((u) => u.readiness_score < 40).length, color: 'var(--q-red)' },
                    ] as { label: string; value: number; color: string }[]
                  ).map(({ label, value, color }) => (
                    <div
                      key={label}
                      className="p-3 rounded-sm"
                      style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.08)' }}
                    >
                      <p className="text-[10px] mb-1" style={{ color: 'rgba(255,255,255,0.4)' }}>{label}</p>
                      <p className="text-lg font-bold tabular-nums" style={{ color }}>{value}</p>
                    </div>
                  ))}
                </div>

                {/* Units table */}
                {units.length > 0 && (
                  <div
                    className="rounded-sm overflow-hidden"
                    style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                  >
                    <table className="w-full text-xs">
                      <thead>
                        <tr style={{ background: '#0b0f14', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                          {['Unit ID', 'Readiness', 'Alerts', 'MDT', 'Open Maint.'].map((h) => (
                            <th
                              key={h}
                              className="px-3 py-2 text-left font-semibold"
                              style={{ color: 'rgba(255,255,255,0.4)' }}
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {units.map((u) => (
                          <tr
                            key={u.unit_id}
                            onClick={() => handleUnitClick(u.unit_id)}
                            className="cursor-pointer transition-colors"
                            style={{
                              borderBottom: '1px solid rgba(255,255,255,0.05)',
                              background: selectedUnit === u.unit_id ? 'rgba(255,107,26,0.06)' : 'transparent',
                            }}
                          >
                            <td className="px-3 py-2 font-semibold" style={{ color: 'var(--q-orange)' }}>{u.unit_id}</td>
                            <td className="px-3 py-2"><ReadinessBar score={u.readiness_score} /></td>
                            <td className="px-3 py-2 tabular-nums" style={{ color: u.alert_count > 0 ? '#e53935' : 'rgba(255,255,255,0.6)' }}>
                              {u.alert_count}
                            </td>
                            <td className="px-3 py-2">
                              <span
                                className="w-2 h-2 rounded-full inline-block"
                                style={{ background: u.mdt_online ? '#4caf50' : '#e53935' }}
                              />
                            </td>
                            <td className="px-3 py-2 tabular-nums" style={{ color: 'rgba(255,255,255,0.6)' }}>
                              {u.open_maintenance}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Unit detail panel */}
                {selectedUnit && (
                  <div
                    className="p-4 rounded-sm"
                    style={{ background: '#0b0f14', border: '1px solid rgba(255,107,26,0.2)' }}
                  >
                    <p className="text-xs font-semibold mb-2" style={{ color: 'var(--q-orange)' }}>
                      Unit Detail — {selectedUnit}
                    </p>
                    {unitDetailBusy ? (
                      <div className="p-6"><QuantumCardSkeleton /></div>
                    ) : unitDetail ? (
                      <pre
                        className="text-xs whitespace-pre-wrap"
                        style={{ color: 'rgba(255,255,255,0.6)', fontFamily: 'monospace' }}
                      >
                        {JSON.stringify(unitDetail, null, 2)}
                      </pre>
                    ) : null}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ══ ALERTS TAB ══ */}
        {activeTab === 'alerts' && (
          <div className="space-y-3">
            {alertsBusy && (
              <div className="p-6"><QuantumCardSkeleton /></div>
            )}
            {!alertsBusy && alerts.length === 0 && (
              <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>No unresolved alerts.</p>
            )}
            {alerts.map((alert) => {
              const s = ALERT_STYLE[alert.severity] ?? ALERT_STYLE.info;
              return (
                <div
                  key={alert.alert_id}
                  className="p-3 rounded-sm"
                  style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <Badge label={s.label} color={s.color} bg={s.bg} />
                    <span className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.8)' }}>
                      {alert.unit_id}
                    </span>
                    <span className="text-[10px] ml-auto" style={{ color: 'rgba(255,255,255,0.35)' }}>
                      {fmtTs(alert.detected_at)}
                    </span>
                  </div>
                  <p className="text-xs mb-2" style={{ color: 'rgba(255,255,255,0.6)' }}>{alert.message}</p>
                  <div className="flex items-center gap-2">
                    <input
                      className="flex-1 bg-bg-void rounded-sm px-2 py-1 text-xs text-text-primary outline-none"
                      style={{ border: '1px solid rgba(255,255,255,0.1)' }}
                      placeholder="Resolution note (optional)"
                      value={resolveNote[alert.alert_id] || ''}
                      onChange={(e) =>
                        setResolveNote((prev) => ({ ...prev, [alert.alert_id]: e.target.value }))
                      }
                    />
                    <button
                      onClick={() => resolveAlert(alert.alert_id)}
                      disabled={resolvingId === alert.alert_id}
                      className="px-2.5 py-1 text-xs font-semibold rounded-sm disabled:opacity-40"
                      style={{ background: 'rgba(76,175,80,0.15)', color: 'var(--q-green)', border: '1px solid rgba(76,175,80,0.3)' }}
                    >
                      {resolvingId === alert.alert_id ? 'Resolving...' : 'Resolve'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ══ WORK ORDERS TAB ══ */}
        {activeTab === 'workorders' && (
          <div className="space-y-4">
            {/* Create form */}
            <div
              className="p-4 rounded-sm"
              style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>
                Create Work Order
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                {(
                  [
                    { key: 'unit_id',     label: 'Unit ID',     type: 'text' },
                    { key: 'title',       label: 'Title',       type: 'text' },
                    { key: 'description', label: 'Description', type: 'text' },
                    { key: 'due_date',    label: 'Due Date',    type: 'date' },
                  ] as { key: keyof typeof woForm; label: string; type: string }[]
                ).map(({ key, label, type }) => (
                  <div key={key} className="flex flex-col gap-1">
                    <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>{label}</label>
                    <input
                      type={type}
                      className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                      style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                      value={woForm[key]}
                      onChange={(e) => setWoForm((p) => ({ ...p, [key]: e.target.value }))}
                    />
                  </div>
                ))}
                <div className="flex flex-col gap-1">
                  <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Priority</label>
                  <select
                    className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                    style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                    value={woForm.priority}
                    onChange={(e) => setWoForm((p) => ({ ...p, priority: e.target.value }))}
                  >
                    <option value="critical">Critical</option>
                    <option value="urgent">Urgent</option>
                    <option value="routine">Routine</option>
                  </select>
                </div>
              </div>
              <button
                onClick={createWorkOrder}
                disabled={woSubmitBusy}
                className="px-3 py-1.5 text-xs font-semibold rounded-sm disabled:opacity-40"
                style={{ background: '#ff6b1a', color: '#fff' }}
              >
                {woSubmitBusy ? 'Creating...' : 'Create Work Order'}
              </button>
            </div>

            {/* List */}
            {woBusy && (
              <div className="p-6"><QuantumCardSkeleton /></div>
            )}
            {workOrders.map((wo) => {
              const s = WO_STATUS_STYLE[wo.status] ?? WO_STATUS_STYLE.open;
              const nextStatuses: WOStatus[] = wo.status === 'open'
                ? ['in_progress', 'completed']
                : wo.status === 'in_progress'
                ? ['completed']
                : [];
              return (
                <div
                  key={wo.work_order_id}
                  className="p-3 rounded-sm"
                  style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <Badge label={s.label} color={s.color} bg={s.bg} />
                    <span className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.85)' }}>
                      {wo.title}
                    </span>
                    <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.35)' }}>
                      {wo.unit_id}
                    </span>
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded-sm ml-auto"
                      style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.4)' }}
                    >
                      {wo.priority}
                    </span>
                  </div>
                  {wo.description && (
                    <p className="text-xs mb-2" style={{ color: 'rgba(255,255,255,0.45)' }}>{wo.description}</p>
                  )}
                  {nextStatuses.length > 0 && (
                    <div className="flex gap-2">
                      {nextStatuses.map((ns) => {
                        const ns_ = WO_STATUS_STYLE[ns];
                        return (
                          <button
                            key={ns}
                            onClick={() => updateWOStatus(wo.work_order_id, ns)}
                            className="px-2 py-0.5 text-[10px] font-semibold rounded-sm"
                            style={{ color: ns_.color, background: ns_.bg, border: `1px solid ${ns_.color}33` }}
                          >
                            Mark {ns_.label}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* ══ INSPECTIONS TAB ══ */}
        {activeTab === 'inspections' && (
          <div className="space-y-4">
            {/* Create form */}
            <div
              className="p-4 rounded-sm"
              style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>
                Create Inspection Template
              </p>
              <div className="flex flex-wrap gap-3 mb-3 items-end">
                <div className="flex flex-col gap-1 flex-1 min-w-[140px]">
                  <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Name</label>
                  <input
                    className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                    style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                    value={inspForm.name}
                    onChange={(e) => setInspForm((p) => ({ ...p, name: e.target.value }))}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Vehicle Type</label>
                  <select
                    className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                    style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                    value={inspForm.vehicle_type}
                    onChange={(e) => setInspForm((p) => ({ ...p, vehicle_type: e.target.value }))}
                  >
                    <option value="ground">Ground</option>
                    <option value="rotor">Rotor</option>
                    <option value="fixed_wing">Fixed Wing</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Frequency</label>
                  <select
                    className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                    style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                    value={inspForm.frequency}
                    onChange={(e) => setInspForm((p) => ({ ...p, frequency: e.target.value }))}
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
                <button
                  onClick={createTemplate}
                  disabled={inspSubmitBusy}
                  className="px-3 py-1.5 text-xs font-semibold rounded-sm disabled:opacity-40"
                  style={{ background: '#ff6b1a', color: '#fff' }}
                >
                  {inspSubmitBusy ? 'Creating...' : 'Create Template'}
                </button>
              </div>
            </div>

            {/* Template list */}
            {inspBusy && (
              <div className="p-6"><QuantumCardSkeleton /></div>
            )}
            {!inspBusy && templates.length === 0 && (
              <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>No templates found.</p>
            )}
            {templates.map((t) => (
              <div
                key={t.template_id}
                className="px-4 py-3 rounded-sm flex flex-wrap items-center gap-3"
                style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.08)' }}
              >
                <span className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.85)' }}>{t.name}</span>
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded-sm"
                  style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.45)' }}
                >
                  {t.vehicle_type}
                </span>
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded-sm"
                  style={{ background: 'rgba(255,107,26,0.1)', color: 'var(--q-orange)' }}
                >
                  {t.frequency}
                </span>
                <span className="text-[10px] ml-auto" style={{ color: 'rgba(255,255,255,0.3)' }}>
                  {t.template_id}
                </span>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
