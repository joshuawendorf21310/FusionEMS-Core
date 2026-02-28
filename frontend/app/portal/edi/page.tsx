'use client';
import { QuantumTableSkeleton, QuantumCardSkeleton } from '@/components/ui';

import { useEffect, useState, useCallback } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function authHeader() {
  return { Authorization: 'Bearer ' + (localStorage.getItem('qs_token') || '') };
}

// ── Types ────────────────────────────────────────────────────────────────────

type BatchStatus = 'pending' | 'submitted' | 'accepted' | 'rejected' | 'partial';

type EdiBatch = {
  id: string;
  created_at?: string;
  claim_count?: number;
  status?: BatchStatus | string;
  claim_ids?: string[];
  validation_errors?: string[];
  metadata?: Record<string, unknown>;
};

type GenerateForm = {
  claim_ids_raw: string;
  npi: string;
  name: string;
  ein: string;
};

type IngestResult = {
  ok: boolean;
  data?: unknown;
  errors?: string[];
};

type ExplainData = {
  explanation?: {
    overall_status?: string;
    adjustment_reasons?: { code: string; description: string }[];
    denial_analysis?: string;
    recommended_actions?: string[];
    next_steps?: string;
  };
  [key: string]: unknown;
};

type TabKey = 'batches' | 'ingest' | 'explain';

// ── Helpers ──────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status?: string }) {
  const s = (status ?? '').toLowerCase();
  const map: Record<string, string> = {
    pending: 'bg-white/10 text-text-primary/50 border-white/10',
    submitted: 'bg-system-billing/20 text-system-billing border-system-billing/30',
    accepted: 'bg-status-active/20 text-status-active border-status-active/30',
    rejected: 'bg-red/20 text-red border-red/30',
    partial: 'bg-status-warning/20 text-status-warning border-status-warning/30',
  };
  const cls = map[s] ?? 'bg-white/10 text-text-primary/40 border-white/10';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${cls}`}>
      {status ?? 'unknown'}
    </span>
  );
}

function CollapsibleJson({ data }: { data: unknown }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-[11px] text-system-billing hover:underline"
      >
        {open ? 'Hide' : 'Show'} parsed result
      </button>
      {open && (
        <pre className="mt-2 p-3 bg-black rounded text-green-400 text-xs overflow-x-auto whitespace-pre-wrap break-all border border-white/10">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

// ── BATCHES TAB ──────────────────────────────────────────────────────────────

function BatchesTab() {
  const [batches, setBatches] = useState<EdiBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [drawerBatch, setDrawerBatch] = useState<EdiBatch | null>(null);
  const [showGenModal, setShowGenModal] = useState(false);
  const [genForm, setGenForm] = useState<GenerateForm>({ claim_ids_raw: '', npi: '', name: '', ein: '' });
  const [genLoading, setGenLoading] = useState(false);
  const [genError, setGenError] = useState('');
  const [genResult, setGenResult] = useState<EdiBatch | null>(null);

  const fetchBatches = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/v1/edi/batches`, { headers: authHeader() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const items: EdiBatch[] = Array.isArray(json) ? json : (json.items ?? json.batches ?? []);
      setBatches(items);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load batches');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchBatches(); }, [fetchBatches]);

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    setGenLoading(true);
    setGenError('');
    setGenResult(null);
    try {
      const claim_ids = genForm.claim_ids_raw.split(',').map((s) => s.trim()).filter(Boolean);
      const res = await fetch(`${API}/api/v1/edi/batches/generate`, {
        method: 'POST',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claim_ids,
          submitter_config: { npi: genForm.npi, name: genForm.name, ein: genForm.ein },
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? `HTTP ${res.status}`);
      setGenResult(json);
      await fetchBatches();
    } catch (e: unknown) {
      setGenError(e instanceof Error ? e.message : 'Generation failed');
    } finally {
      setGenLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-text-primary/40">EDI 837 batch history</p>
        <button
          onClick={() => { setShowGenModal(true); setGenResult(null); setGenError(''); }}
          className="px-4 py-1.5 rounded bg-orange/20 border border-orange/40 text-orange text-xs font-semibold hover:bg-orange/30 transition-colors"
        >
          + Generate New Batch
        </button>
      </div>

      {loading && <div className="p-6"><QuantumTableSkeleton rows={6} cols={4} /></div>}
      {!loading && error && (
        <div className="p-3 rounded bg-red/10 border border-red/30 text-red text-xs">{error}</div>
      )}
      {!loading && !error && (
        <div className="bg-bg-base border border-border-DEFAULT rounded-sm overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border-DEFAULT">
                {['Batch ID', 'Created At', 'Claims', 'Status', 'Actions'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-[10px] font-bold text-text-primary/40 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {batches.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-text-primary/30">No batches found</td>
                </tr>
              )}
              {batches.map((b) => (
                <tr key={b.id} className="border-b border-border-subtle hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 font-mono text-text-primary/70">{b.id.length > 16 ? b.id.slice(0, 8) + '…' + b.id.slice(-4) : b.id}</td>
                  <td className="px-4 py-3 text-text-primary/50">{b.created_at ? new Date(b.created_at).toLocaleString() : 'N/A'}</td>
                  <td className="px-4 py-3 text-text-primary/70">{b.claim_count ?? b.claim_ids?.length ?? 'N/A'}</td>
                  <td className="px-4 py-3"><StatusBadge status={b.status} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <a
                        href={`${API}/api/v1/edi/batches/${b.id}/download`}
                        target="_blank"
                        rel="noreferrer"
                        className="px-2.5 py-1 rounded bg-system-billing/10 border border-system-billing/30 text-system-billing text-[11px] font-semibold hover:bg-system-billing/20 transition-colors"
                      >
                        Download 837
                      </a>
                      <button
                        onClick={() => setDrawerBatch(b)}
                        className="px-2.5 py-1 rounded bg-white/5 border border-white/10 text-text-primary/60 text-[11px] font-semibold hover:bg-white/10 transition-colors"
                      >
                        View Detail
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail Drawer */}
      {drawerBatch && (
        <div className="fixed inset-0 z-50 flex" onClick={() => setDrawerBatch(null)}>
          <div className="flex-1 bg-black/60" />
          <div
            className="w-[480px] h-full bg-bg-base border-l border-border-DEFAULT overflow-y-auto p-6 space-y-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-text-primary">Batch Detail</h3>
              <button onClick={() => setDrawerBatch(null)} className="text-text-primary/40 hover:text-text-primary text-lg leading-none">&times;</button>
            </div>
            <div className="space-y-2">
              {[
                ['ID', drawerBatch.id],
                ['Status', ''],
                ['Created', drawerBatch.created_at ? new Date(drawerBatch.created_at).toLocaleString() : 'N/A'],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="text-[10px] text-text-primary/40 uppercase w-20 shrink-0">{label}</span>
                  {label === 'Status' ? <StatusBadge status={drawerBatch.status} /> : <span className="text-xs font-mono text-text-primary/70 break-all">{value}</span>}
                </div>
              ))}
            </div>
            {(drawerBatch.claim_ids?.length ?? 0) > 0 && (
              <div>
                <p className="text-[10px] text-text-primary/40 uppercase tracking-wider mb-2">Claim IDs ({drawerBatch.claim_ids!.length})</p>
                <div className="flex flex-wrap gap-1.5">
                  {drawerBatch.claim_ids!.map((cid) => (
                    <span key={cid} className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[11px] font-mono text-text-primary/60">{cid}</span>
                  ))}
                </div>
              </div>
            )}
            {(drawerBatch.validation_errors?.length ?? 0) > 0 && (
              <div>
                <p className="text-[10px] text-text-primary/40 uppercase tracking-wider mb-2">Validation Errors</p>
                <ul className="space-y-1">
                  {drawerBatch.validation_errors!.map((err, i) => (
                    <li key={i} className="text-xs text-red bg-red/5 border border-red/20 rounded px-3 py-1.5">{err}</li>
                  ))}
                </ul>
              </div>
            )}
            {drawerBatch.metadata && Object.keys(drawerBatch.metadata).length > 0 && (
              <div>
                <p className="text-[10px] text-text-primary/40 uppercase tracking-wider mb-2">Metadata</p>
                <pre className="p-3 bg-black rounded text-green-400 text-xs overflow-x-auto whitespace-pre-wrap break-all border border-white/10">
                  {JSON.stringify(drawerBatch.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Generate Modal */}
      {showGenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" onClick={() => setShowGenModal(false)}>
          <div
            className="w-[480px] bg-bg-base border border-border-DEFAULT rounded-sm p-6 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-text-primary">Generate New EDI Batch</h3>
              <button onClick={() => setShowGenModal(false)} className="text-text-primary/40 hover:text-text-primary text-lg leading-none">&times;</button>
            </div>
            <form onSubmit={handleGenerate} className="space-y-3">
              <div>
                <label className="block text-[10px] text-text-primary/40 uppercase tracking-wider mb-1">Claim IDs (comma-separated)</label>
                <textarea
                  value={genForm.claim_ids_raw}
                  onChange={(e) => setGenForm((f) => ({ ...f, claim_ids_raw: e.target.value }))}
                  rows={3}
                  placeholder="claim-001, claim-002, ..."
                  className="w-full bg-black/30 border border-white/10 rounded px-3 py-2 text-xs text-text-primary/80 placeholder-white/20 focus:outline-none focus:border-orange/50 resize-none"
                />
              </div>
              {[
                { key: 'npi' as const, label: 'Submitter NPI', placeholder: '1234567890' },
                { key: 'name' as const, label: 'Submitter Name', placeholder: 'Organization Name' },
                { key: 'ein' as const, label: 'Submitter EIN', placeholder: '12-3456789' },
              ].map((field) => (
                <div key={field.key}>
                  <label className="block text-[10px] text-text-primary/40 uppercase tracking-wider mb-1">{field.label}</label>
                  <input
                    type="text"
                    value={genForm[field.key]}
                    onChange={(e) => setGenForm((f) => ({ ...f, [field.key]: e.target.value }))}
                    placeholder={field.placeholder}
                    className="w-full bg-black/30 border border-white/10 rounded px-3 py-2 text-xs text-text-primary/80 placeholder-white/20 focus:outline-none focus:border-orange/50"
                  />
                </div>
              ))}
              {genError && (
                <div className="p-2 rounded bg-red/10 border border-red/30 text-red text-xs">{genError}</div>
              )}
              {genResult && (
                <div className="p-3 rounded bg-status-active/10 border border-status-active/30 text-status-active text-xs space-y-1">
                  <p className="font-semibold">Batch generated successfully</p>
                  <p className="font-mono text-[10px] text-text-primary/50">ID: {genResult.id}</p>
                </div>
              )}
              <div className="flex gap-2 pt-1">
                <button
                  type="submit"
                  disabled={genLoading}
                  className="flex-1 py-2 rounded bg-orange/20 border border-orange/40 text-orange text-xs font-semibold hover:bg-orange/30 transition-colors disabled:opacity-40"
                >
                  {genLoading ? 'Generating...' : 'Generate Batch'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowGenModal(false)}
                  className="px-4 py-2 rounded bg-white/5 border border-white/10 text-text-primary/50 text-xs font-semibold hover:bg-white/10 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ── INGEST TAB ───────────────────────────────────────────────────────────────

type IngestType = '999' | '277' | '835';

const INGEST_CONFIG: { type: IngestType; title: string; description: string; hasBatchId: boolean }[] = [
  { type: '999', title: 'Ingest 999', description: 'Functional Acknowledgment — confirms EDI 837 was received and syntactically valid.', hasBatchId: true },
  { type: '277', title: 'Ingest 277', description: 'Claim Status — updates whether claims were accepted, rejected, or pended.', hasBatchId: false },
  { type: '835', title: 'Ingest 835', description: 'Electronic Remittance Advice — payment, adjustment, and denial details.', hasBatchId: false },
];

function IngestCard({ config }: { config: typeof INGEST_CONFIG[number] }) {
  const [content, setContent] = useState('');
  const [batchId, setBatchId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IngestResult | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const body: Record<string, string> = { x12_content: content };
      if (config.hasBatchId && batchId) body.batch_id = batchId;
      const res = await fetch(`${API}/api/v1/edi/ingest/${config.type}`, {
        method: 'POST',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const json = await res.json();
      if (!res.ok) {
        const errs = json.detail
          ? (Array.isArray(json.detail) ? json.detail.map((d: unknown) => JSON.stringify(d)) : [String(json.detail)])
          : [`HTTP ${res.status}`];
        setResult({ ok: false, errors: errs });
      } else {
        setResult({ ok: true, data: json });
      }
    } catch (e: unknown) {
      setResult({ ok: false, errors: [e instanceof Error ? e.message : 'Network error'] });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-bg-base border border-border-DEFAULT rounded-sm p-5 flex flex-col gap-4">
      <div>
        <h3 className="text-sm font-bold text-text-primary">{config.title}</h3>
        <p className="text-xs text-text-primary/40 mt-1 leading-relaxed">{config.description}</p>
      </div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 flex-1">
        <div className="flex-1">
          <label className="block text-[10px] text-text-primary/40 uppercase tracking-wider mb-1">X12 Content</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={6}
            placeholder="ISA*00*          *00*..."
            className="w-full bg-black/30 border border-white/10 rounded px-3 py-2 text-xs font-mono text-text-primary/80 placeholder-white/20 focus:outline-none focus:border-orange/50 resize-y"
          />
        </div>
        {config.hasBatchId && (
          <div>
            <label className="block text-[10px] text-text-primary/40 uppercase tracking-wider mb-1">Batch ID (optional)</label>
            <input
              type="text"
              value={batchId}
              onChange={(e) => setBatchId(e.target.value)}
              placeholder="batch-uuid"
              className="w-full bg-black/30 border border-white/10 rounded px-3 py-2 text-xs text-text-primary/80 placeholder-white/20 focus:outline-none focus:border-orange/50"
            />
          </div>
        )}
        <button
          type="submit"
          disabled={loading || !content.trim()}
          className="py-2 rounded bg-orange/20 border border-orange/40 text-orange text-xs font-semibold hover:bg-orange/30 transition-colors disabled:opacity-40"
        >
          {loading ? 'Submitting...' : `Submit ${config.type}`}
        </button>
      </form>

      {result && (
        <div className="space-y-2">
          {!result.ok && result.errors && (
            <div className="space-y-1">
              {result.errors.map((err, i) => (
                <div key={i} className="p-2 rounded bg-red/10 border border-red/30 text-red text-xs">{err}</div>
              ))}
            </div>
          )}
          {result.ok && result.data != null && <CollapsibleJson data={result.data} />}
        </div>
      )}
    </div>
  );
}

function IngestTab() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {INGEST_CONFIG.map((cfg) => (
        <IngestCard key={cfg.type} config={cfg} />
      ))}
    </div>
  );
}

// ── EXPLAIN TAB ──────────────────────────────────────────────────────────────

function OverallStatusChip({ status }: { status?: string }) {
  const s = (status ?? '').toLowerCase();
  const map: Record<string, string> = {
    paid: 'bg-status-active/20 text-status-active border-status-active/30',
    denied: 'bg-red/20 text-red border-red/30',
    pending: 'bg-status-warning/20 text-status-warning border-status-warning/30',
  };
  const cls = map[s] ?? 'bg-white/10 text-text-primary/50 border-white/10';
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded text-xs font-bold uppercase border ${cls}`}>
      {status ?? 'unknown'}
    </span>
  );
}

function ExplainTab() {
  const [claimId, setClaimId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<ExplainData | null>(null);

  async function handleExplain(e: React.FormEvent) {
    e.preventDefault();
    if (!claimId.trim()) return;
    setLoading(true);
    setError('');
    setData(null);
    try {
      const res = await fetch(`${API}/api/v1/edi/claims/${claimId.trim()}/explain`, {
        headers: authHeader(),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? `HTTP ${res.status}`);
      setData(json);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to get explanation');
    } finally {
      setLoading(false);
    }
  }

  const explanation = data?.explanation;

  return (
    <div className="max-w-2xl space-y-5">
      <form onSubmit={handleExplain} className="flex gap-2">
        <input
          type="text"
          value={claimId}
          onChange={(e) => setClaimId(e.target.value)}
          placeholder="Enter Claim ID..."
          className="flex-1 bg-bg-base border border-border-DEFAULT rounded px-4 py-2 text-sm text-text-primary/80 placeholder-white/20 focus:outline-none focus:border-orange/50"
        />
        <button
          type="submit"
          disabled={loading || !claimId.trim()}
          className="px-5 py-2 rounded bg-orange/20 border border-orange/40 text-orange text-sm font-semibold hover:bg-orange/30 transition-colors disabled:opacity-40 whitespace-nowrap"
        >
          {loading ? 'Analyzing...' : 'Get AI Explanation'}
        </button>
      </form>

      {error && (
        <div className="p-3 rounded bg-red/10 border border-red/30 text-red text-xs">{error}</div>
      )}

      {explanation && (
        <div className="bg-bg-base border border-border-DEFAULT rounded-sm p-5 space-y-5">
          {/* Overall Status */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-text-primary/40 uppercase tracking-wider">Overall Status</span>
            <OverallStatusChip status={explanation.overall_status} />
          </div>

          {/* Adjustment Reasons */}
          {(explanation.adjustment_reasons?.length ?? 0) > 0 && (
            <div>
              <p className="text-[10px] text-text-primary/40 uppercase tracking-wider mb-2">Adjustment Reasons</p>
              <div className="space-y-2">
                {explanation.adjustment_reasons!.map((r, i) => (
                  <div key={i} className="flex gap-3 bg-white/[0.03] border border-white/[0.06] rounded px-3 py-2">
                    <span className="text-[11px] font-bold font-mono text-status-warning shrink-0 mt-px">{r.code}</span>
                    <span className="text-xs text-text-primary/70">{r.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Denial Analysis */}
          {explanation.denial_analysis && (
            <div>
              <p className="text-[10px] text-text-primary/40 uppercase tracking-wider mb-2">Denial Analysis</p>
              <p className="text-xs text-text-primary/70 leading-relaxed bg-red/5 border border-red/10 rounded px-3 py-2">
                {explanation.denial_analysis}
              </p>
            </div>
          )}

          {/* Recommended Actions */}
          {(explanation.recommended_actions?.length ?? 0) > 0 && (
            <div>
              <p className="text-[10px] text-text-primary/40 uppercase tracking-wider mb-2">Recommended Actions</p>
              <ol className="space-y-2">
                {explanation.recommended_actions!.map((action, i) => (
                  <li key={i} className="flex gap-3 text-xs text-text-primary/70">
                    <span className="w-5 h-5 shrink-0 rounded-full bg-orange/20 border border-orange/30 text-orange flex items-center justify-center text-[10px] font-bold">
                      {i + 1}
                    </span>
                    <span className="leading-relaxed mt-px">{action}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Next Steps */}
          {explanation.next_steps && (
            <div>
              <p className="text-[10px] text-text-primary/40 uppercase tracking-wider mb-2">Next Steps</p>
              <p className="text-xs text-text-primary/70 leading-relaxed bg-system-billing/5 border border-system-billing/10 rounded px-3 py-2">
                {explanation.next_steps}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── PAGE ─────────────────────────────────────────────────────────────────────

const TABS: { key: TabKey; label: string }[] = [
  { key: 'batches', label: 'Batches' },
  { key: 'ingest', label: 'Ingest' },
  { key: 'explain', label: 'Explain' },
];

export default function EdiPage() {
  const [tab, setTab] = useState<TabKey>('batches');

  return (
    <div className="min-h-screen bg-bg-void text-text-primary">
      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-lg font-bold text-text-primary tracking-tight">EDI Batch Management</h1>
          <p className="text-xs text-text-primary/40 mt-1">Generate, track, and process EDI 837 batches and remittance data</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border-DEFAULT pb-0">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2.5 text-xs font-semibold transition-colors border-b-2 -mb-px ${
                tab === t.key
                  ? 'text-orange border-orange'
                  : 'text-text-primary/40 border-transparent hover:text-text-primary/70'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div>
          {tab === 'batches' && <BatchesTab />}
          {tab === 'ingest' && <IngestTab />}
          {tab === 'explain' && <ExplainTab />}
        </div>
      </div>
    </div>
  );
}
