'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return 'Bearer ' + (localStorage.getItem('qs_token') || '');
}

// ─── Types ────────────────────────────────────────────────────────────────────

type IncidentStatus = 'draft' | 'validated' | 'exported';

interface Incident {
  id: string;
  incident_number: string;
  incident_type_code: string;
  start_datetime: string;
  status: IncidentStatus;
  [key: string]: unknown;
}

interface ValidationIssue {
  severity: 'error' | 'warning';
  field_label?: string;
  path?: string;
  ui_section?: string;
  message: string;
  suggested_fix?: string;
}

interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
}

interface RuleField {
  path: string;
  field_label?: string;
  type?: string;
  required?: boolean;
  value_set?: string[];
}

interface RuleSection {
  id: string;
  label: string;
  fields: RuleField[];
}

interface PackRules {
  sections?: RuleSection[];
  value_sets?: Record<string, string[]>;
}

interface ApparatusOption {
  id: string;
  unit_id: string;
  unit_type_code: string;
}

// Incident form state shape
interface UnitEntry {
  apparatus_id: string;
  arrival_time: string;
  departure_time: string;
}

interface ActionEntry {
  action_code: string;
  action_datetime: string;
}

interface IncidentForm {
  incident_number: string;
  start_datetime: string;
  end_datetime: string;
  incident_type_code: string;
  street: string;
  city: string;
  state: string;
  zip: string;
  property_use_code: string;
  on_site_materials: string;
  units: UnitEntry[];
  actions: ActionEntry[];
  civilian_injuries: string;
  civilian_fatalities: string;
  firefighter_injuries: string;
  firefighter_fatalities: string;
  property_loss_estimate: string;
  contents_loss_estimate: string;
}

type StatusFilter = 'all' | IncidentStatus;

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

// ─── Status Badge ─────────────────────────────────────────────────────────────

const STATUS_STYLE: Record<IncidentStatus, { label: string; color: string; bg: string }> = {
  draft:      { label: 'DRAFT',      color: 'rgba(255,255,255,0.5)', bg: 'rgba(255,255,255,0.07)' },
  validated:  { label: 'VALIDATED',  color: '#4caf50',               bg: 'rgba(76,175,80,0.12)' },
  exported:   { label: 'EXPORTED',   color: '#22d3ee',               bg: 'rgba(34,211,238,0.12)' },
};

function IncidentStatusBadge({ status }: { status: IncidentStatus }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.draft;
  return (
    <span
      className="px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider rounded-sm whitespace-nowrap"
      style={{ color: s.color, background: s.bg }}
    >
      {s.label}
    </span>
  );
}

function IncidentTypeBadge({ code }: { code: string }) {
  return (
    <span
      className="px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider rounded-sm"
      style={{ color: '#ff9800', background: 'rgba(255,152,0,0.1)', border: '1px solid rgba(255,152,0,0.2)' }}
    >
      {code.replace(/_/g, ' ')}
    </span>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const inputClass = "w-full bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[rgba(255,107,26,0.35)] placeholder:text-[rgba(255,255,255,0.2)]";
const inputErrorClass = "w-full bg-[rgba(229,57,53,0.05)] border border-[rgba(229,57,53,0.4)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[rgba(229,57,53,0.6)] placeholder:text-[rgba(255,255,255,0.2)]";
const labelClass = "block text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.4)] mb-1";

function makeEmptyForm(): IncidentForm {
  return {
    incident_number: '',
    start_datetime: '',
    end_datetime: '',
    incident_type_code: '',
    street: '',
    city: '',
    state: 'WI',
    zip: '',
    property_use_code: '',
    on_site_materials: '',
    units: [{ apparatus_id: '', arrival_time: '', departure_time: '' }],
    actions: [{ action_code: '', action_datetime: '' }],
    civilian_injuries: '0',
    civilian_fatalities: '0',
    firefighter_injuries: '0',
    firefighter_fatalities: '0',
    property_loss_estimate: '',
    contents_loss_estimate: '',
  };
}

// ─── Incident List ────────────────────────────────────────────────────────────

function IncidentList({
  incidents,
  loading,
  selectedId,
  statusFilter,
  onSelect,
  onNew,
  onFilterChange,
}: {
  incidents: Incident[];
  loading: boolean;
  selectedId: string | null;
  statusFilter: StatusFilter;
  onSelect: (inc: Incident) => void;
  onNew: () => void;
  onFilterChange: (f: StatusFilter) => void;
}) {
  const filters: { value: StatusFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'draft', label: 'Draft' },
    { value: 'validated', label: 'Validated' },
    { value: 'exported', label: 'Exported' },
  ];

  return (
    <div className="flex flex-col h-full border-r border-[rgba(255,255,255,0.08)]" style={{ width: 300, flexShrink: 0 }}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-[rgba(255,255,255,0.08)] flex items-center justify-between">
        <div>
          <p className="text-[9px] uppercase tracking-[0.18em] text-[rgba(255,107,26,0.6)]">Portal</p>
          <h2 className="text-sm font-bold uppercase tracking-wider text-white">Fire Incidents</h2>
        </div>
        <button
          onClick={onNew}
          className="h-7 px-3 text-[10px] font-bold uppercase tracking-wider rounded-sm"
          style={{ background: 'rgba(255,107,26,0.18)', border: '1px solid rgba(255,107,26,0.35)', color: '#ff6b1a' }}
        >
          + New
        </button>
      </div>
      {/* Filter */}
      <div className="px-3 py-2 border-b border-[rgba(255,255,255,0.06)] flex gap-1 flex-wrap">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => onFilterChange(f.value)}
            className="h-6 px-2 text-[9px] font-semibold uppercase tracking-wider rounded-sm transition-colors"
            style={statusFilter === f.value
              ? { background: 'rgba(255,107,26,0.2)', color: '#ff6b1a', border: '1px solid rgba(255,107,26,0.35)' }
              : { background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.45)', border: '1px solid rgba(255,255,255,0.07)' }
            }
          >
            {f.label}
          </button>
        ))}
      </div>
      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="py-8 text-center text-[11px] text-[rgba(255,255,255,0.3)]">Loading…</div>
        )}
        {!loading && incidents.length === 0 && (
          <div className="py-8 text-center text-[11px] text-[rgba(255,255,255,0.3)]">No incidents found</div>
        )}
        {!loading && incidents.map((inc) => (
          <button
            key={inc.id}
            onClick={() => onSelect(inc)}
            className="w-full text-left px-4 py-3 border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.03)] transition-colors"
            style={selectedId === inc.id ? { background: 'rgba(255,107,26,0.07)' } : undefined}
          >
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <span className="text-xs font-semibold text-[rgba(255,255,255,0.85)] font-mono truncate">{inc.incident_number}</span>
              <IncidentStatusBadge status={inc.status} />
            </div>
            <IncidentTypeBadge code={inc.incident_type_code} />
            <p className="text-[10px] text-[rgba(255,255,255,0.35)] mt-1 font-mono">
              {inc.start_datetime ? new Date(inc.start_datetime).toLocaleString() : '—'}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Form Section Accordion ───────────────────────────────────────────────────

function FormSection({
  id,
  label,
  errorCount,
  children,
}: {
  id: string;
  label: string;
  errorCount: number;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(true);
  return (
    <div
      className="bg-[#0b0f14] border rounded-sm overflow-hidden"
      style={{ borderColor: errorCount > 0 ? 'rgba(229,57,53,0.35)' : 'rgba(255,255,255,0.08)' }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[rgba(255,255,255,0.02)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-[rgba(255,255,255,0.85)]">{label}</span>
          {errorCount > 0 && (
            <span className="px-1.5 py-0.5 text-[9px] font-bold uppercase rounded-sm" style={{ color: '#e53935', background: 'rgba(229,57,53,0.15)' }}>
              {errorCount} error{errorCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <span className="text-[rgba(255,255,255,0.4)] text-sm">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 border-t border-[rgba(255,255,255,0.05)]">
          <div className="pt-4">{children}</div>
        </div>
      )}
    </div>
  );
}

// ─── Field with validation ────────────────────────────────────────────────────

function FormField({
  label,
  required,
  error,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className={labelClass}>
        {label}
        {required && <span className="ml-1" style={{ color: '#ff6b1a' }}>*</span>}
      </label>
      {children}
      {error && <p className="text-[10px] text-[#e53935] mt-0.5">{error}</p>}
    </div>
  );
}

// ─── Main Form ────────────────────────────────────────────────────────────────

function IncidentForm({
  selectedIncident,
  packRules,
  apparatus,
  onSaved,
  pushToast,
}: {
  selectedIncident: Incident | null;
  packRules: PackRules | null;
  apparatus: ApparatusOption[];
  onSaved: (inc: Incident) => void;
  pushToast: (msg: string, type: 'success' | 'error') => void;
}) {
  const [form, setForm] = useState<IncidentForm>(makeEmptyForm());
  const [savingDraft, setSavingDraft] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [exportingId, setExportingId] = useState<string | null>(null);
  const [currentId, setCurrentId] = useState<string | null>(null);

  // Populate form when selecting an existing incident
  useEffect(() => {
    if (!selectedIncident) {
      setForm(makeEmptyForm());
      setCurrentId(null);
      setValidationResult(null);
      return;
    }
    const inc = selectedIncident;
    setCurrentId(inc.id);
    setValidationResult(null);
    setForm({
      incident_number: String(inc.incident_number ?? ''),
      start_datetime: String(inc.start_datetime ?? ''),
      end_datetime: String((inc as Record<string, unknown>).end_datetime ?? ''),
      incident_type_code: String(inc.incident_type_code ?? ''),
      street: String((inc as Record<string, unknown>).street ?? ''),
      city: String((inc as Record<string, unknown>).city ?? ''),
      state: String((inc as Record<string, unknown>).state ?? 'WI'),
      zip: String((inc as Record<string, unknown>).zip ?? ''),
      property_use_code: String((inc as Record<string, unknown>).property_use_code ?? ''),
      on_site_materials: String((inc as Record<string, unknown>).on_site_materials ?? ''),
      units: ((inc as Record<string, unknown>).units as UnitEntry[]) ?? [{ apparatus_id: '', arrival_time: '', departure_time: '' }],
      actions: ((inc as Record<string, unknown>).actions as ActionEntry[]) ?? [{ action_code: '', action_datetime: '' }],
      civilian_injuries: String((inc as Record<string, unknown>).civilian_injuries ?? '0'),
      civilian_fatalities: String((inc as Record<string, unknown>).civilian_fatalities ?? '0'),
      firefighter_injuries: String((inc as Record<string, unknown>).firefighter_injuries ?? '0'),
      firefighter_fatalities: String((inc as Record<string, unknown>).firefighter_fatalities ?? '0'),
      property_loss_estimate: String((inc as Record<string, unknown>).property_loss_estimate ?? ''),
      contents_loss_estimate: String((inc as Record<string, unknown>).contents_loss_estimate ?? ''),
    });
  }, [selectedIncident]);

  function update(field: keyof IncidentForm, value: unknown) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  // Helpers: get validation issues by section
  function issuesForSection(sectionId: string): ValidationIssue[] {
    if (!validationResult) return [];
    return validationResult.issues.filter((i) => i.ui_section === sectionId);
  }

  function fieldError(path: string): string | undefined {
    if (!validationResult) return undefined;
    const issue = validationResult.issues.find(
      (i) => i.path === path && i.severity === 'error'
    );
    return issue?.message;
  }

  // Value sets from pack rules
  const valueSet = useCallback((name: string): string[] => {
    return packRules?.value_sets?.[name] ?? [];
  }, [packRules]);

  const incidentTypeValues = valueSet('INCIDENT_TYPE');
  const propertyUseValues = valueSet('PROPERTY_USE');
  const actionTakenValues = valueSet('ACTION_TAKEN');

  // Build payload
  function buildPayload() {
    return {
      incident_number: form.incident_number,
      start_datetime: form.start_datetime || undefined,
      end_datetime: form.end_datetime || undefined,
      incident_type_code: form.incident_type_code || undefined,
      address: { street: form.street, city: form.city, state: form.state, zip: form.zip },
      property_use_code: form.property_use_code || undefined,
      on_site_materials: form.on_site_materials || undefined,
      units: form.units.filter((u) => u.apparatus_id),
      actions: form.actions.filter((a) => a.action_code),
      civilian_injuries: Number(form.civilian_injuries) || 0,
      civilian_fatalities: Number(form.civilian_fatalities) || 0,
      firefighter_injuries: Number(form.firefighter_injuries) || 0,
      firefighter_fatalities: Number(form.firefighter_fatalities) || 0,
      property_loss_estimate: form.property_loss_estimate ? Number(form.property_loss_estimate) : undefined,
      contents_loss_estimate: form.contents_loss_estimate ? Number(form.contents_loss_estimate) : undefined,
    };
  }

  async function saveDraft() {
    setSavingDraft(true);
    try {
      const payload = buildPayload();
      let res: Response;
      if (currentId) {
        res = await fetch(`${API}/api/v1/incidents/fire/${currentId}`, {
          method: 'PATCH',
          headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        res = await fetch(`${API}/api/v1/incidents/fire`, {
          method: 'POST',
          headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? `HTTP ${res.status}`);
      if (!currentId) setCurrentId(json.id ?? json.incident_id);
      pushToast('Draft saved', 'success');
      onSaved(json);
    } catch (e: unknown) {
      pushToast(e instanceof Error ? e.message : 'Save failed', 'error');
    } finally {
      setSavingDraft(false);
    }
  }

  async function validate() {
    if (!currentId) {
      pushToast('Save draft first', 'error');
      return;
    }
    setValidating(true);
    try {
      const res = await fetch(`${API}/api/v1/incidents/fire/${currentId}/validate`, {
        method: 'POST',
        headers: { Authorization: getToken() },
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? `HTTP ${res.status}`);
      setValidationResult(json);
      if (json.valid) pushToast('Validation passed', 'success');
      else pushToast(`${json.issues?.filter((i: ValidationIssue) => i.severity === 'error').length ?? 0} errors found`, 'error');
    } catch (e: unknown) {
      pushToast(e instanceof Error ? e.message : 'Validation failed', 'error');
    } finally {
      setValidating(false);
    }
  }

  async function doExport() {
    if (!currentId) return;
    setExportingId(currentId);
    try {
      const res = await fetch(`${API}/api/v1/incidents/fire/${currentId}/export`, {
        headers: { Authorization: getToken() },
      });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `incident-${form.incident_number || currentId}.json`;
      a.click();
      URL.revokeObjectURL(url);
      pushToast('Export downloaded', 'success');
    } catch {
      pushToast('Export failed', 'error');
    } finally {
      setExportingId(null);
    }
  }

  const incidentStatus = (selectedIncident?.status ?? 'draft') as IncidentStatus;

  // Section error counts
  const sectionErrors = (sectionId: string) => issuesForSection(sectionId).filter((i) => i.severity === 'error').length;
  const totalErrors = validationResult?.issues.filter((i) => i.severity === 'error').length ?? 0;

  function getInputClass(path: string) {
    return fieldError(path) ? inputErrorClass : inputClass;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Form header */}
      <div className="px-5 py-3 border-b border-[rgba(255,255,255,0.08)] flex items-center justify-between flex-shrink-0">
        <div>
          <p className="text-[9px] uppercase tracking-[0.18em] text-[rgba(255,107,26,0.6)]">{currentId ? 'Edit Incident' : 'New Incident'}</p>
          <h3 className="text-sm font-bold text-white">
            {form.incident_number || (currentId ? 'Incident' : 'New Fire Incident')}
          </h3>
        </div>
        {validationResult && (
          <div className="flex items-center gap-2">
            <span
              className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-sm"
              style={validationResult.valid
                ? { color: '#4caf50', background: 'rgba(76,175,80,0.15)', border: '1px solid rgba(76,175,80,0.3)' }
                : { color: '#e53935', background: 'rgba(229,57,53,0.12)', border: '1px solid rgba(229,57,53,0.25)' }}
            >
              {validationResult.valid ? 'VALID' : `${totalErrors} ERROR${totalErrors !== 1 ? 'S' : ''}`}
            </span>
          </div>
        )}
      </div>

      {/* Scrollable form body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">

        {/* ── Section: Incident Basics ── */}
        <FormSection id="incident_basics" label="Incident Basics" errorCount={sectionErrors('incident_basics')}>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Incident Number" required error={fieldError('incident_number')}>
              <input
                type="text"
                value={form.incident_number}
                onChange={(e) => update('incident_number', e.target.value)}
                className={getInputClass('incident_number')}
                placeholder="2025-001"
              />
            </FormField>
            <FormField label="Incident Type" required error={fieldError('incident_type_code')}>
              <select
                value={form.incident_type_code}
                onChange={(e) => update('incident_type_code', e.target.value)}
                className={getInputClass('incident_type_code')}
                style={{ background: '#0b0f14' }}
              >
                <option value="" className="bg-[#0b0f14]">— Select —</option>
                {(incidentTypeValues.length > 0
                  ? incidentTypeValues
                  : ['STRUCTURE_FIRE', 'VEHICLE_FIRE', 'OUTSIDE_RUBBISH_FIRE', 'WILDLAND_FIRE', 'EMS_CALL', 'VEHICLE_ACCIDENT', 'HAZMAT', 'RESCUE', 'PUBLIC_ASSIST', 'FALSE_ALARM', 'GOOD_INTENT', 'SERVICE_CALL']
                ).map((v) => (
                  <option key={v} value={v} className="bg-[#0b0f14]">{v.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <FormField label="Start Date/Time" required error={fieldError('start_datetime')}>
              <input
                type="datetime-local"
                value={form.start_datetime}
                onChange={(e) => update('start_datetime', e.target.value)}
                className={getInputClass('start_datetime')}
              />
            </FormField>
            <FormField label="End Date/Time" error={fieldError('end_datetime')}>
              <input
                type="datetime-local"
                value={form.end_datetime}
                onChange={(e) => update('end_datetime', e.target.value)}
                className={getInputClass('end_datetime')}
              />
            </FormField>
          </div>
          <div className="mt-3">
            <FormField label="Street Address" error={fieldError('address.street')}>
              <input
                type="text"
                value={form.street}
                onChange={(e) => update('street', e.target.value)}
                className={getInputClass('address.street')}
                placeholder="123 Main St"
              />
            </FormField>
          </div>
          <div className="grid grid-cols-3 gap-2 mt-3">
            <FormField label="City" error={fieldError('address.city')}>
              <input type="text" value={form.city} onChange={(e) => update('city', e.target.value)} className={getInputClass('address.city')} placeholder="Madison" />
            </FormField>
            <FormField label="State" error={fieldError('address.state')}>
              <input type="text" value={form.state} onChange={(e) => update('state', e.target.value)} className={getInputClass('address.state')} placeholder="WI" maxLength={2} />
            </FormField>
            <FormField label="ZIP" error={fieldError('address.zip')}>
              <input type="text" value={form.zip} onChange={(e) => update('zip', e.target.value)} className={getInputClass('address.zip')} placeholder="53703" />
            </FormField>
          </div>
        </FormSection>

        {/* ── Section: Property Information ── */}
        <FormSection id="property_information" label="Property Information" errorCount={sectionErrors('property_information')}>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Property Use Code" error={fieldError('property_use_code')}>
              <select
                value={form.property_use_code}
                onChange={(e) => update('property_use_code', e.target.value)}
                className={getInputClass('property_use_code')}
                style={{ background: '#0b0f14' }}
              >
                <option value="" className="bg-[#0b0f14]">— Select —</option>
                {(propertyUseValues.length > 0
                  ? propertyUseValues
                  : ['RESIDENTIAL_1_2', 'RESIDENTIAL_MULTI', 'COMMERCIAL', 'INDUSTRIAL', 'PUBLIC', 'VACANT', 'OPEN_LAND']
                ).map((v) => (
                  <option key={v} value={v} className="bg-[#0b0f14]">{v.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </FormField>
            <FormField label="On-Site Materials" error={fieldError('on_site_materials')}>
              <input
                type="text"
                value={form.on_site_materials}
                onChange={(e) => update('on_site_materials', e.target.value)}
                className={getInputClass('on_site_materials')}
                placeholder="Describe hazardous materials if any"
              />
            </FormField>
          </div>
        </FormSection>

        {/* ── Section: Units & Personnel ── */}
        <FormSection id="units_personnel" label="Units & Personnel" errorCount={sectionErrors('units_personnel')}>
          <div className="space-y-3">
            {form.units.map((unit, i) => (
              <div key={i} className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-sm p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] uppercase tracking-wider text-[rgba(255,107,26,0.7)]">Unit {i + 1}</span>
                  {form.units.length > 1 && (
                    <button
                      onClick={() => update('units', form.units.filter((_, idx) => idx !== i))}
                      className="text-[10px] text-[rgba(229,57,53,0.6)] hover:text-[#e53935]"
                    >
                      Remove
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <FormField label="Apparatus" required>
                    <select
                      value={unit.apparatus_id}
                      onChange={(e) => {
                        const updated = [...form.units];
                        updated[i] = { ...unit, apparatus_id: e.target.value };
                        update('units', updated);
                      }}
                      className={inputClass}
                      style={{ background: '#0b0f14' }}
                    >
                      <option value="" className="bg-[#0b0f14]">— Select —</option>
                      {apparatus.map((a) => (
                        <option key={a.id} value={a.id} className="bg-[#0b0f14]">{a.unit_id} ({a.unit_type_code})</option>
                      ))}
                    </select>
                  </FormField>
                  <FormField label="Arrival Time">
                    <input
                      type="datetime-local"
                      value={unit.arrival_time}
                      onChange={(e) => {
                        const updated = [...form.units];
                        updated[i] = { ...unit, arrival_time: e.target.value };
                        update('units', updated);
                      }}
                      className={inputClass}
                    />
                  </FormField>
                  <FormField label="Departure Time">
                    <input
                      type="datetime-local"
                      value={unit.departure_time}
                      onChange={(e) => {
                        const updated = [...form.units];
                        updated[i] = { ...unit, departure_time: e.target.value };
                        update('units', updated);
                      }}
                      className={inputClass}
                    />
                  </FormField>
                </div>
              </div>
            ))}
          </div>
          <button
            onClick={() => update('units', [...form.units, { apparatus_id: '', arrival_time: '', departure_time: '' }])}
            className="mt-3 h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
            style={{ background: 'rgba(34,211,238,0.08)', border: '1px solid rgba(34,211,238,0.2)', color: '#22d3ee' }}
          >
            + Add Unit
          </button>
        </FormSection>

        {/* ── Section: Actions Taken ── */}
        <FormSection id="actions_taken" label="Actions Taken" errorCount={sectionErrors('actions_taken')}>
          <div className="space-y-3">
            {form.actions.map((action, i) => (
              <div key={i} className="flex items-end gap-3">
                <div className="flex-1">
                  <FormField label="Action Code" required>
                    <select
                      value={action.action_code}
                      onChange={(e) => {
                        const updated = [...form.actions];
                        updated[i] = { ...action, action_code: e.target.value };
                        update('actions', updated);
                      }}
                      className={inputClass}
                      style={{ background: '#0b0f14' }}
                    >
                      <option value="" className="bg-[#0b0f14]">— Select —</option>
                      {(actionTakenValues.length > 0
                        ? actionTakenValues
                        : ['FIRE_CONTROL', 'VENTILATION', 'SALVAGE', 'OVERHAUL', 'WATER_SUPPLY', 'SEARCH', 'RESCUE', 'EMS_CARE', 'HAZMAT_MITIGATION', 'INVESTIGATION']
                      ).map((v) => (
                        <option key={v} value={v} className="bg-[#0b0f14]">{v.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  </FormField>
                </div>
                <div className="flex-1">
                  <FormField label="Action Date/Time">
                    <input
                      type="datetime-local"
                      value={action.action_datetime}
                      onChange={(e) => {
                        const updated = [...form.actions];
                        updated[i] = { ...action, action_datetime: e.target.value };
                        update('actions', updated);
                      }}
                      className={inputClass}
                    />
                  </FormField>
                </div>
                {form.actions.length > 1 && (
                  <button
                    onClick={() => update('actions', form.actions.filter((_, idx) => idx !== i))}
                    className="h-9 px-2 text-[10px] text-[rgba(229,57,53,0.6)] hover:text-[#e53935] mb-0.5"
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
          <button
            onClick={() => update('actions', [...form.actions, { action_code: '', action_datetime: '' }])}
            className="mt-3 h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
            style={{ background: 'rgba(34,211,238,0.08)', border: '1px solid rgba(34,211,238,0.2)', color: '#22d3ee' }}
          >
            + Add Action
          </button>
        </FormSection>

        {/* ── Section: Outcomes ── */}
        <FormSection id="outcomes" label="Outcomes" errorCount={sectionErrors('outcomes')}>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Civilian Injuries" error={fieldError('civilian_injuries')}>
              <input type="number" min={0} value={form.civilian_injuries} onChange={(e) => update('civilian_injuries', e.target.value)} className={getInputClass('civilian_injuries')} />
            </FormField>
            <FormField label="Civilian Fatalities" error={fieldError('civilian_fatalities')}>
              <input type="number" min={0} value={form.civilian_fatalities} onChange={(e) => update('civilian_fatalities', e.target.value)} className={getInputClass('civilian_fatalities')} />
            </FormField>
            <FormField label="Firefighter Injuries" error={fieldError('firefighter_injuries')}>
              <input type="number" min={0} value={form.firefighter_injuries} onChange={(e) => update('firefighter_injuries', e.target.value)} className={getInputClass('firefighter_injuries')} />
            </FormField>
            <FormField label="Firefighter Fatalities" error={fieldError('firefighter_fatalities')}>
              <input type="number" min={0} value={form.firefighter_fatalities} onChange={(e) => update('firefighter_fatalities', e.target.value)} className={getInputClass('firefighter_fatalities')} />
            </FormField>
            <FormField label="Property Loss Estimate ($)" error={fieldError('property_loss_estimate')}>
              <input type="number" min={0} value={form.property_loss_estimate} onChange={(e) => update('property_loss_estimate', e.target.value)} className={getInputClass('property_loss_estimate')} placeholder="0" />
            </FormField>
            <FormField label="Contents Loss Estimate ($)" error={fieldError('contents_loss_estimate')}>
              <input type="number" min={0} value={form.contents_loss_estimate} onChange={(e) => update('contents_loss_estimate', e.target.value)} className={getInputClass('contents_loss_estimate')} placeholder="0" />
            </FormField>
          </div>
        </FormSection>

      </div>

      {/* ── Action Bar ── */}
      <div
        className="flex-shrink-0 px-5 py-3 border-t border-[rgba(255,255,255,0.08)] flex items-center gap-3 flex-wrap"
        style={{ background: '#0b0f14' }}
      >
        <button
          onClick={saveDraft}
          disabled={savingDraft}
          className="h-9 px-5 text-[11px] font-bold uppercase tracking-wider rounded-sm transition-all hover:brightness-110 disabled:opacity-40"
          style={{ background: 'rgba(255,107,26,0.18)', border: '1px solid rgba(255,107,26,0.35)', color: '#ff6b1a' }}
        >
          {savingDraft ? 'Saving…' : 'Save Draft'}
        </button>
        <button
          onClick={validate}
          disabled={validating || !currentId}
          className="h-9 px-5 text-[11px] font-bold uppercase tracking-wider rounded-sm transition-all hover:brightness-110 disabled:opacity-40"
          style={{ background: 'rgba(34,211,238,0.12)', border: '1px solid rgba(34,211,238,0.3)', color: '#22d3ee' }}
        >
          {validating ? 'Validating…' : 'Validate'}
        </button>
        <button
          onClick={doExport}
          disabled={incidentStatus !== 'validated' || exportingId !== null}
          title={incidentStatus !== 'validated' ? 'Validate incident before exporting' : undefined}
          className="h-9 px-5 text-[11px] font-bold uppercase tracking-wider rounded-sm transition-all hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ background: 'rgba(76,175,80,0.12)', border: '1px solid rgba(76,175,80,0.3)', color: '#4caf50' }}
        >
          {exportingId ? 'Exporting…' : 'Export'}
          {incidentStatus !== 'validated' && (
            <span className="ml-1 text-[9px] opacity-60">🔒</span>
          )}
        </button>
        {validationResult && !validationResult.valid && (
          <span className="text-[10px] text-[rgba(229,57,53,0.8)]">
            {totalErrors} error{totalErrors !== 1 ? 's' : ''} — see highlighted sections
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function FireIncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [packRules, setPackRules] = useState<PackRules | null>(null);
  const [apparatus, setApparatus] = useState<ApparatusOption[]>([]);
  const { toasts, push: pushToast } = useToast();

  // Fetch pack rules
  useEffect(() => {
    fetch(`${API}/api/v1/incidents/fire/pack-rules`, {
      headers: { Authorization: getToken() },
    })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => d && setPackRules(d))
      .catch(() => {});
  }, []);

  // Fetch apparatus
  useEffect(() => {
    fetch(`${API}/api/v1/incidents/fire/apparatus`, {
      headers: { Authorization: getToken() },
    })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => d && setApparatus(Array.isArray(d) ? d : d.apparatus ?? []))
      .catch(() => {});
  }, []);

  // Fetch incidents
  const fetchIncidents = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.set('status', statusFilter);
      const res = await fetch(`${API}/api/v1/incidents/fire?${params.toString()}`, {
        headers: { Authorization: getToken() },
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setIncidents(Array.isArray(data) ? data : data.incidents ?? []);
    } catch {
      pushToast('Failed to load incidents', 'error');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, pushToast]);

  useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  function handleSelect(inc: Incident) {
    setSelectedIncident(inc);
    setIsNew(false);
  }

  function handleNew() {
    setSelectedIncident(null);
    setIsNew(true);
  }

  function handleSaved(inc: Incident) {
    fetchIncidents();
    setSelectedIncident(inc);
    setIsNew(false);
  }

  const showForm = isNew || selectedIncident !== null;

  return (
    <div className="min-h-screen bg-[#07090d] text-white flex flex-col" style={{ height: '100vh' }}>
      <Toast items={toasts} />
      <div className="flex flex-1 min-h-0">
        <IncidentList
          incidents={incidents}
          loading={loading}
          selectedId={selectedIncident?.id ?? null}
          statusFilter={statusFilter}
          onSelect={handleSelect}
          onNew={handleNew}
          onFilterChange={setStatusFilter}
        />
        <div className="flex-1 flex flex-col min-h-0">
          {showForm ? (
            <IncidentForm
              selectedIncident={selectedIncident}
              packRules={packRules}
              apparatus={apparatus}
              onSaved={handleSaved}
              pushToast={pushToast}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-3">
                <div className="text-4xl opacity-20">🔥</div>
                <p className="text-sm text-[rgba(255,255,255,0.3)]">Select an incident or create a new one.</p>
                <button
                  onClick={handleNew}
                  className="h-8 px-4 text-[10px] font-bold uppercase tracking-wider rounded-sm"
                  style={{ background: 'rgba(255,107,26,0.18)', border: '1px solid rgba(255,107,26,0.35)', color: '#ff6b1a' }}
                >
                  + New Incident
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
