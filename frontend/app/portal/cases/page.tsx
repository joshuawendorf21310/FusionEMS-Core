'use client';
import { QuantumTableSkeleton, QuantumCardSkeleton } from '@/components/ui';

import { useState, useEffect, useCallback, useRef } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return 'Bearer ' + (localStorage.getItem('qs_token') || '');
}

// ─── Types ────────────────────────────────────────────────────────────────────

type TabId = 'active' | 'new' | 'cms';

type TransportMode = 'ground' | 'rotor' | 'fixed_wing';
type CasePriority = 'routine' | 'urgent' | 'emergent';
type TransportLevel = 'BLS' | 'ALS' | 'SCT' | 'SPECIALTY';

interface CaseRecord {
  case_id: string;
  transport_mode: TransportMode;
  status: string;
  priority: CasePriority;
  patient_name?: string;
  opened_at: string;
  transport_request_id?: string;
  cad_call_id?: string;
  timeline?: TimelineEvent[];
  [key: string]: unknown;
}

interface TimelineEvent {
  event: string;
  timestamp: string;
  [key: string]: unknown;
}

interface CMSGate {
  patient_condition: string;
  transport_reason: string;
  transport_level: TransportLevel;
  origin_address: string;
  destination_name: string;
  pcs_on_file: boolean;
  pcs_obtained: boolean;
  medical_necessity_documented: boolean;
  patient_signature: boolean;
  signature_on_file: boolean;
  primary_insurance_id: string;
  medicare_id: string;
  medicaid_id: string;
}

interface CMSGateResult {
  score: number;
  passed: boolean;
  hard_block?: boolean;
  bs_flag?: boolean;
  gates?: { name: string; passed: boolean; weight: number }[];
  issues?: string[];
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
            color: t.type === 'success' ? 'var(--color-status-active)' : 'var(--color-brand-red)',
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

function fmtTs(ts: string): string {
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

function truncateId(id: string): string {
  return id.length > 12 ? `${id.slice(0, 8)}…` : id;
}

const TRANSPORT_STYLE: Record<TransportMode, { label: string; color: string; bg: string }> = {
  ground:    { label: 'GROUND',     color: 'var(--color-status-info)', bg: 'rgba(66,165,245,0.12)'   },
  rotor:     { label: 'ROTOR',      color: 'var(--q-orange)', bg: 'rgba(255,107,26,0.12)'   },
  fixed_wing:{ label: 'FIXED WING', color: 'var(--color-system-compliance)', bg: 'rgba(206,147,216,0.12)'  },
};

const STATUS_FLOW: Record<string, string> = {
  created:    'assigned',
  assigned:   'en_route',
  en_route:   'on_scene',
  on_scene:   'transporting',
  transporting:'arrived',
  arrived:    'completed',
};

const STATUS_COLORS: Record<string, string> = {
  created:     'rgba(255,255,255,0.5)',
  assigned:    'var(--color-status-info)',
  en_route:    'var(--color-status-warning)',
  on_scene:    'var(--color-brand-orange)',
  transporting:'var(--color-system-compliance)',
  arrived:     'var(--color-status-info)',
  completed:   'var(--color-status-active)',
  cancelled:   'var(--color-brand-red)',
};

function statusColor(s: string): string {
  return STATUS_COLORS[s] ?? 'rgba(255,255,255,0.5)';
}

function Badge({ label, color, bg }: { label: string; color: string; bg: string }) {
  return (
    <span
      className="px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider rounded-sm whitespace-nowrap"
      style={{ color, background: bg, border: `1px solid ${color}33` }}
    >
      {label}
    </span>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CasesPage() {
  const { toasts, push } = useToast();
  const [activeTab, setActiveTab] = useState<TabId>('active');

  // ── Active Cases ──
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [casesBusy, setCasesBusy] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── New Case ──
  const [newCase, setNewCase] = useState({
    transport_mode: 'ground' as TransportMode,
    priority: 'routine' as CasePriority,
    patient_name: '',
    origin_address: '',
    destination_address: '',
    transport_request_id: '',
    cad_call_id: '',
  });
  const [newCaseBusy, setNewCaseBusy] = useState(false);
  const [createdCaseId, setCreatedCaseId] = useState<string | null>(null);
  const [showCmsAfterNew, setShowCmsAfterNew] = useState(false);

  // ── CMS Gate ──
  const [cmsCaseId, setCmsCaseId] = useState('');
  const [cmsGate, setCmsGate] = useState<CMSGate>({
    patient_condition: '',
    transport_reason: '',
    transport_level: 'BLS',
    origin_address: '',
    destination_name: '',
    pcs_on_file: false,
    pcs_obtained: false,
    medical_necessity_documented: false,
    patient_signature: false,
    signature_on_file: false,
    primary_insurance_id: '',
    medicare_id: '',
    medicaid_id: '',
  });
  const [cmsResult, setCmsResult] = useState<CMSGateResult | null>(null);
  const [cmsBusy, setCmsBusy] = useState(false);

  // ── Fetch cases ──
  const fetchCases = useCallback(async () => {
    setCasesBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/cases/`, {
        headers: { Authorization: getToken() },
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setCases(Array.isArray(data) ? data : (data.cases ?? []));
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to load cases', 'error');
    } finally {
      setCasesBusy(false);
    }
  }, [push]);

  useEffect(() => {
    if (activeTab === 'active') {
      fetchCases();
      intervalRef.current = setInterval(fetchCases, 15000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [activeTab, fetchCases]);

  // ── Status transition ──
  async function transitionStatus(caseId: string, toStatus: string) {
    try {
      const r = await fetch(`${API}/api/v1/cases/${caseId}/status`, {
        method: 'PATCH',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: toStatus }),
      });
      if (!r.ok) throw new Error(await r.text());
      setCases((prev) =>
        prev.map((c) => c.case_id === caseId ? { ...c, status: toStatus } : c)
      );
      push('Status updated');
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to update status', 'error');
    }
  }

  // ── Create new case ──
  async function submitNewCase() {
    if (!newCase.patient_name.trim() || !newCase.origin_address.trim()) {
      push('Patient name and origin address are required', 'error'); return;
    }
    setNewCaseBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/cases/`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transport_mode: newCase.transport_mode,
          priority: newCase.priority,
          patient_name: newCase.patient_name.trim(),
          origin_address: newCase.origin_address.trim(),
          destination_address: newCase.destination_address.trim() || undefined,
          transport_request_id: newCase.transport_request_id.trim() || undefined,
          cad_call_id: newCase.cad_call_id.trim() || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      const created: CaseRecord = await r.json();
      setCreatedCaseId(created.case_id);
      setCmsCaseId(created.case_id);
      setCmsGate((prev) => ({
        ...prev,
        origin_address: newCase.origin_address.trim(),
      }));
      setShowCmsAfterNew(true);
      push('Case created — fill CMS gate below');
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to create case', 'error');
    } finally {
      setNewCaseBusy(false);
    }
  }

  // ── Evaluate CMS gate ──
  async function evaluateCms() {
    if (!cmsCaseId.trim()) { push('Enter a case ID', 'error'); return; }
    setCmsBusy(true);
    setCmsResult(null);
    try {
      const r = await fetch(`${API}/api/v1/cms-gate/cases/${cmsCaseId.trim()}/evaluate`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify(cmsGate),
      });
      if (!r.ok) throw new Error(await r.text());
      setCmsResult(await r.json());
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to evaluate CMS gate', 'error');
    } finally {
      setCmsBusy(false);
    }
  }

  const TABS: { id: TabId; label: string }[] = [
    { id: 'active', label: 'Active Cases' },
    { id: 'new',    label: 'New Case'     },
    { id: 'cms',    label: 'CMS Gate'     },
  ];

  // ── CMS form shared renderer ──
  function CmsForm() {
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {(
            [
              { key: 'patient_condition',   label: 'Patient Condition',   type: 'text' },
              { key: 'transport_reason',    label: 'Transport Reason',    type: 'text' },
              { key: 'origin_address',      label: 'Origin Address',      type: 'text' },
              { key: 'destination_name',    label: 'Destination Name',    type: 'text' },
              { key: 'primary_insurance_id',label: 'Primary Insurance ID',type: 'text' },
              { key: 'medicare_id',         label: 'Medicare ID',         type: 'text' },
              { key: 'medicaid_id',         label: 'Medicaid ID',         type: 'text' },
            ] as { key: keyof CMSGate; label: string; type: string }[]
          ).map(({ key, label, type }) => (
            <div key={key} className="flex flex-col gap-1">
              <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>{label}</label>
              <input
                type={type}
                className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                value={cmsGate[key] as string}
                onChange={(e) => setCmsGate((p) => ({ ...p, [key]: e.target.value }))}
              />
            </div>
          ))}
          <div className="flex flex-col gap-1">
            <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Transport Level</label>
            <select
              className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
              style={{ border: '1px solid rgba(255,255,255,0.12)' }}
              value={cmsGate.transport_level}
              onChange={(e) => setCmsGate((p) => ({ ...p, transport_level: e.target.value as TransportLevel }))}
            >
              <option value="BLS">BLS</option>
              <option value="ALS">ALS</option>
              <option value="SCT">SCT</option>
              <option value="SPECIALTY">Specialty</option>
            </select>
          </div>
        </div>

        {/* Checkboxes */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-2 gap-x-4">
          {(
            [
              { key: 'pcs_on_file',                   label: 'PCS on file'                   },
              { key: 'pcs_obtained',                  label: 'PCS obtained'                  },
              { key: 'medical_necessity_documented',  label: 'Medical necessity documented'  },
              { key: 'patient_signature',             label: 'Patient signature'             },
              { key: 'signature_on_file',             label: 'Signature on file'             },
            ] as { key: keyof CMSGate; label: string }[]
          ).map(({ key, label }) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={cmsGate[key] as boolean}
                onChange={(e) => setCmsGate((p) => ({ ...p, [key]: e.target.checked }))}
                className="w-3.5 h-3.5 accent-[var(--color-brand-orange)] cursor-pointer"
              />
              <span className="text-xs" style={{ color: 'rgba(255,255,255,0.7)' }}>{label}</span>
            </label>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-void text-text-primary">
      <Toast items={toasts} />

      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
        <h1 className="text-sm font-semibold tracking-wide">Cases Dashboard</h1>
        <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>
          Transport case management and CMS gate evaluation
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
              color: activeTab === tab.id ? 'var(--color-brand-orange)' : 'rgba(255,255,255,0.4)',
              borderBottom: activeTab === tab.id ? '2px solid var(--color-brand-orange)' : '2px solid transparent',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="px-6 py-5">

        {/* ══ ACTIVE CASES TAB ══ */}
        {activeTab === 'active' && (
          <div>
            {casesBusy && cases.length === 0 && (
              <div className="p-6"><QuantumCardSkeleton /></div>
            )}
            {!casesBusy && cases.length === 0 && (
              <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>No active cases.</p>
            )}
            <div className="space-y-2">
              {cases.map((c) => {
                const tm = TRANSPORT_STYLE[c.transport_mode] ?? TRANSPORT_STYLE.ground;
                const scol = statusColor(c.status);
                const nextStatus = STATUS_FLOW[c.status];
                const isExpanded = expandedId === c.case_id;

                return (
                  <div
                    key={c.case_id}
                    className="rounded-sm overflow-hidden"
                    style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                  >
                    {/* Row */}
                    <div
                      className="px-3 py-2.5 flex flex-wrap items-center gap-2 cursor-pointer"
                      style={{ background: 'var(--color-bg-base)' }}
                      onClick={() => setExpandedId(isExpanded ? null : c.case_id)}
                    >
                      <span
                        className="text-xs font-mono font-semibold"
                        style={{ color: 'var(--q-orange)' }}
                        title={c.case_id}
                      >
                        {truncateId(c.case_id)}
                      </span>
                      <Badge label={tm.label} color={tm.color} bg={tm.bg} />
                      <Badge
                        label={c.status.toUpperCase()}
                        color={scol}
                        bg={`${scol}18`}
                      />
                      <Badge
                        label={c.priority.toUpperCase()}
                        color={c.priority === 'emergent' ? 'var(--color-brand-red)' : c.priority === 'urgent' ? 'var(--color-status-warning)' : 'rgba(255,255,255,0.5)'}
                        bg={c.priority === 'emergent' ? 'rgba(229,57,53,0.1)' : c.priority === 'urgent' ? 'rgba(255,152,0,0.1)' : 'rgba(255,255,255,0.06)'}
                      />
                      <span className="text-xs ml-1" style={{ color: 'rgba(255,255,255,0.7)' }}>
                        {c.patient_name ?? '—'}
                      </span>
                      <span className="text-[10px] ml-auto" style={{ color: 'rgba(255,255,255,0.35)' }}>
                        {fmtTs(c.opened_at)}
                      </span>
                    </div>

                    {/* Expanded panel */}
                    {isExpanded && (
                      <div
                        className="px-4 py-3 space-y-3"
                        style={{ background: 'var(--color-bg-input)', borderTop: '1px solid rgba(255,255,255,0.06)' }}
                      >
                        {/* Linked IDs */}
                        <div className="flex flex-wrap gap-4">
                          {c.transport_request_id && (
                            <div>
                              <p className="text-[10px] mb-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>Transport Request ID</p>
                              <p className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.65)' }}>{c.transport_request_id}</p>
                            </div>
                          )}
                          {c.cad_call_id && (
                            <div>
                              <p className="text-[10px] mb-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>CAD Call ID</p>
                              <p className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.65)' }}>{c.cad_call_id}</p>
                            </div>
                          )}
                          <div>
                            <p className="text-[10px] mb-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>Full Case ID</p>
                            <p className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.65)' }}>{c.case_id}</p>
                          </div>
                        </div>

                        {/* Timeline */}
                        {Array.isArray(c.timeline) && c.timeline.length > 0 && (
                          <div>
                            <p className="text-[10px] mb-1.5 font-semibold" style={{ color: 'rgba(255,255,255,0.4)' }}>
                              Timeline
                            </p>
                            <div className="relative pl-4 space-y-2">
                              <div
                                className="absolute left-1 top-0 bottom-0 w-px"
                                style={{ background: 'rgba(255,255,255,0.08)' }}
                              />
                              {c.timeline.map((ev, i) => (
                                <div key={i} className="relative">
                                  <div
                                    className="absolute -left-[13px] top-1 w-2 h-2 rounded-full"
                                    style={{ background: 'var(--color-brand-orange)' }}
                                  />
                                  <p className="text-[10px]" style={{ color: 'rgba(255,255,255,0.35)' }}>
                                    {fmtTs(ev.timestamp)}
                                  </p>
                                  <p className="text-xs" style={{ color: 'rgba(255,255,255,0.7)' }}>{ev.event}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Status transition */}
                        {nextStatus && (
                          <button
                            onClick={() => transitionStatus(c.case_id, nextStatus)}
                            className="px-3 py-1 text-xs font-semibold rounded-sm"
                            style={{
                              color: statusColor(nextStatus),
                              background: `${statusColor(nextStatus)}18`,
                              border: `1px solid ${statusColor(nextStatus)}33`,
                            }}
                          >
                            Advance to {nextStatus.replace(/_/g, ' ').toUpperCase()}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ══ NEW CASE TAB ══ */}
        {activeTab === 'new' && (
          <div className="space-y-4">
            <div
              className="p-4 rounded-sm"
              style={{ background: 'var(--color-bg-base)', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>
                New Transport Case
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Transport Mode</label>
                  <select
                    className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                    style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                    value={newCase.transport_mode}
                    onChange={(e) => setNewCase((p) => ({ ...p, transport_mode: e.target.value as TransportMode }))}
                  >
                    <option value="ground">Ground</option>
                    <option value="rotor">Rotor</option>
                    <option value="fixed_wing">Fixed Wing</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Priority</label>
                  <select
                    className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                    style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                    value={newCase.priority}
                    onChange={(e) => setNewCase((p) => ({ ...p, priority: e.target.value as CasePriority }))}
                  >
                    <option value="routine">Routine</option>
                    <option value="urgent">Urgent</option>
                    <option value="emergent">Emergent</option>
                  </select>
                </div>
                {(
                  [
                    { key: 'patient_name',          label: 'Patient Name'           },
                    { key: 'origin_address',         label: 'Origin Address'         },
                    { key: 'destination_address',    label: 'Destination Address'    },
                    { key: 'transport_request_id',   label: 'Transport Request ID (optional)' },
                    { key: 'cad_call_id',            label: 'CAD Call ID (optional)' },
                  ] as { key: keyof typeof newCase; label: string }[]
                ).map(({ key, label }) => (
                  <div key={key} className="flex flex-col gap-1">
                    <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>{label}</label>
                    <input
                      type="text"
                      className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                      style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                      value={newCase[key] as string}
                      onChange={(e) => setNewCase((p) => ({ ...p, [key]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
              <button
                onClick={submitNewCase}
                disabled={newCaseBusy}
                className="px-3 py-1.5 text-xs font-semibold rounded-sm disabled:opacity-40"
                style={{ background: 'var(--color-brand-orange)', color: 'var(--color-text-primary)' }}
              >
                {newCaseBusy ? 'Creating...' : 'Create Case'}
              </button>
            </div>

            {/* CMS gate shown immediately after creation */}
            {showCmsAfterNew && createdCaseId && (
              <div
                className="p-4 rounded-sm"
                style={{ background: 'var(--color-bg-base)', border: '1px solid rgba(255,107,26,0.2)' }}
              >
                <p className="text-xs font-semibold mb-1" style={{ color: 'var(--q-orange)' }}>
                  CMS Gate — Case {createdCaseId}
                </p>
                <p className="text-[10px] mb-3" style={{ color: 'rgba(255,255,255,0.35)' }}>
                  Complete and evaluate the CMS gate for the newly created case.
                </p>
                <CmsForm />
                <button
                  onClick={async () => {
                    setCmsCaseId(createdCaseId);
                    await evaluateCms();
                  }}
                  disabled={cmsBusy}
                  className="mt-3 px-3 py-1.5 text-xs font-semibold rounded-sm disabled:opacity-40"
                  style={{ background: 'var(--color-brand-orange)', color: 'var(--color-text-primary)' }}
                >
                  {cmsBusy ? 'Evaluating...' : 'Evaluate CMS Gate'}
                </button>
                {cmsResult && <CmsResultPanel result={cmsResult} />}
              </div>
            )}
          </div>
        )}

        {/* ══ CMS GATE TAB ══ */}
        {activeTab === 'cms' && (
          <div className="space-y-4">
            <div
              className="p-4 rounded-sm"
              style={{ background: 'var(--color-bg-base)', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>
                CMS Gate Evaluation
              </p>

              <div className="flex flex-col gap-1 mb-4 max-w-xs">
                <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Case ID</label>
                <input
                  type="text"
                  className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                  style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                  placeholder="Enter case ID"
                  value={cmsCaseId}
                  onChange={(e) => setCmsCaseId(e.target.value)}
                />
              </div>

              <CmsForm />

              <button
                onClick={evaluateCms}
                disabled={cmsBusy}
                className="mt-4 px-3 py-1.5 text-xs font-semibold rounded-sm disabled:opacity-40"
                style={{ background: 'var(--color-brand-orange)', color: 'var(--color-text-primary)' }}
              >
                {cmsBusy ? 'Evaluating...' : 'Evaluate CMS Gate'}
              </button>
            </div>

            {cmsResult && <CmsResultPanel result={cmsResult} />}
          </div>
        )}

      </div>
    </div>
  );
}

// ─── CMS Result Panel ─────────────────────────────────────────────────────────

function CmsResultPanel({ result }: { result: CMSGateResult }) {
  return (
    <div className="space-y-3 mt-4">
      {/* BS flag warning */}
      {result.bs_flag && (
        <div
          className="px-4 py-2.5 rounded-sm text-xs font-semibold"
          style={{
            background: 'rgba(229,57,53,0.1)',
            border: '1px solid rgba(229,57,53,0.35)',
            color: 'var(--q-red)',
          }}
        >
          Billing Sensitivity Flag — this case has been flagged for review.
        </div>
      )}

      {/* Hard block warning */}
      {result.hard_block && (
        <div
          className="px-4 py-2.5 rounded-sm text-xs font-semibold"
          style={{
            background: 'rgba(229,57,53,0.1)',
            border: '1px solid rgba(229,57,53,0.35)',
            color: 'var(--q-red)',
          }}
        >
          HARD BLOCK — submission is not permitted until blocking issues are resolved.
        </div>
      )}

      {/* Score + pass/fail */}
      <div
        className="p-4 rounded-sm"
        style={{ background: 'var(--color-bg-base)', border: '1px solid rgba(255,255,255,0.08)' }}
      >
        <div className="flex items-center gap-3 mb-3">
          <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Score</span>
          <span
            className="text-lg font-bold tabular-nums"
            style={{ color: result.score >= 70 ? 'var(--color-status-active)' : result.score >= 40 ? 'var(--color-status-warning)' : 'var(--color-brand-red)' }}
          >
            {result.score}
          </span>
          <span className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>/100</span>
          <span
            className="px-2 py-0.5 text-[10px] font-semibold uppercase rounded-sm"
            style={{
              color: result.passed ? 'var(--color-status-active)' : 'var(--color-brand-red)',
              background: result.passed ? 'rgba(76,175,80,0.12)' : 'rgba(229,57,53,0.12)',
              border: `1px solid ${result.passed ? 'rgba(76,175,80,0.3)' : 'rgba(229,57,53,0.3)'}`,
            }}
          >
            {result.passed ? 'PASSED' : 'FAILED'}
          </span>
        </div>

        {/* Score bar */}
        <div
          className="h-2 rounded-full mb-4"
          style={{ background: 'rgba(255,255,255,0.08)' }}
        >
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.min(result.score, 100)}%`,
              background: result.score >= 70 ? 'var(--color-status-active)' : result.score >= 40 ? 'var(--color-status-warning)' : 'var(--color-brand-red)',
            }}
          />
        </div>

        {/* Gates table */}
        {result.gates && result.gates.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold mb-2" style={{ color: 'rgba(255,255,255,0.4)' }}>GATES</p>
            <table className="w-full text-xs">
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  {['Gate', 'Weight', 'Result'].map((h) => (
                    <th
                      key={h}
                      className="pb-1.5 text-left font-semibold"
                      style={{ color: 'rgba(255,255,255,0.35)' }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.gates.map((g, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td className="py-1.5 pr-4" style={{ color: 'rgba(255,255,255,0.7)' }}>{g.name}</td>
                    <td className="py-1.5 pr-4 tabular-nums" style={{ color: 'rgba(255,255,255,0.45)' }}>{g.weight}</td>
                    <td className="py-1.5">
                      <span
                        className="px-1.5 py-0.5 text-[9px] font-semibold uppercase rounded-sm"
                        style={{
                          color: g.passed ? 'var(--color-status-active)' : 'var(--color-brand-red)',
                          background: g.passed ? 'rgba(76,175,80,0.1)' : 'rgba(229,57,53,0.1)',
                        }}
                      >
                        {g.passed ? 'PASS' : 'FAIL'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Issues list */}
        {result.issues && result.issues.length > 0 && (
          <div className="mt-3">
            <p className="text-[10px] font-semibold mb-1.5" style={{ color: 'rgba(255,255,255,0.4)' }}>ISSUES</p>
            <ul className="space-y-1">
              {result.issues.map((issue, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-0.5 text-[10px]" style={{ color: 'var(--q-red)' }}>&#x25CF;</span>
                  <span className="text-xs" style={{ color: 'rgba(255,255,255,0.6)' }}>{issue}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
