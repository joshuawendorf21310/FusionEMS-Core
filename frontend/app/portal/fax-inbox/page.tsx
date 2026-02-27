'use client';

import { useEffect, useState, useCallback } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function authHeader() {
  return { Authorization: 'Bearer ' + (localStorage.getItem('qs_token') || '') };
}

type MatchSuggestion = {
  claim_id: string;
  patient_name?: string;
  score?: number;
};

type FaxItem = {
  id: string;
  from_number?: string;
  to_number?: string;
  received_at?: string;
  page_count?: number;
  document_match_status?: string;
  status?: string;
  data?: {
    match_suggestions?: MatchSuggestion[];
    claim_id?: string;
    patient_name?: string;
    match_type?: string;
    confidence?: number;
  };
};

type FilterTab = 'all' | 'unmatched' | 'matched' | 'review';

function relativeTime(iso?: string): string {
  if (!iso) return 'N/A';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function MatchChip({ fax }: { fax: FaxItem }) {
  const status = fax.document_match_status ?? fax.status ?? '';
  if (status === 'matched') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-[#4caf50]/20 text-[#4caf50] border border-[#4caf50]/30">
        AUTO-MATCHED
      </span>
    );
  }
  if (status === 'review') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-[#ff9800]/20 text-[#ff9800] border border-[#ff9800]/30">
        NEEDS REVIEW
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-white/10 text-white/50 border border-white/10">
      UNMATCHED
    </span>
  );
}

function FaxIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 18H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2" />
      <rect x="6" y="14" width="12" height="8" rx="1" />
      <path d="M6 2h12v4H6z" />
    </svg>
  );
}

export default function FaxInboxPage() {
  const [faxes, setFaxes] = useState<FaxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<FilterTab>('all');
  const [selected, setSelected] = useState<FaxItem | null>(null);
  const [actionLoading, setActionLoading] = useState('');
  const [actionMsg, setActionMsg] = useState('');

  const fetchFaxes = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/v1/fax/inbox?status=all&limit=50`, {
        headers: authHeader(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const items: FaxItem[] = Array.isArray(json) ? json : (json.items ?? json.faxes ?? []);
      setFaxes(items);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load faxes');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchFaxes(); }, [fetchFaxes]);

  const filteredFaxes = faxes.filter((f) => {
    const s = f.document_match_status ?? f.status ?? '';
    if (filter === 'all') return true;
    if (filter === 'matched') return s === 'matched';
    if (filter === 'review') return s === 'review';
    if (filter === 'unmatched') return s !== 'matched' && s !== 'review';
    return true;
  });

  async function triggerMatch(faxId: string) {
    setActionLoading('trigger-' + faxId);
    setActionMsg('');
    try {
      const res = await fetch(`${API}/api/v1/fax/${faxId}/match/trigger`, {
        method: 'POST',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
      });
      const json = await res.json();
      setActionMsg(res.ok ? 'Match triggered successfully.' : (json.detail ?? 'Error triggering match'));
      if (res.ok) {
        await fetchFaxes();
        const updated = faxes.find((f) => f.id === faxId);
        if (updated) setSelected(updated);
      }
    } catch {
      setActionMsg('Network error.');
    } finally {
      setActionLoading('');
    }
  }

  async function attachFax(claimId: string, faxId: string) {
    setActionLoading('attach-' + faxId);
    setActionMsg('');
    try {
      const res = await fetch(`${API}/api/v1/claims/${claimId}/documents/attach-fax`, {
        method: 'POST',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ fax_id: faxId, attachment_type: 'manual' }),
      });
      const json = await res.json();
      setActionMsg(res.ok ? 'Fax attached to claim.' : (json.detail ?? 'Error attaching fax'));
      if (res.ok) await fetchFaxes();
    } catch {
      setActionMsg('Network error.');
    } finally {
      setActionLoading('');
    }
  }

  async function detachFax(faxId: string) {
    setActionLoading('detach-' + faxId);
    setActionMsg('');
    try {
      const res = await fetch(`${API}/api/v1/fax/${faxId}/match/detach`, {
        method: 'POST',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
      });
      const json = await res.json();
      setActionMsg(res.ok ? 'Match detached.' : (json.detail ?? 'Error detaching'));
      if (res.ok) await fetchFaxes();
    } catch {
      setActionMsg('Network error.');
    } finally {
      setActionLoading('');
    }
  }

  const TABS: { key: FilterTab; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'unmatched', label: 'Unmatched' },
    { key: 'matched', label: 'Matched' },
    { key: 'review', label: 'Review' },
  ];

  return (
    <div className="min-h-screen bg-[#07090d] text-white flex flex-col">
      <div className="flex flex-1 overflow-hidden" style={{ height: 'calc(100vh - 0px)' }}>
        {/* Left Panel */}
        <div className="w-[340px] shrink-0 flex flex-col border-r border-[rgba(255,255,255,0.08)] bg-[#0b0f14]">
          {/* Header */}
          <div className="px-4 pt-5 pb-3 border-b border-[rgba(255,255,255,0.08)]">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold tracking-widest text-white/70 uppercase">Fax Inbox</span>
              <span className="ml-1 bg-[#ff6b1a]/20 text-[#ff6b1a] border border-[#ff6b1a]/30 text-[10px] font-bold px-2 py-0.5 rounded-full">
                {faxes.length}
              </span>
            </div>
            {/* Filter Tabs */}
            <div className="flex gap-1 mt-3">
              {TABS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setFilter(t.key)}
                  className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                    filter === t.key
                      ? 'bg-[#ff6b1a]/20 text-[#ff6b1a] border border-[#ff6b1a]/40'
                      : 'text-white/40 hover:text-white/70 border border-transparent'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Fax List */}
          <div className="flex-1 overflow-y-auto">
            {loading && (
              <div className="flex items-center justify-center h-32 text-white/30 text-sm">Loading...</div>
            )}
            {!loading && error && (
              <div className="m-4 p-3 rounded bg-[#e53935]/10 border border-[#e53935]/30 text-[#e53935] text-xs">{error}</div>
            )}
            {!loading && !error && filteredFaxes.length === 0 && (
              <div className="flex items-center justify-center h-32 text-white/30 text-sm">No faxes</div>
            )}
            {!loading && filteredFaxes.map((fax) => {
              const isSelected = selected?.id === fax.id;
              const confidence = fax.data?.confidence;
              return (
                <button
                  key={fax.id}
                  onClick={() => { setSelected(fax); setActionMsg(''); }}
                  className={`w-full text-left px-4 py-3 border-b border-[rgba(255,255,255,0.06)] transition-colors flex gap-3 items-start ${
                    isSelected ? 'bg-[#ff6b1a]/10' : 'hover:bg-white/[0.03]'
                  }`}
                >
                  {/* Thumbnail */}
                  <div className="w-12 h-16 shrink-0 rounded bg-white/10 border border-white/10 flex items-center justify-center text-white/30">
                    <FaxIcon />
                  </div>
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-mono text-white/80 truncate">{fax.from_number ?? 'N/A'}</div>
                    <div className="text-[10px] text-white/40 mt-0.5">{relativeTime(fax.received_at)}</div>
                    <div className="text-[10px] text-white/30 mt-0.5">{fax.page_count ?? 0} page{(fax.page_count ?? 0) !== 1 ? 's' : ''}</div>
                    <div className="flex flex-wrap gap-1 mt-1.5 items-center">
                      <MatchChip fax={fax} />
                      {confidence != null && (
                        <span className="text-[10px] text-[#22d3ee] font-mono">{Math.round(confidence * 100)}% match</span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Panel */}
        <div className="flex-1 overflow-y-auto bg-[#07090d] p-6">
          {!selected ? (
            <div className="flex flex-col items-center justify-center h-full text-white/20">
              <FaxIcon />
              <p className="mt-3 text-sm">Select a fax to view details</p>
            </div>
          ) : (
            <div className="max-w-2xl mx-auto space-y-5">
              {/* Header */}
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-base font-bold text-white">Fax Detail</h2>
                  <p className="text-xs text-white/40 font-mono mt-0.5">{selected.id}</p>
                </div>
                <a
                  href={`${API}/api/v1/fax/${selected.id}/download`}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-1.5 rounded bg-[#ff6b1a]/20 border border-[#ff6b1a]/40 text-[#ff6b1a] text-xs font-semibold hover:bg-[#ff6b1a]/30 transition-colors"
                >
                  Download
                </a>
              </div>

              {/* Metadata */}
              <div className="bg-[#0b0f14] border border-[rgba(255,255,255,0.08)] rounded-sm p-4 grid grid-cols-2 gap-3">
                {[
                  ['From', selected.from_number ?? 'N/A'],
                  ['To', selected.to_number ?? 'N/A'],
                  ['Received', selected.received_at ? new Date(selected.received_at).toLocaleString() : 'N/A'],
                  ['Pages', String(selected.page_count ?? 'N/A')],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="text-[10px] text-white/40 uppercase tracking-wider">{label}</p>
                    <p className="text-sm text-white/80 font-mono mt-0.5">{value}</p>
                  </div>
                ))}
              </div>

              {/* Action message */}
              {actionMsg && (
                <div className={`p-3 rounded text-xs border ${
                  actionMsg.includes('success') || actionMsg.includes('attached') || actionMsg.includes('triggered') || actionMsg.includes('detached')
                    ? 'bg-[#4caf50]/10 border-[#4caf50]/30 text-[#4caf50]'
                    : 'bg-[#e53935]/10 border-[#e53935]/30 text-[#e53935]'
                }`}>
                  {actionMsg}
                </div>
              )}

              {/* Match Section */}
              <div className="bg-[#0b0f14] border border-[rgba(255,255,255,0.08)] rounded-sm p-4 space-y-4">
                <h3 className="text-xs font-bold tracking-widest text-white/60 uppercase">Match</h3>

                {(selected.document_match_status ?? selected.status) === 'matched' ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        ['Claim ID', selected.data?.claim_id ?? 'N/A'],
                        ['Patient', selected.data?.patient_name ?? 'N/A'],
                        ['Match Type', selected.data?.match_type ?? 'N/A'],
                        ['Confidence', selected.data?.confidence != null ? `${Math.round(selected.data.confidence * 100)}%` : 'N/A'],
                      ].map(([label, value]) => (
                        <div key={label}>
                          <p className="text-[10px] text-white/40 uppercase tracking-wider">{label}</p>
                          <p className="text-sm text-white/80 font-mono mt-0.5">{value}</p>
                        </div>
                      ))}
                    </div>
                    <button
                      onClick={() => detachFax(selected.id)}
                      disabled={!!actionLoading}
                      className="px-4 py-1.5 rounded bg-[#e53935]/10 border border-[#e53935]/30 text-[#e53935] text-xs font-semibold hover:bg-[#e53935]/20 transition-colors disabled:opacity-40"
                    >
                      {actionLoading === 'detach-' + selected.id ? 'Detaching...' : 'Detach'}
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <button
                      onClick={() => triggerMatch(selected.id)}
                      disabled={!!actionLoading}
                      className="px-4 py-1.5 rounded bg-[#22d3ee]/10 border border-[#22d3ee]/30 text-[#22d3ee] text-xs font-semibold hover:bg-[#22d3ee]/20 transition-colors disabled:opacity-40"
                    >
                      {actionLoading === 'trigger-' + selected.id ? 'Searching...' : 'Find Match'}
                    </button>
                  </div>
                )}

                {/* Match Suggestions */}
                {(selected.data?.match_suggestions?.length ?? 0) > 0 && (
                  <div className="space-y-2 pt-2 border-t border-white/[0.06]">
                    <p className="text-[10px] text-white/40 uppercase tracking-wider">Suggestions</p>
                    {selected.data!.match_suggestions!.map((s, i) => {
                      const pct = s.score != null ? Math.round(s.score * 100) : null;
                      return (
                        <div key={i} className="flex items-center gap-3 bg-white/[0.03] rounded p-3 border border-white/[0.06]">
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-mono text-white/80 truncate">{s.claim_id}</p>
                            <p className="text-[10px] text-white/40 mt-0.5">{s.patient_name ?? 'N/A'}</p>
                            {pct != null && (
                              <div className="mt-1.5 flex items-center gap-2">
                                <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                  <div
                                    className="h-full rounded-full bg-[#22d3ee]"
                                    style={{ width: `${pct}%` }}
                                  />
                                </div>
                                <span className="text-[10px] text-[#22d3ee] font-mono">{pct}%</span>
                              </div>
                            )}
                          </div>
                          <button
                            onClick={() => attachFax(s.claim_id, selected.id)}
                            disabled={!!actionLoading}
                            className="px-3 py-1 rounded bg-[#4caf50]/10 border border-[#4caf50]/30 text-[#4caf50] text-[11px] font-semibold hover:bg-[#4caf50]/20 transition-colors disabled:opacity-40 shrink-0"
                          >
                            {actionLoading === 'attach-' + selected.id ? '...' : 'Attach'}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
