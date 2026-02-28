'use client';
import { QuantumTableSkeleton, QuantumCardSkeleton } from '@/components/ui';

import { useState, useEffect, useCallback, useRef } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return 'Bearer ' + (localStorage.getItem('qs_token') || '');
}

// ─── Types ────────────────────────────────────────────────────────────────────

type ReadinessState = 'ready' | 'limited' | 'no_go' | 'maintenance_hold';
type TurbulenceLevel = 'none' | 'light' | 'moderate' | 'severe';
type GoNoGo = 'go' | 'no_go';

interface ChecklistTemplate {
  items?: string[];
  risk_factors?: string[];
}

interface SafetyEvent {
  event_type: string;
  timestamp: string;
  details?: Record<string, unknown>;
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

// ─── Constants ────────────────────────────────────────────────────────────────

const READINESS_STATES: ReadinessState[] = ['ready', 'limited', 'no_go', 'maintenance_hold'];

const READINESS_STYLE: Record<ReadinessState, { label: string; color: string; bg: string }> = {
  ready:            { label: 'READY',            color: 'var(--q-green)', bg: 'rgba(76,175,80,0.12)' },
  limited:          { label: 'LIMITED',          color: 'var(--q-yellow)', bg: 'rgba(255,152,0,0.12)' },
  no_go:            { label: 'NO-GO',            color: 'var(--q-red)', bg: 'rgba(229,57,53,0.12)' },
  maintenance_hold: { label: 'MAINTENANCE HOLD', color: '#9e9e9e', bg: 'rgba(158,158,158,0.12)' },
};

const CHECKLIST_KEYS = [
  'wx_reviewed',
  'minima_met',
  'aircraft_preflight',
  'fuel_sufficient',
  'crew_rest',
  'crew_briefed',
  'comms_check',
  'lz_info_received',
  'medical_crew_ready',
  'no_safety_concerns',
] as const;

const CHECKLIST_LABELS: Record<typeof CHECKLIST_KEYS[number], string> = {
  wx_reviewed:        'Weather reviewed',
  minima_met:         'Minima met',
  aircraft_preflight: 'Aircraft preflight complete',
  fuel_sufficient:    'Fuel sufficient',
  crew_rest:          'Crew rest requirements met',
  crew_briefed:       'Crew briefed',
  comms_check:        'Comms check complete',
  lz_info_received:   'LZ info received',
  medical_crew_ready: 'Medical crew ready',
  no_safety_concerns: 'No safety concerns',
};

const RISK_FACTOR_KEYS = [
  'night_ops',
  'mountainous_terrain',
  'marginal_wx',
  'unfamiliar_lz',
  'single_pilot',
  'critical_patient',
  'long_transport',
  'comms_degraded',
] as const;

const RISK_FACTOR_LABELS: Record<typeof RISK_FACTOR_KEYS[number], string> = {
  night_ops:          'Night operations',
  mountainous_terrain:'Mountainous terrain',
  marginal_wx:        'Marginal weather',
  unfamiliar_lz:      'Unfamiliar LZ',
  single_pilot:       'Single pilot',
  critical_patient:   'Critical patient',
  long_transport:     'Long transport',
  comms_degraded:     'Comms degraded',
};

const RISK_WEIGHTS: Record<typeof RISK_FACTOR_KEYS[number], number> = {
  night_ops:          10,
  mountainous_terrain:8,
  marginal_wx:        12,
  unfamiliar_lz:      8,
  single_pilot:       10,
  critical_patient:   5,
  long_transport:     5,
  comms_degraded:     8,
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function ReadinessBadge({ state }: { state: ReadinessState }) {
  const s = READINESS_STYLE[state] ?? READINESS_STYLE.no_go;
  return (
    <span
      className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
      style={{ color: s.color, background: s.bg, border: `1px solid ${s.color}33` }}
    >
      {s.label}
    </span>
  );
}

function riskColor(score: number): string {
  if (score < 20) return '#4caf50';
  if (score < 45) return '#ff9800';
  return '#e53935';
}

function fmtTs(ts: string): string {
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function HemsPage() {
  const { toasts, push } = useToast();

  // Shared IDs
  const [missionId, setMissionId] = useState('');
  const [aircraftId, setAircraftId] = useState('');

  // ── Aircraft Readiness ───
  const [readinessState, setReadinessState] = useState<ReadinessState | null>(null);
  const [newReadiness, setNewReadiness] = useState<ReadinessState>('ready');
  const [readinessReason, setReadinessReason] = useState('');
  const [readinessBusy, setReadinessBusy] = useState(false);

  // ── Mission Acceptance Checklist ───
  const [checklistItems, setChecklistItems] = useState<Record<typeof CHECKLIST_KEYS[number], boolean>>(
    Object.fromEntries(CHECKLIST_KEYS.map((k) => [k, false])) as Record<typeof CHECKLIST_KEYS[number], boolean>
  );
  const [riskFactors, setRiskFactors] = useState<Record<typeof RISK_FACTOR_KEYS[number], boolean>>(
    Object.fromEntries(RISK_FACTOR_KEYS.map((k) => [k, false])) as Record<typeof RISK_FACTOR_KEYS[number], boolean>
  );
  const [acceptanceBusy, setAcceptanceBusy] = useState(false);

  // ── Weather Brief ───
  const [wx, setWx] = useState({
    ceiling_ft: '',
    visibility_sm: '',
    wind_direction: '',
    wind_speed_kt: '',
    gusts_kt: '',
    precip: false,
    icing: false,
    turbulence: 'none' as TurbulenceLevel,
    go_no_go: 'go' as GoNoGo,
    source: '',
  });
  const [wxBusy, setWxBusy] = useState(false);

  // ── Safety Timeline ───
  const [timeline, setTimeline] = useState<SafetyEvent[]>([]);
  const [timelineBusy, setTimelineBusy] = useState(false);

  // ── Fetch checklist template on mount ───
  useEffect(() => {
    fetch(`${API}/api/v1/hems/checklist-template`, {
      headers: { Authorization: getToken() },
    })
      .then((r) => r.ok ? r.json() : null)
      .then((data: ChecklistTemplate | null) => {
        if (!data) return;
      })
      .catch((e: unknown) => { console.warn('checklist-template fetch failed', e); });
  }, []);

  // ── SSE: realtime mission events ───────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined') return;
    let es: EventSource | null = null;
    let pollInterval: ReturnType<typeof setInterval> | null = null;

    function startSSE() {
      const token = getToken().replace('Bearer ', '');
      es = new EventSource(`${API}/api/v1/hems/missions/stream?token=${encodeURIComponent(token)}`);

      es.addEventListener('mission_complete', (e) => {
        const data = JSON.parse(e.data);
        const mid = (data?.data?.mission_id ?? '');
        if (mid && !missionId) setMissionId(mid);
        push('Mission event received', 'success');
      });

      es.addEventListener('wheels_up', (e) => {
        const data = JSON.parse(e.data);
        const mid = (data?.data?.mission_id ?? '');
        if (mid && !missionId) setMissionId(mid);
      });

      es.addEventListener('pilot_acknowledge', (e) => {
        const data = JSON.parse(e.data);
        const mid = (data?.data?.mission_id ?? '');
        if (mid && !missionId) setMissionId(mid);
      });

      es.onerror = () => {
        es?.close();
        // Fallback: poll every 15s
        pollInterval = setInterval(() => {
          if (missionId) fetchTimeline();
        }, 15000);
      };
    }

    startSSE();
    return () => {
      es?.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, []);

  // ── Set Readiness ───
  async function submitReadiness() {
    if (!aircraftId.trim()) { push('Enter aircraft ID', 'error'); return; }
    setReadinessBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/hems/aircraft/${aircraftId.trim()}/readiness`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: newReadiness, reason: readinessReason }),
      });
      if (!r.ok) throw new Error(await r.text());
      setReadinessState(newReadiness);
      setReadinessReason('');
      push('Readiness updated');
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to update readiness', 'error');
    } finally {
      setReadinessBusy(false);
    }
  }

  // ── Submit Acceptance ───
  function riskScore(): number {
    return RISK_FACTOR_KEYS.reduce((sum, k) => sum + (riskFactors[k] ? RISK_WEIGHTS[k] : 0), 0);
  }

  async function submitAcceptance() {
    if (!missionId.trim()) { push('Enter mission ID', 'error'); return; }
    setAcceptanceBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/hems/missions/${missionId.trim()}/acceptance`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          aircraft_id: aircraftId.trim() || undefined,
          checklist: checklistItems,
          risk_factors: riskFactors,
          risk_score: riskScore(),
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      push('Acceptance submitted');
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to submit acceptance', 'error');
    } finally {
      setAcceptanceBusy(false);
    }
  }

  // ── Submit Weather Brief ───
  async function submitWeather() {
    if (!missionId.trim()) { push('Enter mission ID', 'error'); return; }
    setWxBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/hems/missions/${missionId.trim()}/weather-brief`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ceiling_ft: wx.ceiling_ft ? Number(wx.ceiling_ft) : undefined,
          visibility_sm: wx.visibility_sm ? Number(wx.visibility_sm) : undefined,
          wind_direction: wx.wind_direction ? Number(wx.wind_direction) : undefined,
          wind_speed_kt: wx.wind_speed_kt ? Number(wx.wind_speed_kt) : undefined,
          gusts_kt: wx.gusts_kt ? Number(wx.gusts_kt) : undefined,
          precip: wx.precip,
          icing: wx.icing,
          turbulence: wx.turbulence,
          go_no_go: wx.go_no_go,
          source: wx.source || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      push('Weather brief submitted');
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to submit weather brief', 'error');
    } finally {
      setWxBusy(false);
    }
  }

  // ── Fetch Safety Timeline ───
  async function fetchTimeline() {
    if (!missionId.trim()) { push('Enter mission ID', 'error'); return; }
    setTimelineBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/hems/missions/${missionId.trim()}/safety-timeline`, {
        headers: { Authorization: getToken() },
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setTimeline(Array.isArray(data) ? data : (data.events ?? []));
    } catch (e: unknown) {
      push(e instanceof Error ? e.message : 'Failed to fetch timeline', 'error');
    } finally {
      setTimelineBusy(false);
    }
  }

  const score = riskScore();

  return (
    <div className="min-h-screen bg-bg-void text-text-primary" style={{ fontFamily: 'inherit' }}>
      <Toast items={toasts} />

      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
        <h1 className="text-sm font-semibold tracking-wide text-text-primary">HEMS Pilot Portal</h1>
        <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>
          Helicopter Emergency Medical Services — Mission Acceptance &amp; Safety
        </p>
      </div>

      <div className="px-6 py-5 space-y-5">

        {/* ── Shared ID inputs ── */}
        <div
          className="p-4 rounded-sm"
          style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>Session IDs</p>
          <div className="flex flex-wrap gap-3">
            <div className="flex flex-col gap-1 flex-1 min-w-[160px]">
              <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Aircraft ID</label>
              <input
                className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                placeholder="e.g. N123HM"
                value={aircraftId}
                onChange={(e) => setAircraftId(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1 flex-1 min-w-[160px]">
              <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Mission ID</label>
              <input
                className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                placeholder="e.g. MSN-0001"
                value={missionId}
                onChange={(e) => setMissionId(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* ── 1. Aircraft Readiness Panel ── */}
        <div
          className="p-4 rounded-sm"
          style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.6)' }}>
              Aircraft Readiness
            </p>
            {readinessState && <ReadinessBadge state={readinessState} />}
          </div>
          {!readinessState && (
            <p className="text-xs mb-3" style={{ color: 'rgba(255,255,255,0.3)' }}>
              No readiness state recorded this session.
            </p>
          )}
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex flex-col gap-1">
              <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>New State</label>
              <select
                className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                value={newReadiness}
                onChange={(e) => setNewReadiness(e.target.value as ReadinessState)}
              >
                {READINESS_STATES.map((s) => (
                  <option key={s} value={s}>{READINESS_STYLE[s].label}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1 flex-1 min-w-[180px]">
              <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Reason</label>
              <input
                className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                placeholder="Optional reason"
                value={readinessReason}
                onChange={(e) => setReadinessReason(e.target.value)}
              />
            </div>
            <button
              onClick={submitReadiness}
              disabled={readinessBusy}
              className="px-3 py-1.5 text-xs font-semibold rounded-sm disabled:opacity-40 transition-opacity"
              style={{ background: '#ff6b1a', color: '#fff' }}
            >
              {readinessBusy ? 'Saving...' : 'Set Readiness'}
            </button>
          </div>
        </div>

        {/* ── 2. Mission Acceptance Checklist ── */}
        <div
          className="p-4 rounded-sm"
          style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>
            Mission Acceptance Checklist
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-2 gap-x-6 mb-4">
            {CHECKLIST_KEYS.map((key) => (
              <label key={key} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checklistItems[key]}
                  onChange={(e) =>
                    setChecklistItems((prev) => ({ ...prev, [key]: e.target.checked }))
                  }
                  className="w-3.5 h-3.5 accent-[#ff6b1a] cursor-pointer"
                />
                <span className="text-xs" style={{ color: 'rgba(255,255,255,0.7)' }}>
                  {CHECKLIST_LABELS[key]}
                </span>
              </label>
            ))}
          </div>

          <p className="text-xs font-semibold mb-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
            Risk Factors
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-2 gap-x-6 mb-4">
            {RISK_FACTOR_KEYS.map((key) => (
              <label key={key} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={riskFactors[key]}
                  onChange={(e) =>
                    setRiskFactors((prev) => ({ ...prev, [key]: e.target.checked }))
                  }
                  className="w-3.5 h-3.5 accent-[#ff6b1a] cursor-pointer"
                />
                <span className="text-xs" style={{ color: 'rgba(255,255,255,0.7)' }}>
                  {RISK_FACTOR_LABELS[key]}
                  <span className="ml-1" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    (+{RISK_WEIGHTS[key]})
                  </span>
                </span>
              </label>
            ))}
          </div>

          {/* Risk Score */}
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Risk Score:</span>
            <span
              className="text-sm font-bold tabular-nums"
              style={{ color: riskColor(score) }}
            >
              {score}
            </span>
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-sm font-semibold uppercase"
              style={{
                color: riskColor(score),
                background: `${riskColor(score)}1a`,
                border: `1px solid ${riskColor(score)}33`,
              }}
            >
              {score < 20 ? 'Low' : score < 45 ? 'Moderate' : 'High'}
            </span>
          </div>

          <button
            onClick={submitAcceptance}
            disabled={acceptanceBusy}
            className="px-3 py-1.5 text-xs font-semibold rounded-sm disabled:opacity-40 transition-opacity"
            style={{ background: '#ff6b1a', color: '#fff' }}
          >
            {acceptanceBusy ? 'Submitting...' : 'Submit Acceptance'}
          </button>
        </div>

        {/* ── 3. Weather Brief ── */}
        <div
          className="p-4 rounded-sm"
          style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>
            Weather Brief
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
            {(
              [
                { key: 'ceiling_ft',     label: 'Ceiling (ft)',        type: 'number' },
                { key: 'visibility_sm',  label: 'Visibility (sm)',     type: 'number' },
                { key: 'wind_direction', label: 'Wind Direction (deg)',type: 'number' },
                { key: 'wind_speed_kt',  label: 'Wind Speed (kt)',     type: 'number' },
                { key: 'gusts_kt',       label: 'Gusts (kt)',          type: 'number' },
                { key: 'source',         label: 'Source',              type: 'text'   },
              ] as { key: keyof typeof wx; label: string; type: string }[]
            ).map(({ key, label, type }) => (
              <div key={key} className="flex flex-col gap-1">
                <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>{label}</label>
                <input
                  type={type}
                  className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                  style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                  value={wx[key] as string}
                  onChange={(e) => setWx((prev) => ({ ...prev, [key]: e.target.value }))}
                />
              </div>
            ))}

            <div className="flex flex-col gap-1">
              <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Turbulence</label>
              <select
                className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                value={wx.turbulence}
                onChange={(e) => setWx((prev) => ({ ...prev, turbulence: e.target.value as TurbulenceLevel }))}
              >
                <option value="none">None</option>
                <option value="light">Light</option>
                <option value="moderate">Moderate</option>
                <option value="severe">Severe</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Go / No-Go</label>
              <select
                className="bg-bg-void rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
                style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                value={wx.go_no_go}
                onChange={(e) => setWx((prev) => ({ ...prev, go_no_go: e.target.value as GoNoGo }))}
              >
                <option value="go">Go</option>
                <option value="no_go">No-Go</option>
              </select>
            </div>
          </div>

          <div className="flex gap-4 mb-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={wx.precip}
                onChange={(e) => setWx((prev) => ({ ...prev, precip: e.target.checked }))}
                className="w-3.5 h-3.5 accent-[#ff6b1a] cursor-pointer"
              />
              <span className="text-xs" style={{ color: 'rgba(255,255,255,0.7)' }}>Precipitation</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={wx.icing}
                onChange={(e) => setWx((prev) => ({ ...prev, icing: e.target.checked }))}
                className="w-3.5 h-3.5 accent-[#ff6b1a] cursor-pointer"
              />
              <span className="text-xs" style={{ color: 'rgba(255,255,255,0.7)' }}>Icing</span>
            </label>
          </div>

          <button
            onClick={submitWeather}
            disabled={wxBusy}
            className="px-3 py-1.5 text-xs font-semibold rounded-sm disabled:opacity-40 transition-opacity"
            style={{ background: '#ff6b1a', color: '#fff' }}
          >
            {wxBusy ? 'Submitting...' : 'Submit Weather Brief'}
          </button>
        </div>

        {/* ── 4. Safety Timeline ── */}
        <div
          className="p-4 rounded-sm"
          style={{ background: '#0b0f14', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.6)' }}>
              Safety Timeline
            </p>
            <button
              onClick={fetchTimeline}
              disabled={timelineBusy}
              className="px-3 py-1 text-xs font-semibold rounded-sm disabled:opacity-40 transition-opacity"
              style={{ background: 'rgba(255,107,26,0.15)', color: 'var(--q-orange)', border: '1px solid rgba(255,107,26,0.3)' }}
            >
              {timelineBusy ? 'Loading...' : 'Fetch Timeline'}
            </button>
          </div>

          {timeline.length === 0 ? (
            <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
              No events loaded. Enter a mission ID and click Fetch Timeline.
            </p>
          ) : (
            <div className="relative pl-4">
              {/* vertical line */}
              <div
                className="absolute left-1 top-0 bottom-0 w-px"
                style={{ background: 'rgba(255,255,255,0.08)' }}
              />
              <div className="space-y-3">
                {timeline.map((ev, i) => (
                  <div key={i} className="relative">
                    <div
                      className="absolute -left-[13px] top-1 w-2 h-2 rounded-full"
                      style={{ background: '#ff6b1a' }}
                    />
                    <p className="text-[10px] mb-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>
                      {fmtTs(ev.timestamp)}
                    </p>
                    <p className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.8)' }}>
                      {ev.event_type}
                    </p>
                    {ev.details && Object.keys(ev.details).length > 0 && (
                      <p className="text-[10px] mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        {JSON.stringify(ev.details)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
