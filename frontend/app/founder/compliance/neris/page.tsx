'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return 'Bearer ' + (localStorage.getItem('qs_token') || '');
}

// ─── Types ────────────────────────────────────────────────────────────────────

type PackStatus = 'importing' | 'staged' | 'compiled' | 'active' | 'archived' | 'import_failed';

interface NerisPack {
  id: string;
  name: string;
  source_type: string;
  source_uri?: string;
  source_ref?: string;
  sha256?: string;
  file_count?: number;
  status: PackStatus;
  created_at: string;
  compiled?: boolean;
  data?: { rules_json?: RulesJson; [key: string]: unknown };
}

interface RulesJson {
  entity_rules?: RuleSection[];
  incident_rules?: RuleSection[];
}

interface RuleSection {
  id: string;
  label: string;
  fields: RuleField[];
}

interface RuleField {
  path: string;
  type?: string;
  required?: boolean;
  value_set?: string[];
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

interface CopilotResult {
  summary?: string;
  actions?: { type: string; instruction: string }[];
  confidence?: number;
}

type TabKey = 'packs' | 'validate' | 'fixlist' | 'rules';

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

const PACK_STATUS_MAP: Record<PackStatus, { label: string; color: string; bg: string; pulse?: boolean }> = {
  importing:     { label: 'IMPORTING',  color: '#f59e0b', bg: 'rgba(245,158,11,0.12)',  pulse: true },
  staged:        { label: 'STAGED',     color: '#22d3ee', bg: 'rgba(34,211,238,0.12)' },
  compiled:      { label: 'COMPILED',   color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
  active:        { label: 'ACTIVE',     color: '#4caf50', bg: 'rgba(76,175,80,0.12)' },
  archived:      { label: 'ARCHIVED',   color: 'rgba(255,255,255,0.35)', bg: 'rgba(255,255,255,0.06)' },
  import_failed: { label: 'FAILED',     color: '#e53935', bg: 'rgba(229,57,53,0.12)' },
};

function PackStatusBadge({ status }: { status: PackStatus }) {
  const s = PACK_STATUS_MAP[status] ?? PACK_STATUS_MAP.staged;
  return (
    <span
      className={`px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-sm whitespace-nowrap${s.pulse ? ' animate-pulse' : ''}`}
      style={{ color: s.color, background: s.bg }}
    >
      {s.label}
    </span>
  );
}

// ─── Import Modal ─────────────────────────────────────────────────────────────

function ImportModal({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const [name, setName] = useState('');
  const [repo, setRepo] = useState('ulfsri/neris-framework');
  const [ref, setRef] = useState('main');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError('Pack name is required'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/v1/founder/neris/packs/import`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_type: 'github', repo, ref, name }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? `HTTP ${res.status}`);
      onImported();
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Import failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.65)' }}
      onClick={onClose}
    >
      <div
        className="bg-[#0b0f14] border border-[rgba(255,255,255,0.12)] rounded-sm p-6 w-full max-w-md shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-white">Import from GitHub</h3>
          <button onClick={onClose} className="text-[rgba(255,255,255,0.4)] hover:text-white text-lg leading-none">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          {[
            { label: 'Pack Name', value: name, onChange: setName, placeholder: 'e.g. WI NERIS 2025-Q1' },
            { label: 'Repository', value: repo, onChange: setRepo, placeholder: 'owner/repo' },
            { label: 'Ref (branch/tag)', value: ref, onChange: setRef, placeholder: 'main' },
          ].map((f) => (
            <div key={f.label}>
              <label className="block text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.4)] mb-1">{f.label}</label>
              <input
                type="text"
                value={f.value}
                onChange={(e) => f.onChange(e.target.value)}
                placeholder={f.placeholder}
                className="w-full bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[rgba(255,107,26,0.4)] placeholder:text-[rgba(255,255,255,0.2)]"
              />
            </div>
          ))}
          {error && (
            <div className="p-2 text-xs text-[#e53935] bg-[rgba(229,57,53,0.08)] border border-[rgba(229,57,53,0.25)] rounded-sm">
              {error}
            </div>
          )}
          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2 text-xs font-semibold uppercase tracking-wider rounded-sm transition-all hover:brightness-110 disabled:opacity-40"
              style={{ background: 'rgba(255,107,26,0.18)', border: '1px solid rgba(255,107,26,0.35)', color: '#ff6b1a' }}
            >
              {loading ? 'Importing…' : 'Start Import'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-sm"
              style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.5)' }}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Pack Detail Drawer ───────────────────────────────────────────────────────

function PackDetailDrawer({
  pack,
  onClose,
  onAction,
}: {
  pack: NerisPack;
  onClose: () => void;
  onAction: (type: 'compile' | 'activate', id: string) => void;
}) {
  return (
    <div
      className="fixed inset-0 z-40 flex justify-end"
      style={{ background: 'rgba(0,0,0,0.4)' }}
      onClick={onClose}
    >
      <div
        className="bg-[#0b0f14] border-l border-[rgba(255,255,255,0.1)] h-full overflow-y-auto flex flex-col"
        style={{ width: 400 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4 border-b border-[rgba(255,255,255,0.08)] flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">Pack Detail</h2>
            <p className="text-[10px] text-[rgba(255,255,255,0.38)] mt-0.5">{pack.name}</p>
          </div>
          <button onClick={onClose} className="text-[rgba(255,255,255,0.4)] hover:text-white transition-colors text-lg leading-none">✕</button>
        </div>
        <div className="flex-1 px-5 py-4 space-y-5">
          <div>
            <p className="text-[9px] uppercase tracking-[0.18em] text-[rgba(255,107,26,0.6)] mb-3">Pack Data</p>
            <div className="space-y-2.5">
              {[
                { label: 'Name', value: pack.name },
                { label: 'Source URI', value: pack.source_uri ?? '—' },
                { label: 'Ref', value: pack.source_ref ?? '—' },
                { label: 'SHA256', value: pack.sha256 ? pack.sha256.slice(0, 24) + '…' : '—' },
                { label: 'File Count', value: String(pack.file_count ?? '—') },
                { label: 'Created', value: new Date(pack.created_at).toLocaleString() },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-start justify-between gap-3">
                  <span className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] flex-shrink-0 mt-0.5">{label}</span>
                  <span className="text-xs text-[rgba(255,255,255,0.8)] text-right font-mono break-all">{value}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between py-3 border-y border-[rgba(255,255,255,0.06)]">
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)]">Status</span>
              <PackStatusBadge status={pack.status} />
            </div>
            {pack.compiled && (
              <div className="flex flex-col gap-1.5 items-end">
                <span className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)]">Compiled</span>
                <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-sm" style={{ color: '#4caf50', background: 'rgba(76,175,80,0.12)' }}>YES</span>
              </div>
            )}
          </div>
          {pack.compiled && (
            <div className="flex gap-2">
              <div className="flex flex-col items-center px-3 py-2 rounded-sm" style={{ background: 'rgba(34,211,238,0.08)', border: '1px solid rgba(34,211,238,0.2)' }}>
                <span className="text-[9px] uppercase tracking-wider text-[rgba(255,255,255,0.4)]">Entity Rules</span>
                <span className="text-base font-bold text-[#22d3ee]">{(pack.data as any)?.rules_json?.entity_rules?.length ?? '—'}</span>
              </div>
              <div className="flex flex-col items-center px-3 py-2 rounded-sm" style={{ background: 'rgba(168,85,247,0.08)', border: '1px solid rgba(168,85,247,0.2)' }}>
                <span className="text-[9px] uppercase tracking-wider text-[rgba(255,255,255,0.4)]">Incident Rules</span>
                <span className="text-base font-bold text-[#a855f7]">{(pack.data as any)?.rules_json?.incident_rules?.length ?? '—'}</span>
              </div>
            </div>
          )}
          <div>
            <p className="text-[9px] uppercase tracking-[0.18em] text-[rgba(255,107,26,0.6)] mb-3">Actions</p>
            <div className="flex flex-wrap gap-2">
              {pack.status === 'staged' && (
                <button
                  onClick={() => onAction('compile', pack.id)}
                  className="h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
                  style={{ background: 'rgba(96,165,250,0.12)', border: '1px solid rgba(96,165,250,0.3)', color: '#60a5fa' }}
                >
                  Compile
                </button>
              )}
              {(pack.status === 'staged' || pack.status === 'compiled') && (
                <button
                  onClick={() => onAction('activate', pack.id)}
                  className="h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
                  style={{ background: 'rgba(76,175,80,0.12)', border: '1px solid rgba(76,175,80,0.3)', color: '#4caf50' }}
                >
                  Activate
                </button>
              )}
              {pack.status === 'active' && (
                <span className="h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm flex items-center" style={{ color: '#4caf50', background: 'rgba(76,175,80,0.08)', border: '1px solid rgba(76,175,80,0.2)' }}>
                  Currently Active
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Packs Tab ────────────────────────────────────────────────────────────────

function PacksTab({
  packs,
  loading,
  lastRefreshed,
  onRefresh,
  onImport,
  activePackId,
}: {
  packs: NerisPack[];
  loading: boolean;
  lastRefreshed: Date | null;
  onRefresh: () => void;
  onImport: () => void;
  activePackId: string | null;
}) {
  const [detailPack, setDetailPack] = useState<NerisPack | null>(null);
  const { toasts, push: pushToast } = useToast();

  async function doCompile(id: string) {
    try {
      const res = await fetch(`${API}/api/v1/founder/neris/packs/${id}/compile`, {
        method: 'POST',
        headers: { Authorization: getToken() },
      });
      if (!res.ok) throw new Error();
      pushToast('Compile initiated', 'success');
      onRefresh();
    } catch {
      pushToast('Compile failed', 'error');
    }
  }

  async function doActivate(id: string) {
    try {
      const res = await fetch(`${API}/api/v1/founder/neris/packs/${id}/activate`, {
        method: 'POST',
        headers: { Authorization: getToken() },
      });
      if (!res.ok) throw new Error();
      pushToast('Pack activated', 'success');
      onRefresh();
    } catch {
      pushToast('Activation failed', 'error');
    }
  }

  function handleAction(type: 'compile' | 'activate', id: string) {
    if (type === 'compile') doCompile(id);
    else doActivate(id);
    setDetailPack(null);
  }

  return (
    <div className="space-y-4">
      <Toast items={toasts} />
      {detailPack && (
        <PackDetailDrawer
          pack={detailPack}
          onClose={() => setDetailPack(null)}
          onAction={handleAction}
        />
      )}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onImport}
            className="h-8 px-4 text-[10px] font-bold uppercase tracking-wider rounded-sm transition-all hover:brightness-110"
            style={{ background: 'rgba(255,107,26,0.18)', border: '1px solid rgba(255,107,26,0.35)', color: '#ff6b1a' }}
          >
            Import from GitHub
          </button>
          <button
            onClick={onRefresh}
            className="h-8 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)' }}
          >
            Refresh
          </button>
        </div>
        {lastRefreshed && (
          <span className="text-[10px] text-[rgba(255,255,255,0.3)] font-mono">
            Last refreshed: {lastRefreshed.toLocaleTimeString()}
          </span>
        )}
      </div>
      <div className="bg-[#0b0f14] border border-[rgba(255,255,255,0.08)] rounded-sm overflow-x-auto">
        <table className="w-full text-xs min-w-[780px]">
          <thead>
            <tr className="border-b border-[rgba(255,255,255,0.07)]">
              {['Name', 'Source Type', 'Status', 'Created At', 'SHA256', 'Actions'].map((h) => (
                <th key={h} className="text-left py-2.5 px-3 text-[9px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] font-semibold whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="py-10 text-center text-[11px] text-[rgba(255,255,255,0.3)]">Loading…</td>
              </tr>
            )}
            {!loading && packs.length === 0 && (
              <tr>
                <td colSpan={6} className="py-10 text-center text-[11px] text-[rgba(255,255,255,0.3)]">No packs found. Import a pack to get started.</td>
              </tr>
            )}
            {!loading && packs.map((pack) => (
              <tr
                key={pack.id}
                className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)] transition-colors"
                style={pack.id === activePackId ? { background: 'rgba(76,175,80,0.04)' } : undefined}
              >
                <td className="py-2.5 px-3 font-medium text-[rgba(255,255,255,0.85)] whitespace-nowrap">
                  {pack.name}
                  {pack.id === activePackId && (
                    <span className="ml-2 text-[9px] text-[#4caf50] uppercase tracking-wider">● active</span>
                  )}
                </td>
                <td className="py-2.5 px-3 text-[rgba(255,255,255,0.5)] uppercase">{pack.source_type}</td>
                <td className="py-2.5 px-3"><PackStatusBadge status={pack.status} /></td>
                <td className="py-2.5 px-3 font-mono text-[rgba(255,255,255,0.38)] whitespace-nowrap">
                  {new Date(pack.created_at).toLocaleDateString()}
                </td>
                <td className="py-2.5 px-3 font-mono text-[rgba(255,255,255,0.4)] text-[10px]">
                  {pack.sha256 ? pack.sha256.slice(0, 12) : '—'}
                </td>
                <td className="py-2.5 px-3">
                  <div className="flex items-center gap-1.5">
                    {pack.status === 'staged' && (
                      <button
                        onClick={() => doCompile(pack.id)}
                        className="h-6 px-2 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
                        style={{ background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.25)', color: '#60a5fa' }}
                      >
                        Compile
                      </button>
                    )}
                    {(pack.status === 'staged' || pack.status === 'compiled') && (
                      <button
                        onClick={() => doActivate(pack.id)}
                        className="h-6 px-2 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
                        style={{ background: 'rgba(76,175,80,0.1)', border: '1px solid rgba(76,175,80,0.25)', color: '#4caf50' }}
                      >
                        Activate
                      </button>
                    )}
                    <button
                      onClick={() => setDetailPack(pack)}
                      className="h-6 px-2 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
                      style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.6)' }}
                    >
                      Details
                    </button>
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

// ─── Copilot Result ───────────────────────────────────────────────────────────

function CopilotResult({ result }: { result: CopilotResult }) {
  return (
    <div className="mt-4 p-4 rounded-sm space-y-3" style={{ background: 'rgba(168,85,247,0.07)', border: '1px solid rgba(168,85,247,0.2)' }}>
      <p className="text-[9px] uppercase tracking-[0.18em] text-[#a855f7]">Copilot Analysis</p>
      {result.summary && (
        <p className="text-xs text-[rgba(255,255,255,0.75)] leading-relaxed">{result.summary}</p>
      )}
      {result.actions && result.actions.length > 0 && (
        <div className="space-y-2">
          {result.actions.map((item, i) => (
            <div key={i} className="flex gap-2 items-start">
              <span
                className="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded-sm shrink-0 mt-0.5"
                style={{ background: 'rgba(255,107,26,0.15)', color: '#ff6b1a', border: '1px solid rgba(255,107,26,0.3)' }}
              >
                {item.type}
              </span>
              <span className="text-xs text-[rgba(255,255,255,0.7)]">{item.instruction}</span>
            </div>
          ))}
        </div>
      )}
      {result.confidence !== undefined && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[9px] uppercase tracking-wider text-[rgba(255,255,255,0.4)]">Confidence</span>
            <span className="text-[10px] font-mono text-[rgba(255,255,255,0.6)]">{Math.round(result.confidence * 100)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-[rgba(255,255,255,0.08)]">
            <div
              className="h-full rounded-full"
              style={{ width: `${result.confidence * 100}%`, background: '#a855f7' }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Issue Card ───────────────────────────────────────────────────────────────

function IssueCard({ issue }: { issue: ValidationIssue }) {
  return (
    <div
      className="p-3 rounded-sm"
      style={{
        background: issue.severity === 'error' ? 'rgba(229,57,53,0.06)' : 'rgba(255,152,0,0.06)',
        border: `1px solid ${issue.severity === 'error' ? 'rgba(229,57,53,0.2)' : 'rgba(255,152,0,0.2)'}`,
      }}
    >
      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
        <span
          className="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded-sm"
          style={{
            color: issue.severity === 'error' ? '#e53935' : '#ff9800',
            background: issue.severity === 'error' ? 'rgba(229,57,53,0.15)' : 'rgba(255,152,0,0.15)',
          }}
        >
          {issue.severity}
        </span>
        {issue.field_label && (
          <span className="text-xs font-semibold text-[rgba(255,255,255,0.8)]">{issue.field_label}</span>
        )}
        {issue.path && (
          <span className="text-[10px] font-mono text-[rgba(255,255,255,0.45)]">{issue.path}</span>
        )}
        {issue.ui_section && (
          <span
            className="px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider rounded-sm"
            style={{ background: 'rgba(34,211,238,0.1)', color: '#22d3ee', border: '1px solid rgba(34,211,238,0.2)' }}
          >
            {issue.ui_section}
          </span>
        )}
      </div>
      <p className="text-xs text-[rgba(255,255,255,0.7)] mb-1">{issue.message}</p>
      {issue.suggested_fix && (
        <p className="text-[11px] text-[rgba(255,255,255,0.38)]">{issue.suggested_fix}</p>
      )}
    </div>
  );
}

// ─── Validate Tab ─────────────────────────────────────────────────────────────

function ValidateTab({
  activePackId,
  onIssuesPersist,
}: {
  activePackId: string | null;
  onIssuesPersist: (issues: ValidationIssue[]) => void;
}) {
  const [entityJson, setEntityJson] = useState('');
  const [incidentJson, setIncidentJson] = useState('');
  const [entityType, setEntityType] = useState<'ENTITY' | 'INCIDENT'>('INCIDENT');
  const [entityResult, setEntityResult] = useState<ValidationResult | null>(null);
  const [incidentResult, setIncidentResult] = useState<ValidationResult | null>(null);
  const [loadingEntity, setLoadingEntity] = useState(false);
  const [loadingIncident, setLoadingIncident] = useState(false);
  const [entityError, setEntityError] = useState('');
  const [incidentError, setIncidentError] = useState('');
  const [copilotResult, setCopilotResult] = useState<CopilotResult | null>(null);
  const [loadingCopilot, setLoadingCopilot] = useState(false);

  async function validateEntity() {
    if (!activePackId) { setEntityError('No active pack. Activate a pack first.'); return; }
    let payload: unknown;
    try { payload = JSON.parse(entityJson); } catch { setEntityError('Invalid JSON'); return; }
    setLoadingEntity(true);
    setEntityError('');
    setEntityResult(null);
    try {
      const res = await fetch(`${API}/api/v1/founder/neris/validate/bundle`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ pack_id: activePackId, entity_type: 'ENTITY', payload }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? `HTTP ${res.status}`);
      setEntityResult(json);
      if (json.issues?.length > 0) onIssuesPersist(json.issues);
    } catch (e: unknown) {
      setEntityError(e instanceof Error ? e.message : 'Validation failed');
    } finally {
      setLoadingEntity(false);
    }
  }

  async function validateIncident() {
    if (!activePackId) { setIncidentError('No active pack. Activate a pack first.'); return; }
    let payload: unknown;
    try { payload = JSON.parse(incidentJson); } catch { setIncidentError('Invalid JSON'); return; }
    setLoadingIncident(true);
    setIncidentError('');
    setIncidentResult(null);
    try {
      const res = await fetch(`${API}/api/v1/founder/neris/validate/bundle`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ pack_id: activePackId, entity_type: entityType, payload }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? `HTTP ${res.status}`);
      setIncidentResult(json);
      if (json.issues?.length > 0) onIssuesPersist(json.issues);
    } catch (e: unknown) {
      setIncidentError(e instanceof Error ? e.message : 'Validation failed');
    } finally {
      setLoadingIncident(false);
    }
  }

  async function explainWithCopilot(issues: ValidationIssue[]) {
    setLoadingCopilot(true);
    setCopilotResult(null);
    try {
      const res = await fetch(`${API}/api/v1/neris/copilot/explain`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ issues }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? `HTTP ${res.status}`);
      setCopilotResult(json);
    } catch {
      /* silently fail */
    } finally {
      setLoadingCopilot(false);
    }
  }

  const allIssues = [
    ...(entityResult?.issues ?? []),
    ...(incidentResult?.issues ?? []),
  ];

  const inputClass = "w-full bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] text-xs font-mono text-[rgba(255,255,255,0.75)] px-3 py-2 rounded-sm outline-none focus:border-[rgba(255,107,26,0.35)] placeholder:text-[rgba(255,255,255,0.2)] resize-y";

  return (
    <div className="space-y-5">
      {!activePackId && (
        <div className="p-3 rounded-sm text-xs" style={{ background: 'rgba(255,152,0,0.08)', border: '1px solid rgba(255,152,0,0.25)', color: '#ff9800' }}>
          No active NERIS pack. Go to the Packs tab to import and activate a pack.
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Entity panel */}
        <div className="bg-[#0b0f14] border border-[rgba(255,255,255,0.08)] rounded-sm p-4 space-y-3">
          <div>
            <p className="text-[10px] uppercase tracking-[0.18em] text-[rgba(255,107,26,0.6)] mb-0.5">Entity (Department)</p>
            <p className="text-[11px] text-[rgba(255,255,255,0.35)]">Paste entity JSON payload below</p>
          </div>
          <textarea
            value={entityJson}
            onChange={(e) => setEntityJson(e.target.value)}
            rows={10}
            placeholder='{"name": "Example Fire Dept", ...}'
            className={inputClass}
          />
          {entityError && (
            <p className="text-xs text-[#e53935]">{entityError}</p>
          )}
          <button
            onClick={validateEntity}
            disabled={loadingEntity || !entityJson.trim()}
            className="w-full py-2 text-[10px] font-bold uppercase tracking-wider rounded-sm transition-all hover:brightness-110 disabled:opacity-40"
            style={{ background: 'rgba(255,107,26,0.16)', border: '1px solid rgba(255,107,26,0.3)', color: '#ff6b1a' }}
          >
            {loadingEntity ? 'Validating…' : 'Validate Entity'}
          </button>
          {entityResult && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span
                  className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-sm"
                  style={entityResult.valid
                    ? { color: '#4caf50', background: 'rgba(76,175,80,0.15)', border: '1px solid rgba(76,175,80,0.3)' }
                    : { color: '#e53935', background: 'rgba(229,57,53,0.12)', border: '1px solid rgba(229,57,53,0.25)' }}
                >
                  {entityResult.valid ? 'VALID' : 'INVALID'}
                </span>
                <span className="text-[11px] text-[rgba(255,255,255,0.4)]">{entityResult.issues.length} issue{entityResult.issues.length !== 1 ? 's' : ''}</span>
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {entityResult.issues.map((issue, i) => <IssueCard key={i} issue={issue} />)}
              </div>
            </div>
          )}
        </div>
        {/* Incident panel */}
        <div className="bg-[#0b0f14] border border-[rgba(255,255,255,0.08)] rounded-sm p-4 space-y-3">
          <div>
            <p className="text-[10px] uppercase tracking-[0.18em] text-[rgba(255,107,26,0.6)] mb-0.5">Incident</p>
            <p className="text-[11px] text-[rgba(255,255,255,0.35)]">Paste incident JSON payload below</p>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.4)]">Entity Type</label>
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value as 'ENTITY' | 'INCIDENT')}
              className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-2 py-1 rounded-sm outline-none focus:border-[rgba(255,107,26,0.4)]"
              style={{ background: '#0b0f14' }}
            >
              <option value="ENTITY">ENTITY</option>
              <option value="INCIDENT">INCIDENT</option>
            </select>
          </div>
          <textarea
            value={incidentJson}
            onChange={(e) => setIncidentJson(e.target.value)}
            rows={10}
            placeholder='{"incident_number": "2025-001", ...}'
            className={inputClass}
          />
          {incidentError && (
            <p className="text-xs text-[#e53935]">{incidentError}</p>
          )}
          <button
            onClick={validateIncident}
            disabled={loadingIncident || !incidentJson.trim()}
            className="w-full py-2 text-[10px] font-bold uppercase tracking-wider rounded-sm transition-all hover:brightness-110 disabled:opacity-40"
            style={{ background: 'rgba(255,107,26,0.16)', border: '1px solid rgba(255,107,26,0.3)', color: '#ff6b1a' }}
          >
            {loadingIncident ? 'Validating…' : 'Validate'}
          </button>
          {incidentResult && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span
                  className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-sm"
                  style={incidentResult.valid
                    ? { color: '#4caf50', background: 'rgba(76,175,80,0.15)', border: '1px solid rgba(76,175,80,0.3)' }
                    : { color: '#e53935', background: 'rgba(229,57,53,0.12)', border: '1px solid rgba(229,57,53,0.25)' }}
                >
                  {incidentResult.valid ? 'VALID' : 'INVALID'}
                </span>
                <span className="text-[11px] text-[rgba(255,255,255,0.4)]">{incidentResult.issues.length} issue{incidentResult.issues.length !== 1 ? 's' : ''}</span>
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {incidentResult.issues.map((issue, i) => <IssueCard key={i} issue={issue} />)}
              </div>
            </div>
          )}
        </div>
      </div>
      {allIssues.length > 0 && (
        <div className="flex items-center gap-3">
          <button
            onClick={() => explainWithCopilot(allIssues)}
            disabled={loadingCopilot}
            className="h-8 px-4 text-[10px] font-bold uppercase tracking-wider rounded-sm transition-all hover:brightness-110 disabled:opacity-40"
            style={{ background: 'rgba(168,85,247,0.16)', border: '1px solid rgba(168,85,247,0.35)', color: '#a855f7' }}
          >
            {loadingCopilot ? 'Analyzing…' : 'Explain with Copilot'}
          </button>
        </div>
      )}
      {copilotResult && <CopilotResult result={copilotResult} />}
    </div>
  );
}

// ─── Fix List Tab ─────────────────────────────────────────────────────────────

function FixListTab({ issues }: { issues: ValidationIssue[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [copilotResult, setCopilotResult] = useState<CopilotResult | null>(null);
  const [loadingCopilot, setLoadingCopilot] = useState(false);

  const grouped: Record<string, ValidationIssue[]> = {};
  for (const issue of issues) {
    const sec = issue.ui_section ?? 'General';
    if (!grouped[sec]) grouped[sec] = [];
    grouped[sec].push(issue);
  }

  const errorCount = issues.filter((i) => i.severity === 'error').length;
  const warnCount = issues.filter((i) => i.severity === 'warning').length;

  function toggleSection(sec: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(sec)) next.delete(sec);
      else next.add(sec);
      return next;
    });
  }

  function copyAsJson() {
    navigator.clipboard.writeText(JSON.stringify(issues, null, 2));
  }

  async function explainAll() {
    setLoadingCopilot(true);
    setCopilotResult(null);
    try {
      const res = await fetch(`${API}/api/v1/neris/copilot/explain`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ issues }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error();
      setCopilotResult(json);
    } catch {
      /* silently fail */
    } finally {
      setLoadingCopilot(false);
    }
  }

  if (issues.length === 0) {
    return (
      <div className="py-16 text-center text-[rgba(255,255,255,0.3)] text-sm">
        No issues. Run a validation in the Validate tab to populate the fix list.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          {errorCount > 0 && (
            <span className="text-xs font-semibold" style={{ color: '#e53935' }}>{errorCount} error{errorCount !== 1 ? 's' : ''}</span>
          )}
          {warnCount > 0 && (
            <span className="text-xs font-semibold" style={{ color: '#ff9800' }}>{warnCount} warning{warnCount !== 1 ? 's' : ''}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={copyAsJson}
            className="h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
            style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.6)' }}
          >
            Copy Fix List as JSON
          </button>
          <button
            onClick={explainAll}
            disabled={loadingCopilot}
            className="h-7 px-3 text-[10px] font-bold uppercase tracking-wider rounded-sm disabled:opacity-40"
            style={{ background: 'rgba(168,85,247,0.14)', border: '1px solid rgba(168,85,247,0.3)', color: '#a855f7' }}
          >
            {loadingCopilot ? 'Analyzing…' : 'Explain All with Copilot'}
          </button>
        </div>
      </div>

      {Object.entries(grouped).map(([section, sectionIssues]) => {
        const isOpen = expanded.has(section);
        const secErrors = sectionIssues.filter((i) => i.severity === 'error').length;
        const secWarns = sectionIssues.filter((i) => i.severity === 'warning').length;
        return (
          <div key={section} className="bg-[#0b0f14] border border-[rgba(255,255,255,0.08)] rounded-sm overflow-hidden">
            <button
              onClick={() => toggleSection(section)}
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[rgba(255,255,255,0.02)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-[rgba(255,255,255,0.8)]">{section}</span>
                {secErrors > 0 && (
                  <span className="px-1.5 py-0.5 text-[9px] font-bold uppercase rounded-sm" style={{ color: '#e53935', background: 'rgba(229,57,53,0.15)' }}>
                    {secErrors} error{secErrors !== 1 ? 's' : ''}
                  </span>
                )}
                {secWarns > 0 && (
                  <span className="px-1.5 py-0.5 text-[9px] font-bold uppercase rounded-sm" style={{ color: '#ff9800', background: 'rgba(255,152,0,0.12)' }}>
                    {secWarns} warning{secWarns !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <span className="text-[rgba(255,255,255,0.4)] text-sm">{isOpen ? '▾' : '▸'}</span>
            </button>
            {isOpen && (
              <div className="px-4 pb-4 space-y-2 border-t border-[rgba(255,255,255,0.05)]">
                <div className="pt-3 space-y-2">
                  {sectionIssues.map((issue, i) => (
                    <div key={i} className="flex gap-2 items-start">
                      <span className="mt-0.5 text-sm leading-none" style={{ color: issue.severity === 'error' ? '#e53935' : '#ff9800' }}>
                        {issue.severity === 'error' ? '✖' : '▲'}
                      </span>
                      <div>
                        <span className="text-xs font-semibold text-[rgba(255,255,255,0.8)]">{issue.field_label ?? issue.path ?? 'Field'}</span>
                        <p className="text-[11px] text-[rgba(255,255,255,0.6)] mt-0.5">{issue.message}</p>
                        {issue.suggested_fix && (
                          <p className="text-[10px] text-[rgba(255,255,255,0.35)] mt-0.5">{issue.suggested_fix}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}

      {copilotResult && <CopilotResult result={copilotResult} />}
    </div>
  );
}

// ─── Rules Browser Tab ────────────────────────────────────────────────────────

function RulesBrowserTab({ activePackId, packs }: { activePackId: string | null; packs: NerisPack[] }) {
  const [packDetail, setPackDetail] = useState<{ pack: NerisPack; files?: unknown[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [subTab, setSubTab] = useState<'entity' | 'incident'>('entity');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!activePackId) return;
    setLoading(true);
    fetch(`${API}/api/v1/founder/neris/packs/${activePackId}`, {
      headers: { Authorization: getToken() },
    })
      .then((r) => r.json())
      .then((d) => setPackDetail(d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [activePackId]);

  if (!activePackId) {
    return (
      <div className="py-16 text-center text-[rgba(255,255,255,0.3)] text-sm max-w-md mx-auto">
        No active NERIS pack. Import and activate a pack in the Packs tab.
      </div>
    );
  }

  if (loading) {
    return <div className="py-16 text-center text-[rgba(255,255,255,0.3)] text-sm">Loading rules…</div>;
  }

  const rules = subTab === 'entity'
    ? (packDetail?.pack?.data?.rules_json?.entity_rules ?? [])
    : (packDetail?.pack?.data?.rules_json?.incident_rules ?? []);

  const activePack = packs.find((p) => p.id === activePackId);

  function toggleSection(id: string) {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleField(key: string) {
    setExpandedFields((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-[rgba(255,107,26,0.6)]">Active Pack</p>
          <p className="text-sm font-semibold text-white">{activePack?.name ?? activePackId}</p>
        </div>
        <div className="flex gap-1 border-b border-[rgba(255,255,255,0.08)] ml-auto">
          {(['entity', 'incident'] as const).map((k) => (
            <button
              key={k}
              onClick={() => setSubTab(k)}
              className={`px-4 py-2 text-xs font-semibold transition-colors border-b-2 -mb-px ${subTab === k ? 'text-[#ff6b1a] border-[#ff6b1a]' : 'text-[rgba(255,255,255,0.4)] border-transparent hover:text-[rgba(255,255,255,0.7)]'}`}
            >
              {k === 'entity' ? 'Entity Rules' : 'Incident Rules'}
            </button>
          ))}
        </div>
      </div>

      {rules.length === 0 && (
        <div className="py-16 text-center text-[rgba(255,255,255,0.3)] text-sm">
          No {subTab} rules found in this pack.
        </div>
      )}

      <div className="space-y-2">
        {rules.map((section) => {
          const isOpen = expandedSections.has(section.id);
          return (
            <div key={section.id} className="bg-[#0b0f14] border border-[rgba(255,255,255,0.08)] rounded-sm overflow-hidden">
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[rgba(255,255,255,0.02)] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono text-[rgba(255,255,255,0.35)]">{section.id}</span>
                  <span className="text-xs font-semibold text-[rgba(255,255,255,0.85)]">{section.label}</span>
                  <span className="px-1.5 py-0.5 text-[9px] font-semibold uppercase rounded-sm" style={{ color: '#22d3ee', background: 'rgba(34,211,238,0.1)', border: '1px solid rgba(34,211,238,0.2)' }}>
                    {section.fields.length} field{section.fields.length !== 1 ? 's' : ''}
                  </span>
                </div>
                <span className="text-[rgba(255,255,255,0.4)] text-sm">{isOpen ? '▾' : '▸'}</span>
              </button>
              {isOpen && (
                <div className="border-t border-[rgba(255,255,255,0.05)] px-4 py-3 space-y-1.5">
                  {section.fields.map((field) => {
                    const fKey = `${section.id}::${field.path}`;
                    const fOpen = expandedFields.has(fKey);
                    return (
                      <div key={field.path} className="rounded-sm overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
                        <button
                          onClick={() => toggleField(fKey)}
                          className="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-[rgba(255,255,255,0.02)] transition-colors"
                        >
                          <span className="text-[11px] font-mono text-[rgba(255,255,255,0.6)] flex-1 truncate">{field.path}</span>
                          {field.type && (
                            <span className="text-[9px] font-mono uppercase text-[rgba(255,255,255,0.35)]">{field.type}</span>
                          )}
                          {field.required && (
                            <span className="text-[9px] uppercase tracking-wider" style={{ color: '#ff6b1a' }}>req</span>
                          )}
                          {field.value_set && field.value_set.length > 0 && (
                            <span className="text-[9px] text-[rgba(255,255,255,0.3)]">{fOpen ? '▾' : '▸'} values</span>
                          )}
                        </button>
                        {fOpen && field.value_set && field.value_set.length > 0 && (
                          <div className="px-3 pb-3 border-t border-[rgba(255,255,255,0.04)]">
                            <p className="text-[9px] uppercase tracking-wider text-[rgba(255,255,255,0.3)] mt-2 mb-1.5">Allowed Values</p>
                            <div className="flex flex-wrap gap-1">
                              {field.value_set.map((v) => (
                                <span
                                  key={v}
                                  className="px-1.5 py-0.5 text-[10px] font-mono rounded-sm"
                                  style={{ background: 'rgba(168,85,247,0.1)', border: '1px solid rgba(168,85,247,0.2)', color: '#a855f7' }}
                                >
                                  {v}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const TABS: { key: TabKey; label: string }[] = [
  { key: 'packs', label: 'Packs' },
  { key: 'validate', label: 'Validate' },
  { key: 'fixlist', label: 'Fix List' },
  { key: 'rules', label: 'Rules Browser' },
];

export default function NerisComplianceStudioPage() {
  const [tab, setTab] = useState<TabKey>('packs');
  const [packs, setPacks] = useState<NerisPack[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);
  const [persistedIssues, setPersistedIssues] = useState<ValidationIssue[]>([]);
  const { toasts, push: pushToast } = useToast();

  const activePackId = packs.find((p) => p.status === 'active')?.id ?? null;

  const fetchPacks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/founder/neris/packs`, {
        headers: { Authorization: getToken() },
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setPacks(Array.isArray(data) ? data : data.packs ?? []);
      setLastRefreshed(new Date());
    } catch {
      pushToast('Failed to load packs', 'error');
    } finally {
      setLoading(false);
    }
  }, [pushToast]);

  useEffect(() => {
    fetchPacks();
    const interval = setInterval(fetchPacks, 30000);
    return () => clearInterval(interval);
  }, [fetchPacks]);

  const fixListCount = persistedIssues.length;

  return (
    <div className="min-h-screen bg-[#07090d] text-white p-5">
      <Toast items={toasts} />

      {showImportModal && (
        <ImportModal
          onClose={() => setShowImportModal(false)}
          onImported={fetchPacks}
        />
      )}

      {/* Page Header */}
      <div className="mb-5">
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">
          5 · COMPLIANCE
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-lg font-black uppercase tracking-wider text-white">
            NERIS COMPLIANCE STUDIO
          </h1>
          <span className="text-base">🏴</span>
          <span
            className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
            style={{ color: '#22d3ee', background: 'rgba(34,211,238,0.1)', border: '1px solid rgba(34,211,238,0.2)' }}
          >
            Wisconsin RMS-Only
          </span>
        </div>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">
          Pack management · Validation engine · Copilot fix assistant · Rules browser
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[rgba(255,255,255,0.08)] pb-0 mb-5">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-xs font-semibold transition-colors border-b-2 -mb-px relative ${
              tab === t.key
                ? 'text-[#ff6b1a] border-[#ff6b1a]'
                : 'text-[rgba(255,255,255,0.4)] border-transparent hover:text-[rgba(255,255,255,0.7)]'
            }`}
          >
            {t.label}
            {t.key === 'fixlist' && fixListCount > 0 && (
              <span
                className="ml-1.5 px-1.5 py-0.5 text-[9px] font-bold rounded-sm"
                style={{ background: 'rgba(229,57,53,0.2)', color: '#e53935' }}
              >
                {fixListCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div>
        {tab === 'packs' && (
          <PacksTab
            packs={packs}
            loading={loading}
            lastRefreshed={lastRefreshed}
            onRefresh={fetchPacks}
            onImport={() => setShowImportModal(true)}
            activePackId={activePackId}
          />
        )}
        {tab === 'validate' && (
          <ValidateTab
            activePackId={activePackId}
            onIssuesPersist={setPersistedIssues}
          />
        )}
        {tab === 'fixlist' && <FixListTab issues={persistedIssues} />}
        {tab === 'rules' && (
          <RulesBrowserTab activePackId={activePackId} packs={packs} />
        )}
      </div>
    </div>
  );
}
