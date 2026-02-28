'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return 'Bearer ' + (localStorage.getItem('qs_token') || '');
}

// ─── Types ────────────────────────────────────────────────────────────────────

type StepStatus = 'pending' | 'in_progress' | 'complete' | 'skipped';

interface StepState {
  id: string;
  label: string;
  status: StepStatus;
}

interface OnboardingStatus {
  onboarding_id: string;
  department?: { id: string; data?: { name?: string; reporting_mode?: string; [key: string]: unknown } };
  steps?: { id: string; label: string; status: StepStatus; required?: boolean }[];
  progress_percent?: number;
  required_complete?: number;
  required_total?: number;
  production_ready?: boolean;
  completed_at?: string | null;
  wi_dsps_checklist?: Record<string, boolean>;
  golive_items?: string[];
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
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500);
  }, []);
  return { toasts, push };
}

// ─── Step definitions ─────────────────────────────────────────────────────────

const STEP_DEFS = [
  { id: 'department_identity', label: 'Department Identity' },
  { id: 'reporting_mode', label: 'Reporting Mode' },
  { id: 'stations', label: 'Stations' },
  { id: 'apparatus', label: 'Apparatus' },
  { id: 'personnel', label: 'Personnel' },
  { id: 'pack_assignment', label: 'Pack Assignment' },
  { id: 'sample_incident', label: 'Sample Incident' },
  { id: 'golive_checklist', label: 'Go-Live Checklist' },
];

const UNIT_TYPES = ['ENGINE', 'LADDER', 'RESCUE', 'TANKER', 'BRUSH', 'COMMAND', 'UTILITY', 'AMBULANCE', 'HAZMAT', 'OTHER'];

const WI_CHECKLIST_ITEMS = [
  { id: 'dsps_1', label: 'Department registered with WI DSPS Fire Prevention' },
  { id: 'dsps_2', label: 'NERIS Reporting Agreement signed and on file' },
  { id: 'dsps_3', label: 'At least one apparatus record entered and validated' },
  { id: 'dsps_4', label: 'Primary contact designated and verified' },
  { id: 'dsps_5', label: 'Sample incident created with zero validation errors' },
  { id: 'dsps_6', label: 'Reporting mode confirmed as RMS (no CAD integration)' },
  { id: 'dsps_7', label: 'Active NERIS pack assigned by system administrator' },
  { id: 'dsps_8', label: 'Staff trained on FusionEMS NERIS data entry procedures' },
];

const INCIDENT_TYPE_VALUES = [
  { code: '100', label: 'Fire' },
  { code: '111', label: 'Building fire' },
  { code: '120', label: 'Fire in mobile property' },
  { code: '200', label: 'Overpressure rupture' },
  { code: '300', label: 'Rescue & EMS' },
  { code: '311', label: 'Medical assist, assist EMS crew' },
  { code: '320', label: 'Emergency medical service' },
  { code: '400', label: 'Hazardous condition' },
  { code: '500', label: 'Service call' },
  { code: '600', label: 'Good intent call' },
  { code: '700', label: 'False alarm' },
  { code: '800', label: 'Severe weather' },
  { code: '900', label: 'Special incident type' },
  { code: 'UNK', label: 'Unknown' },
];

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({
  steps,
  currentStepId,
  onStepClick,
}: {
  steps: StepState[];
  currentStepId: string;
  onStepClick: (id: string) => void;
}) {
  return (
    <div
      className="bg-bg-base border-r border-border-DEFAULT flex-shrink-0 overflow-y-auto"
      style={{ width: 200 }}
    >
      <div className="p-4 border-b border-border-DEFAULT">
        <p className="text-[9px] uppercase tracking-[0.2em] text-orange-dim">NERIS Onboarding</p>
        <p className="text-xs font-bold text-text-primary mt-0.5">Wisconsin</p>
      </div>
      <div className="py-2">
        {steps.map((step, index) => {
          const isActive = step.id === currentStepId;
          return (
            <button
              key={step.id}
              onClick={() => onStepClick(step.id)}
              className="w-full flex items-center gap-2.5 px-4 py-2.5 text-left transition-colors hover:bg-[rgba(255,255,255,0.03)]"
              style={isActive ? { background: 'rgba(255,107,26,0.08)' } : undefined}
            >
              <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                {step.status === 'complete' && (
                  <div className="w-4 h-4 rounded-full flex items-center justify-center" style={{ background: 'rgba(76,175,80,0.2)', border: '1px solid rgba(76,175,80,0.4)' }}>
                    <span className="text-[8px] text-status-active font-bold">✓</span>
                  </div>
                )}
                {step.status === 'in_progress' && (
                  <div className="w-3.5 h-3.5 rounded-full animate-pulse" style={{ background: 'var(--color-brand-orange)' }} />
                )}
                {step.status === 'skipped' && (
                  <div className="w-4 h-4 rounded-full flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)' }}>
                    <span className="text-[8px] text-[rgba(255,255,255,0.35)]">—</span>
                  </div>
                )}
                {step.status === 'pending' && (
                  <div className="w-4 h-4 rounded-full" style={{ border: '1px solid rgba(255,255,255,0.2)', background: 'transparent' }} />
                )}
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.3)] mr-1">
                  {index + 1}.
                </span>
                <span
                  className={`text-[11px] font-medium ${isActive ? 'text-[rgba(255,255,255,0.9)]' : 'text-[rgba(255,255,255,0.5)]'}`}
                >
                  {step.label}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Field helper ─────────────────────────────────────────────────────────────

const inputClass = "w-full bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-xs text-text-primary px-3 py-2 rounded-sm outline-none focus:border-[rgba(255,107,26,0.4)] placeholder:text-[rgba(255,255,255,0.2)]";
const labelClass = "block text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.4)] mb-1";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      {children}
    </div>
  );
}

function PrimaryBtn({ onClick, disabled, children }: { onClick: () => void; disabled?: boolean; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="h-9 px-5 text-[11px] font-bold uppercase tracking-wider rounded-sm transition-all hover:brightness-110 disabled:opacity-40"
      style={{ background: 'rgba(255,107,26,0.2)', border: '1px solid rgba(255,107,26,0.4)', color: 'var(--q-orange)' }}
    >
      {children}
    </button>
  );
}

function SecondaryBtn({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="h-9 px-4 text-[11px] font-semibold uppercase tracking-wider rounded-sm"
      style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.55)' }}
    >
      {children}
    </button>
  );
}

// ─── Step 1: Department Identity ──────────────────────────────────────────────

function Step1({ onComplete }: { onComplete: (data: unknown) => Promise<void> }) {
  const [name, setName] = useState('');
  const [contactName, setContactName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleComplete() {
    setLoading(true);
    await onComplete({ name, primary_contact_name: contactName, primary_contact_email: email, primary_contact_phone: phone });
    setLoading(false);
  }

  return (
    <div className="space-y-4 max-w-lg">
      <p className="text-xs text-[rgba(255,255,255,0.45)] leading-relaxed">
        Enter your department&rsquo;s basic identity information. This will be used in all NERIS submissions.
      </p>
      <Field label="Department Name">
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} className={inputClass} placeholder="e.g. Madison Fire Department" />
      </Field>
      <Field label="Primary Contact Name">
        <input type="text" value={contactName} onChange={(e) => setContactName(e.target.value)} className={inputClass} placeholder="Full name" />
      </Field>
      <Field label="Primary Contact Email">
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} placeholder="email@department.gov" />
      </Field>
      <Field label="Primary Contact Phone">
        <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} className={inputClass} placeholder="(608) 555-0100" />
      </Field>
      <div className="pt-2">
        <PrimaryBtn onClick={handleComplete} disabled={loading || !name.trim() || !email.trim()}>
          {loading ? 'Saving…' : 'Complete Step'}
        </PrimaryBtn>
      </div>
    </div>
  );
}

// ─── Step 2: Reporting Mode ───────────────────────────────────────────────────

function Step2({ onComplete }: { onComplete: (data: unknown) => Promise<void> }) {
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleComplete() {
    setLoading(true);
    await onComplete({ reporting_mode: 'RMS' });
    setLoading(false);
  }

  return (
    <div className="space-y-4 max-w-lg">
      <div className="p-4 rounded-sm" style={{ background: 'rgba(34,211,238,0.06)', border: '1px solid rgba(34,211,238,0.2)' }}>
        <p className="text-[10px] uppercase tracking-[0.15em] text-system-billing font-semibold mb-2">RMS Reporting (No CAD Integration)</p>
        <p className="text-xs text-[rgba(255,255,255,0.6)] leading-relaxed">
          Your department reports incidents directly through the Records Management System (RMS) without a Computer-Aided Dispatch (CAD) or 911 system integration.
          Incidents are manually entered by authorized personnel. This is the standard reporting mode for most Wisconsin fire departments using FusionEMS NERIS.
        </p>
      </div>
      <label className="flex items-start gap-3 cursor-pointer group">
        <div className="mt-0.5 flex-shrink-0">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
            className="hidden"
          />
          <div
            className="w-4 h-4 rounded-sm flex items-center justify-center transition-all"
            style={{
              background: confirmed ? 'rgba(255,107,26,0.2)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${confirmed ? 'rgba(255,107,26,0.5)' : 'rgba(255,255,255,0.15)'}`,
            }}
          >
            {confirmed && <span className="text-orange text-[10px] font-bold">✓</span>}
          </div>
        </div>
        <span className="text-xs text-[rgba(255,255,255,0.7)] leading-relaxed">
          Confirm: This department uses RMS-only reporting without CAD/911 integration
        </span>
      </label>
      <div className="pt-2">
        <PrimaryBtn onClick={handleComplete} disabled={loading || !confirmed}>
          {loading ? 'Saving…' : 'Complete Step'}
        </PrimaryBtn>
      </div>
    </div>
  );
}

// ─── Step 3: Stations ─────────────────────────────────────────────────────────

interface Station {
  name: string;
  street: string;
  city: string;
  state: string;
  zip: string;
}

function Step3({ onComplete }: { onComplete: (data: unknown) => Promise<void> }) {
  const [stations, setStations] = useState<Station[]>([{ name: '', street: '', city: '', state: 'WI', zip: '' }]);
  const [loading, setLoading] = useState(false);

  function addStation() {
    setStations((prev) => [...prev, { name: '', street: '', city: '', state: 'WI', zip: '' }]);
  }

  function removeStation(i: number) {
    setStations((prev) => prev.filter((_, idx) => idx !== i));
  }

  function updateStation(i: number, field: keyof Station, value: string) {
    setStations((prev) => prev.map((s, idx) => idx === i ? { ...s, [field]: value } : s));
  }

  async function handleComplete() {
    setLoading(true);
    await onComplete({
      stations: stations.map((s) => ({
        name: s.name,
        address: { street: s.street, city: s.city, state: s.state, zip: s.zip },
      })),
    });
    setLoading(false);
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <p className="text-xs text-[rgba(255,255,255,0.45)]">Add all active fire stations for your department.</p>
      {stations.map((station, i) => (
        <div key={i} className="bg-[rgba(255,255,255,0.02)] border border-border-subtle rounded-sm p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wider text-[rgba(255,107,26,0.7)] font-semibold">Station {i + 1}</span>
            {stations.length > 1 && (
              <button
                onClick={() => removeStation(i)}
                className="text-[10px] text-[rgba(229,57,53,0.7)] hover:text-red transition-colors"
              >
                Remove
              </button>
            )}
          </div>
          <Field label="Station Name">
            <input type="text" value={station.name} onChange={(e) => updateStation(i, 'name', e.target.value)} className={inputClass} placeholder="Station 1 — Downtown" />
          </Field>
          <Field label="Street Address">
            <input type="text" value={station.street} onChange={(e) => updateStation(i, 'street', e.target.value)} className={inputClass} placeholder="123 Main St" />
          </Field>
          <div className="grid grid-cols-3 gap-2">
            <Field label="City">
              <input type="text" value={station.city} onChange={(e) => updateStation(i, 'city', e.target.value)} className={inputClass} placeholder="Madison" />
            </Field>
            <Field label="State">
              <input type="text" value={station.state} onChange={(e) => updateStation(i, 'state', e.target.value)} className={inputClass} placeholder="WI" maxLength={2} />
            </Field>
            <Field label="ZIP">
              <input type="text" value={station.zip} onChange={(e) => updateStation(i, 'zip', e.target.value)} className={inputClass} placeholder="53703" />
            </Field>
          </div>
        </div>
      ))}
      <button
        onClick={addStation}
        className="h-8 px-4 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
        style={{ background: 'rgba(34,211,238,0.08)', border: '1px solid rgba(34,211,238,0.2)', color: 'var(--color-system-billing)' }}
      >
        + Add Station
      </button>
      <div className="pt-2">
        <PrimaryBtn onClick={handleComplete} disabled={loading || stations.every((s) => !s.name.trim())}>
          {loading ? 'Saving…' : 'Complete Step'}
        </PrimaryBtn>
      </div>
    </div>
  );
}

// ─── Step 4: Apparatus ────────────────────────────────────────────────────────

interface ApparatusRow {
  unit_id: string;
  unit_type_code: string;
  station_id: string;
}

function Step4({ onComplete }: { onComplete: (data: unknown) => Promise<void> }) {
  const [apparatus, setApparatus] = useState<ApparatusRow[]>([{ unit_id: '', unit_type_code: 'ENGINE', station_id: '' }]);
  const [loading, setLoading] = useState(false);

  function addRow() {
    setApparatus((prev) => [...prev, { unit_id: '', unit_type_code: 'ENGINE', station_id: '' }]);
  }

  function removeRow(i: number) {
    setApparatus((prev) => prev.filter((_, idx) => idx !== i));
  }

  function updateRow(i: number, field: keyof ApparatusRow, value: string) {
    setApparatus((prev) => prev.map((a, idx) => idx === i ? { ...a, [field]: value } : a));
  }

  async function handleComplete() {
    setLoading(true);
    await onComplete({ apparatus });
    setLoading(false);
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <p className="text-xs text-[rgba(255,255,255,0.45)]">Enter all apparatus (fire vehicles/units) operated by your department.</p>
      {apparatus.map((row, i) => (
        <div key={i} className="bg-[rgba(255,255,255,0.02)] border border-border-subtle rounded-sm p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] uppercase tracking-wider text-[rgba(255,107,26,0.7)] font-semibold">Unit {i + 1}</span>
            {apparatus.length > 1 && (
              <button onClick={() => removeRow(i)} className="text-[10px] text-[rgba(229,57,53,0.7)] hover:text-red transition-colors">Remove</button>
            )}
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Unit ID">
              <input type="text" value={row.unit_id} onChange={(e) => updateRow(i, 'unit_id', e.target.value)} className={inputClass} placeholder="E-1" />
            </Field>
            <Field label="Unit Type">
              <select
                value={row.unit_type_code}
                onChange={(e) => updateRow(i, 'unit_type_code', e.target.value)}
                className={inputClass}
                style={{ background: 'var(--color-bg-base)' }}
              >
                {UNIT_TYPES.map((t) => (
                  <option key={t} value={t} className="bg-bg-base">{t}</option>
                ))}
              </select>
            </Field>
            <Field label="Station (optional)">
              <input type="text" value={row.station_id} onChange={(e) => updateRow(i, 'station_id', e.target.value)} className={inputClass} placeholder="Station 1" />
            </Field>
          </div>
        </div>
      ))}
      <button
        onClick={addRow}
        className="h-8 px-4 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
        style={{ background: 'rgba(34,211,238,0.08)', border: '1px solid rgba(34,211,238,0.2)', color: 'var(--color-system-billing)' }}
      >
        + Add Unit
      </button>
      <div className="pt-2">
        <PrimaryBtn onClick={handleComplete} disabled={loading || apparatus.every((a) => !a.unit_id.trim())}>
          {loading ? 'Saving…' : 'Complete Step'}
        </PrimaryBtn>
      </div>
    </div>
  );
}

// ─── Step 5: Personnel ────────────────────────────────────────────────────────

interface PersonnelRow { name: string; role: string }

function Step5({ onComplete }: { onComplete: (data: unknown) => Promise<void> }) {
  const [personnel, setPersonnel] = useState<PersonnelRow[]>([{ name: '', role: '' }]);
  const [loading, setLoading] = useState(false);

  function addRow() {
    setPersonnel((prev) => [...prev, { name: '', role: '' }]);
  }

  function removeRow(i: number) {
    setPersonnel((prev) => prev.filter((_, idx) => idx !== i));
  }

  function updateRow(i: number, field: keyof PersonnelRow, value: string) {
    setPersonnel((prev) => prev.map((p, idx) => idx === i ? { ...p, [field]: value } : p));
  }

  async function handleComplete(skip = false) {
    setLoading(true);
    await onComplete({ personnel: skip ? [] : personnel.filter((p) => p.name.trim()) });
    setLoading(false);
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <p className="text-xs text-[rgba(255,255,255,0.45)]">
        Optionally add personnel (firefighters, officers). You can skip this step and add personnel later.
      </p>
      {personnel.map((row, i) => (
        <div key={i} className="flex gap-3 items-start">
          <div className="flex-1">
            <Field label="Name">
              <input type="text" value={row.name} onChange={(e) => updateRow(i, 'name', e.target.value)} className={inputClass} placeholder="Full name" />
            </Field>
          </div>
          <div className="flex-1">
            <Field label="Role (optional)">
              <input type="text" value={row.role} onChange={(e) => updateRow(i, 'role', e.target.value)} className={inputClass} placeholder="Captain, Firefighter…" />
            </Field>
          </div>
          {personnel.length > 1 && (
            <button onClick={() => removeRow(i)} className="mt-5 text-[10px] text-[rgba(229,57,53,0.7)] hover:text-red transition-colors">✕</button>
          )}
        </div>
      ))}
      <button
        onClick={addRow}
        className="h-8 px-4 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
        style={{ background: 'rgba(34,211,238,0.08)', border: '1px solid rgba(34,211,238,0.2)', color: 'var(--color-system-billing)' }}
      >
        + Add Person
      </button>
      <div className="flex items-center gap-3 pt-2">
        <PrimaryBtn onClick={() => handleComplete(false)} disabled={loading || personnel.every((p) => !p.name.trim())}>
          {loading ? 'Saving…' : 'Complete Step'}
        </PrimaryBtn>
        <SecondaryBtn onClick={() => handleComplete(true)}>Skip this step</SecondaryBtn>
      </div>
    </div>
  );
}

// ─── Step 6: Pack Assignment ──────────────────────────────────────────────────

function Step6({
  onComplete,
  assignedPackName,
}: {
  onComplete: (data: unknown) => Promise<void>;
  assignedPackName?: string;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [packName, setPackName] = useState(assignedPackName ?? '');

  async function handleAssign() {
    setLoading(true);
    setError('');
    try {
      await onComplete({});
      setDone(true);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      if (msg.includes('no_active_neris_pack')) {
        setError('No active NERIS pack found. Contact your administrator.');
      } else {
        setError(msg || 'Assignment failed');
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!done && !assignedPackName) {
      handleAssign();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-4 max-w-lg">
      {loading && !done && (
        <div className="flex items-center gap-3 p-4 rounded-sm" style={{ background: 'rgba(255,107,26,0.06)', border: '1px solid rgba(255,107,26,0.2)' }}>
          <div className="w-4 h-4 rounded-full animate-pulse" style={{ background: 'var(--color-brand-orange)' }} />
          <span className="text-xs text-[rgba(255,255,255,0.7)]">Auto-assigning active NERIS pack…</span>
        </div>
      )}
      {error && (
        <div className="p-4 rounded-sm" style={{ background: 'rgba(255,152,0,0.08)', border: '1px solid rgba(255,152,0,0.25)' }}>
          <p className="text-xs font-semibold" style={{ color: 'var(--q-yellow)' }}>Warning</p>
          <p className="text-xs text-[rgba(255,255,255,0.6)] mt-1">{error}</p>
        </div>
      )}
      {(done || assignedPackName) && packName && (
        <div className="p-4 rounded-sm" style={{ background: 'rgba(76,175,80,0.08)', border: '1px solid rgba(76,175,80,0.25)' }}>
          <p className="text-xs font-semibold text-status-active">Pack Assigned Successfully</p>
          <p className="text-xs text-text-secondary mt-1 font-mono">{packName}</p>
        </div>
      )}
      {(done || error) && (
        <div className="pt-2">
          <PrimaryBtn
            onClick={async () => {
              setLoading(true);
              await onComplete({});
              setLoading(false);
            }}
            disabled={loading || !!error}
          >
            {loading ? 'Saving…' : 'Proceed'}
          </PrimaryBtn>
        </div>
      )}
    </div>
  );
}

// ─── Step 7: Sample Incident ──────────────────────────────────────────────────

interface SampleIncidentForm {
  incident_number: string;
  start_datetime: string;
  incident_type_code: string;
  street: string;
  city: string;
  state: string;
  zip: string;
}

interface ValidationIssue {
  severity: 'error' | 'warning';
  field_label?: string;
  path?: string;
  message: string;
  suggested_fix?: string;
}

function Step7({ onComplete }: { onComplete: (data: unknown) => Promise<void> }) {
  const [form, setForm] = useState<SampleIncidentForm>({
    incident_number: '',
    start_datetime: '',
    incident_type_code: '100',
    street: '',
    city: '',
    state: 'WI',
    zip: '',
  });
  const [loading, setLoading] = useState(false);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [validationDone, setValidationDone] = useState(false);
  const [error, setError] = useState('');

  function update(field: keyof SampleIncidentForm, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleCreateAndValidate() {
    setLoading(true);
    setError('');
    setIssues([]);
    setValidationDone(false);
    setCreatedId(null);
    try {
      const createRes = await fetch(`${API}/api/v1/incidents/fire`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          incident_number: form.incident_number,
          start_datetime: form.start_datetime,
          incident_type_code: form.incident_type_code,
          address: { street: form.street, city: form.city, state: form.state, zip: form.zip },
        }),
      });
      const createJson = await createRes.json();
      if (!createRes.ok) throw new Error(createJson.detail ?? `HTTP ${createRes.status}`);
      const incidentId = createJson.id ?? createJson.incident_id;
      setCreatedId(incidentId);

      const valRes = await fetch(`${API}/api/v1/incidents/fire/${incidentId}/validate`, {
        method: 'POST',
        headers: { Authorization: getToken() },
      });
      const valJson = await valRes.json();
      setIssues(valJson.issues ?? []);
      setValidationDone(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create/validate incident');
    } finally {
      setLoading(false);
    }
  }

  const errorCount = issues.filter((i) => i.severity === 'error').length;

  async function handleComplete() {
    if (!createdId) return;
    setLoading(true);
    await onComplete({ sample_incident_id: createdId });
    setLoading(false);
  }

  return (
    <div className="space-y-4 max-w-xl">
      <p className="text-xs text-[rgba(255,255,255,0.45)]">Create a sample incident to verify your NERIS configuration. The incident must pass validation (0 errors) to continue.</p>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Incident Number">
          <input type="text" value={form.incident_number} onChange={(e) => update('incident_number', e.target.value)} className={inputClass} placeholder="2025-001" />
        </Field>
        <Field label="Start Date/Time">
          <input type="datetime-local" value={form.start_datetime} onChange={(e) => update('start_datetime', e.target.value)} className={inputClass} />
        </Field>
      </div>
      <Field label="Incident Type">
        <select value={form.incident_type_code} onChange={(e) => update('incident_type_code', e.target.value)} className={inputClass} style={{ background: 'var(--color-bg-base)' }}>
          {INCIDENT_TYPE_VALUES.map((v) => (
            <option key={v.code} value={v.code} className="bg-bg-base">{v.label}</option>
          ))}
        </select>
      </Field>
      <Field label="Street Address">
        <input type="text" value={form.street} onChange={(e) => update('street', e.target.value)} className={inputClass} placeholder="123 Main St" />
      </Field>
      <div className="grid grid-cols-3 gap-2">
        <Field label="City">
          <input type="text" value={form.city} onChange={(e) => update('city', e.target.value)} className={inputClass} placeholder="Madison" />
        </Field>
        <Field label="State">
          <input type="text" value={form.state} onChange={(e) => update('state', e.target.value)} className={inputClass} placeholder="WI" maxLength={2} />
        </Field>
        <Field label="ZIP">
          <input type="text" value={form.zip} onChange={(e) => update('zip', e.target.value)} className={inputClass} placeholder="53703" />
        </Field>
      </div>
      {error && <p className="text-xs text-red">{error}</p>}
      <div className="pt-1">
        <button
          onClick={handleCreateAndValidate}
          disabled={loading || !form.incident_number.trim() || !form.start_datetime}
          className="h-9 px-5 text-[11px] font-bold uppercase tracking-wider rounded-sm transition-all hover:brightness-110 disabled:opacity-40"
          style={{ background: 'rgba(34,211,238,0.14)', border: '1px solid rgba(34,211,238,0.3)', color: 'var(--color-system-billing)' }}
        >
          {loading ? 'Working…' : 'Create & Validate'}
        </button>
      </div>
      {validationDone && (
        <div className="space-y-3">
          {errorCount === 0 ? (
            <div className="p-3 rounded-sm" style={{ background: 'rgba(76,175,80,0.08)', border: '1px solid rgba(76,175,80,0.25)' }}>
              <p className="text-xs font-semibold text-status-active">Validation Passed — 0 errors</p>
              {issues.length > 0 && (
                <p className="text-[11px] text-[rgba(255,255,255,0.5)] mt-0.5">{issues.filter((i) => i.severity === 'warning').length} warning(s)</p>
              )}
            </div>
          ) : (
            <div className="p-3 rounded-sm" style={{ background: 'rgba(229,57,53,0.07)', border: '1px solid rgba(229,57,53,0.2)' }}>
              <p className="text-xs font-semibold text-red">{errorCount} validation error{errorCount !== 1 ? 's' : ''}</p>
              <p className="text-[11px] text-[rgba(255,255,255,0.45)] mt-1">Fix the errors below and re-validate.</p>
            </div>
          )}
          {issues.length > 0 && (
            <div className="space-y-2 max-h-56 overflow-y-auto">
              {issues.map((issue, i) => (
                <div
                  key={i}
                  className="p-2.5 rounded-sm"
                  style={{
                    background: issue.severity === 'error' ? 'rgba(229,57,53,0.06)' : 'rgba(255,152,0,0.06)',
                    border: `1px solid ${issue.severity === 'error' ? 'rgba(229,57,53,0.18)' : 'rgba(255,152,0,0.18)'}`,
                  }}
                >
                  <span className="text-[9px] font-bold uppercase" style={{ color: issue.severity === 'error' ? 'var(--color-brand-red)' : 'var(--color-status-warning)' }}>
                    {issue.severity}
                  </span>
                  {issue.field_label && <span className="ml-1.5 text-xs font-medium text-[rgba(255,255,255,0.75)]">{issue.field_label}</span>}
                  <p className="text-[11px] text-[rgba(255,255,255,0.6)] mt-0.5">{issue.message}</p>
                  {issue.suggested_fix && <p className="text-[10px] text-[rgba(255,255,255,0.35)] mt-0.5">{issue.suggested_fix}</p>}
                </div>
              ))}
            </div>
          )}
          {errorCount === 0 && (
            <div className="pt-1">
              <PrimaryBtn onClick={handleComplete} disabled={loading}>
                {loading ? 'Saving…' : 'Complete Step'}
              </PrimaryBtn>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Step 8: Go-Live Checklist ────────────────────────────────────────────────

function Step8({ onComplete }: { onComplete: (data: unknown) => Promise<void> }) {
  const [checked, setChecked] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    for (const item of WI_CHECKLIST_ITEMS) init[item.id] = false;
    return init;
  });
  const [loading, setLoading] = useState(false);

  function toggle(id: string) {
    setChecked((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  const allChecked = WI_CHECKLIST_ITEMS.every((item) => checked[item.id]);

  async function handleComplete() {
    setLoading(true);
    await onComplete({ checklist: checked });
    setLoading(false);
  }

  return (
    <div className="space-y-4 max-w-xl">
      <p className="text-xs text-[rgba(255,255,255,0.45)]">Review and confirm all Wisconsin DSPS go-live requirements.</p>
      <div className="space-y-2">
        {WI_CHECKLIST_ITEMS.map((item) => (
          <label key={item.id} className="flex items-start gap-3 cursor-pointer group">
            <div className="mt-0.5 flex-shrink-0" onClick={() => toggle(item.id)}>
              <div
                className="w-4 h-4 rounded-sm flex items-center justify-center transition-all"
                style={{
                  background: checked[item.id] ? 'rgba(76,175,80,0.2)' : 'rgba(255,255,255,0.04)',
                  border: `1px solid ${checked[item.id] ? 'rgba(76,175,80,0.5)' : 'rgba(255,255,255,0.15)'}`,
                }}
              >
                {checked[item.id] && <span className="text-status-active text-[10px] font-bold">✓</span>}
              </div>
            </div>
            <span className="text-xs text-[rgba(255,255,255,0.75)] leading-relaxed">{item.label}</span>
          </label>
        ))}
      </div>
      <div className="flex items-center gap-3 pt-2 flex-wrap">
        <PrimaryBtn onClick={handleComplete} disabled={loading || !allChecked}>
          {loading ? 'Saving…' : 'Mark Complete'}
        </PrimaryBtn>
        <button
          onClick={() => window.print()}
          className="h-9 px-4 text-[11px] font-semibold uppercase tracking-wider rounded-sm"
          style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.55)' }}
        >
          Print
        </button>
        {!allChecked && (
          <span className="text-[10px] text-[rgba(255,255,255,0.35)]">Check all items to complete</span>
        )}
      </div>
    </div>
  );
}

// ─── Complete Banner ──────────────────────────────────────────────────────────

function CompleteBanner({ departmentName }: { departmentName?: string }) {
  return (
    <div className="p-8 rounded-sm text-center space-y-4" style={{ background: 'rgba(76,175,80,0.07)', border: '1px solid rgba(76,175,80,0.3)' }}>
      <div className="text-4xl">🏆</div>
      <div>
        <p className="text-[10px] uppercase tracking-[0.25em] text-status-active font-bold mb-1">NERIS Onboarding Complete</p>
        <h2 className="text-xl font-black uppercase tracking-wider text-text-primary">READY FOR PRODUCTION</h2>
        {departmentName && (
          <p className="text-sm text-[rgba(255,255,255,0.55)] mt-1">{departmentName}</p>
        )}
      </div>
      <p className="text-xs text-[rgba(255,255,255,0.5)] max-w-sm mx-auto leading-relaxed">
        Your department has completed all Wisconsin NERIS onboarding steps and is authorized to begin production incident reporting.
      </p>
      <button
        onClick={() => window.print()}
        className="h-9 px-5 text-[11px] font-bold uppercase tracking-wider rounded-sm"
        style={{ background: 'rgba(76,175,80,0.2)', border: '1px solid rgba(76,175,80,0.4)', color: 'var(--q-green)' }}
      >
        Print Summary
      </button>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function NerisOnboardingPage() {
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null);
  const [notStarted, setNotStarted] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [departmentNameInput, setDepartmentNameInput] = useState('');
  const [startLoading, setStartLoading] = useState(false);
  const [currentStepId, setCurrentStepId] = useState(STEP_DEFS[0].id);
  const [allComplete, setAllComplete] = useState(false);
  const { toasts, push: pushToast } = useToast();

  const stepStates: StepState[] = STEP_DEFS.map((def) => ({
    id: def.id,
    label: def.label,
    status: onboardingStatus?.steps?.find((s) => s.id === def.id)?.status ?? 'pending',
  }));

  // Determine active step from status
  useEffect(() => {
    if (!onboardingStatus?.steps) return;
    const steps = onboardingStatus.steps;
    const firstIncomplete = STEP_DEFS.find(
      (d) => {
        const s = steps.find((st) => st.id === d.id)?.status;
        return s !== 'complete' && s !== 'skipped';
      }
    );
    if (!firstIncomplete) {
      setAllComplete(true);
    } else {
      setCurrentStepId(firstIncomplete.id);
    }
  }, [onboardingStatus]);

  const fetchStatus = useCallback(async () => {
    setLoadingStatus(true);
    try {
      const res = await fetch(`${API}/api/v1/tenant/neris/onboarding/status`, {
        headers: { Authorization: getToken() },
      });
      if (res.status === 404) {
        setNotStarted(true);
        return;
      }
      const data = await res.json();
      if (!data || !data.onboarding_id) {
        setNotStarted(true);
        return;
      }
      setOnboardingStatus(data);
    } catch {
      setNotStarted(true);
    } finally {
      setLoadingStatus(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  async function handleStart() {
    if (!departmentNameInput.trim()) return;
    setStartLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/tenant/neris/onboarding/start`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ department_name: departmentNameInput, state: 'WI' }),
      });
      if (!res.ok) throw new Error();
      setNotStarted(false);
      await fetchStatus();
    } catch {
      pushToast('Failed to start onboarding', 'error');
    } finally {
      setStartLoading(false);
    }
  }

  async function completeStep(stepId: string, data: unknown) {
    const res = await fetch(`${API}/api/v1/tenant/neris/onboarding/step/${stepId}/complete`, {
      method: 'POST',
      headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ data }),
    });
    const json = await res.json();
    if (!res.ok) {
      const detail = json.detail ?? `HTTP ${res.status}`;
      pushToast(`Step failed: ${detail}`, 'error');
      throw new Error(detail);
    }
    pushToast('Step completed', 'success');
    // Optimistically advance
    setOnboardingStatus((prev) => {
      if (!prev) return prev;
      const prevSteps = prev.steps ?? [];
      const steps = prevSteps.map((s) =>
        s.id === stepId ? { ...s, status: 'complete' as StepStatus } : s
      );
      return { ...prev, steps };
    });
    await fetchStatus();
  }

  if (loadingStatus) {
    return (
      <div className="min-h-screen bg-bg-void flex items-center justify-center">
        <div className="text-[rgba(255,255,255,0.3)] text-sm">Loading onboarding status…</div>
      </div>
    );
  }

  if (notStarted) {
    return (
      <div className="min-h-screen bg-bg-void flex items-center justify-center p-6">
        <Toast items={toasts} />
        <div className="bg-bg-base border border-border-DEFAULT rounded-sm p-8 w-full max-w-md space-y-5">
          <div>
            <p className="text-[9px] uppercase tracking-[0.2em] text-orange-dim mb-1">Portal · NERIS</p>
            <h1 className="text-lg font-black uppercase tracking-wider text-text-primary">Start NERIS Onboarding</h1>
            <p className="text-xs text-text-muted mt-1">Wisconsin RMS-Only · DSPS Fire Prevention</p>
          </div>
          <Field label="Department Name">
            <input
              type="text"
              value={departmentNameInput}
              onChange={(e) => setDepartmentNameInput(e.target.value)}
              className={inputClass}
              placeholder="e.g. Madison Fire Department"
            />
          </Field>
          <PrimaryBtn onClick={handleStart} disabled={startLoading || !departmentNameInput.trim()}>
            {startLoading ? 'Starting…' : 'Start NERIS Onboarding'}
          </PrimaryBtn>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-void text-text-primary flex flex-col">
      <Toast items={toasts} />
      {/* Header */}
      <div className="bg-bg-base border-b border-border-DEFAULT px-5 py-3 flex items-center gap-4 flex-shrink-0">
        <div>
          <p className="text-[9px] uppercase tracking-[0.2em] text-orange-dim">Portal · NERIS Onboarding</p>
          <h1 className="text-sm font-black uppercase tracking-wider text-text-primary">
            {onboardingStatus?.department?.data?.name ?? 'NERIS Onboarding Wizard'}
          </h1>
        </div>
        <span className="ml-auto text-[10px] text-[rgba(255,255,255,0.3)]">Wisconsin RMS-Only</span>
      </div>
      {/* Body */}
      <div className="flex flex-1 min-h-0">
        <Sidebar
          steps={stepStates}
          currentStepId={currentStepId}
          onStepClick={setCurrentStepId}
        />
        <div className="flex-1 overflow-y-auto p-6">
          {allComplete ? (
            <CompleteBanner departmentName={onboardingStatus?.department?.data?.name} />
          ) : (
            <div>
              {/* Step header */}
              <div className="mb-5">
                <div className="text-[9px] uppercase tracking-[0.18em] text-orange-dim mb-0.5">
                  Step {STEP_DEFS.findIndex((d) => d.id === currentStepId) + 1} of {STEP_DEFS.length}
                </div>
                <h2 className="text-base font-bold uppercase tracking-wider text-text-primary">
                  {STEP_DEFS.find((d) => d.id === currentStepId)?.label}
                </h2>
              </div>
              {/* Step content */}
              {currentStepId === 'department_identity' && (
                <Step1 onComplete={(data) => completeStep('department_identity', data)} />
              )}
              {currentStepId === 'reporting_mode' && (
                <Step2 onComplete={(data) => completeStep('reporting_mode', data)} />
              )}
              {currentStepId === 'stations' && (
                <Step3 onComplete={(data) => completeStep('stations', data)} />
              )}
              {currentStepId === 'apparatus' && (
                <Step4 onComplete={(data) => completeStep('apparatus', data)} />
              )}
              {currentStepId === 'personnel' && (
                <Step5 onComplete={(data) => completeStep('personnel', data)} />
              )}
              {currentStepId === 'pack_assignment' && (
                <Step6
                  onComplete={(data) => completeStep('pack_assignment', data)}
                  assignedPackName={undefined}
                />
              )}
              {currentStepId === 'sample_incident' && (
                <Step7 onComplete={(data) => completeStep('sample_incident', data)} />
              )}
              {currentStepId === 'golive_checklist' && (
                <Step8 onComplete={(data) => completeStep('golive_checklist', data)} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
