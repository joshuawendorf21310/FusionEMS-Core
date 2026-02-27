"use client";
import { useState, useEffect, useRef } from "react";

const API = "/api/v1/founder/compliance";

interface Pack {
  pack_id: string;
  name: string;
  jurisdiction: string;
  s3_key?: string;
  tags?: string[];
}

interface RecommendedSet {
  set_id: string;
  label: string;
  description: string;
  pack_ids: string[];
  tags?: string[];
}

interface PackIndex {
  packs: Pack[];
  recommended_sets: RecommendedSet[];
}

interface TenantStatus {
  tenant_id: string;
  active_pack_ids: string[];
  active_set_id: string | null;
  active_packs: { pack_id: string; name: string; jurisdiction: string; status: string }[];
  fleet_score: number | null;
  last_inspection: string | null;
  inspections_total: number;
  updated_at: string | null;
  updated_by: string | null;
}

const JURISDICTION_COLORS: Record<string, string> = {
  WI_STATE: "bg-blue-900/40 text-blue-300 border-blue-800",
  US_FEDERAL: "bg-red-900/40 text-red-300 border-red-800",
  US_ACCREDITATION: "bg-purple-900/40 text-purple-300 border-purple-800",
  CAMTS_GLOBAL: "bg-sky-900/40 text-sky-300 border-sky-800",
  HOSPITAL_ACCREDITATION: "bg-teal-900/40 text-teal-300 border-teal-800",
};

const SET_ICONS: Record<string, string> = {
  WI_GROUND_DEFAULT: "WI",
  WI_GROUND_CAAS: "WI+",
  HEMS_CAMTS_READY: "AIR",
  HOSPITAL_EMS_ALIGNMENT: "RX",
};

export default function FounderCompliancePacksPage() {
  const [index, setIndex] = useState<PackIndex | null>(null);
  const [tenantId, setTenantId] = useState("");
  const [tenantStatus, setTenantStatus] = useState<TenantStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [applying, setApplying] = useState<string | null>(null);
  const [progressLog, setProgressLog] = useState<string[]>([]);
  const [confirmSet, setConfirmSet] = useState<RecommendedSet | null>(null);
  const [enablingPack, setEnablingPack] = useState<string | null>(null);
  const [disablingPack, setDisablingPack] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API}/packs/index`)
      .then((r) => r.json())
      .then(setIndex)
      .catch((e: unknown) => { console.warn("[fetch error]", e); });
  }, []);

  useEffect(() => {
    if (logEndRef.current) logEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [progressLog]);

  function addLog(msg: string) {
    setProgressLog((prev) => [...prev, `${new Date().toLocaleTimeString()} — ${msg}`]);
  }

  async function loadTenantStatus(tid: string) {
    if (!tid) return;
    setLoadingStatus(true);
    setTenantStatus(null);
    try {
      const r = await fetch(`${API}/tenants/${tid}/status`);
      const data = await r.json();
      setTenantStatus(data);
    } catch {
      setTenantStatus(null);
    } finally {
      setLoadingStatus(false);
    }
  }

  async function applySet(set: RecommendedSet) {
    setConfirmSet(null);
    setApplying(set.set_id);
    setProgressLog([]);
    addLog(`Applying pack set: ${set.label}`);

    for (const packId of set.pack_ids) {
      addLog(`Ingesting ${packId}…`);
      await fetch(`${API}/packs/${packId}/ingest`, { method: "POST" }).catch((e: unknown) => { console.warn("[fetch error]", e); });
      addLog(`${packId} ingested`);
    }

    addLog(`Activating packs on tenant ${tenantId}…`);
    const r = await fetch(`${API}/tenants/${tenantId}/apply-pack-set`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ set_id: set.set_id }),
    });
    const result = await r.json();
    addLog(`Done — ${result.packs_applied?.length ?? 0} packs active`);
    addLog("compliance.tenant.packset.applied");
    setApplying(null);
    await loadTenantStatus(tenantId);
  }

  async function enablePack(packId: string) {
    setEnablingPack(packId);
    addLog(`Enabling ${packId}…`);
    await fetch(`${API}/tenants/${tenantId}/enable-pack`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pack_id: packId }),
    });
    addLog(`${packId} enabled`);
    setEnablingPack(null);
    await loadTenantStatus(tenantId);
  }

  async function disablePack(packId: string) {
    setDisablingPack(packId);
    addLog(`Disabling ${packId}…`);
    await fetch(`${API}/tenants/${tenantId}/disable-pack`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pack_id: packId }),
    });
    addLog(`${packId} disabled`);
    setDisablingPack(null);
    await loadTenantStatus(tenantId);
  }

  const activePacks = new Set(tenantStatus?.active_pack_ids ?? []);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-xl font-bold text-white">Compliance Pack Index</h1>
        <p className="text-sm text-gray-400 mt-0.5">Apply compliance packs to tenants with one click — DEA, CAAS, CAMTS, Trans 309, Hospital</p>
      </div>

      <div className="p-6 space-y-8 max-w-6xl">
        {/* Tenant Selector */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <h2 className="text-sm font-semibold text-gray-200 mb-3">Tenant Selector</h2>
          <div className="flex gap-3">
            <input
              className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-gray-100 placeholder-gray-500 font-mono"
              placeholder="Tenant UUID"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") loadTenantStatus(tenantId); }}
            />
            <button
              onClick={() => loadTenantStatus(tenantId)}
              disabled={!tenantId || loadingStatus}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded text-sm font-medium transition-colors"
            >
              {loadingStatus ? "Loading…" : "Load Status"}
            </button>
          </div>

          {tenantStatus && (
            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="rounded-lg bg-gray-800 p-3">
                <p className="text-xs text-gray-400">Active Packs</p>
                <p className="text-xl font-bold text-white">{tenantStatus.active_pack_ids.length}</p>
              </div>
              <div className="rounded-lg bg-gray-800 p-3">
                <p className="text-xs text-gray-400">Fleet Score</p>
                <p className="text-xl font-bold text-white">{tenantStatus.fleet_score !== null ? `${tenantStatus.fleet_score}%` : "—"}</p>
              </div>
              <div className="rounded-lg bg-gray-800 p-3">
                <p className="text-xs text-gray-400">Inspections</p>
                <p className="text-xl font-bold text-white">{tenantStatus.inspections_total}</p>
              </div>
              <div className="rounded-lg bg-gray-800 p-3">
                <p className="text-xs text-gray-400">Active Set</p>
                <p className="text-sm font-semibold text-emerald-400 truncate">{tenantStatus.active_set_id ?? "—"}</p>
              </div>
            </div>
          )}
        </div>

        {/* Recommended Sets */}
        <div>
          <h2 className="text-base font-semibold text-gray-200 mb-3">Recommended Sets</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {index?.recommended_sets.map((set) => {
              const isActive = tenantStatus?.active_set_id === set.set_id;
              const isApplying = applying === set.set_id;
              return (
                <div
                  key={set.set_id}
                  className={`rounded-xl border p-5 transition-colors ${
                    isActive ? "border-emerald-700 bg-emerald-900/10" : "border-gray-800 bg-gray-900"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-gray-700 flex items-center justify-center text-xs font-bold text-gray-300">
                        {SET_ICONS[set.set_id] ?? "SET"}
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-white">{set.label}</p>
                        <p className="text-xs text-gray-400 mt-0.5">{set.description}</p>
                      </div>
                    </div>
                    {isActive ? (
                      <span className="flex-shrink-0 px-2 py-1 bg-emerald-800/50 text-emerald-400 text-xs rounded font-medium">Active</span>
                    ) : (
                      <button
                        onClick={() => setConfirmSet(set)}
                        disabled={!tenantId || isApplying || !!applying}
                        className="flex-shrink-0 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded text-xs font-semibold transition-colors"
                      >
                        {isApplying ? "Applying…" : "Apply"}
                      </button>
                    )}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {set.pack_ids.map((pid) => (
                      <span
                        key={pid}
                        className={`px-2 py-0.5 rounded text-xs border ${
                          activePacks.has(pid) ? "bg-emerald-900/30 text-emerald-400 border-emerald-800" : "bg-gray-800 text-gray-400 border-gray-700"
                        }`}
                      >
                        {pid}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* All Packs Table */}
        <div>
          <h2 className="text-base font-semibold text-gray-200 mb-3">All Packs</h2>
          <div className="rounded-xl border border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 text-gray-400 text-xs">
                <tr>
                  <th className="px-4 py-2.5 text-left">Pack</th>
                  <th className="px-4 py-2.5 text-left">Jurisdiction</th>
                  <th className="px-4 py-2.5 text-left">Status</th>
                  <th className="px-4 py-2.5 text-left">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {index?.packs.map((pack) => {
                  const isActive = activePacks.has(pack.pack_id);
                  const isEnabling = enablingPack === pack.pack_id;
                  const isDisabling = disablingPack === pack.pack_id;
                  return (
                    <tr key={pack.pack_id} className="hover:bg-gray-800/50">
                      <td className="px-4 py-3">
                        <p className="font-medium text-gray-200">{pack.name}</p>
                        <p className="text-xs text-gray-500 font-mono mt-0.5">{pack.pack_id}</p>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs border ${JURISDICTION_COLORS[pack.jurisdiction] ?? "bg-gray-700 text-gray-400 border-gray-600"}`}>
                          {pack.jurisdiction}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {isActive ? (
                          <span className="px-2 py-0.5 bg-emerald-900/40 text-emerald-400 rounded text-xs">Active</span>
                        ) : tenantStatus ? (
                          <span className="px-2 py-0.5 bg-gray-700 text-gray-400 rounded text-xs">Inactive</span>
                        ) : (
                          <span className="text-gray-600 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {tenantId && (
                          <div className="flex gap-2">
                            {!isActive ? (
                              <button
                                onClick={() => enablePack(pack.pack_id)}
                                disabled={isEnabling || !!applying}
                                className="px-3 py-1 bg-emerald-800 hover:bg-emerald-700 disabled:opacity-40 rounded text-xs transition-colors"
                              >
                                {isEnabling ? "Enabling…" : "Enable"}
                              </button>
                            ) : (
                              <button
                                onClick={() => disablePack(pack.pack_id)}
                                disabled={isDisabling || !!applying}
                                className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-40 rounded text-xs transition-colors"
                              >
                                {isDisabling ? "Disabling…" : "Disable"}
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {!index?.packs.length && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-gray-500 text-sm">
                      Loading pack index…
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Active Packs Detail */}
        {tenantStatus?.active_packs && tenantStatus.active_packs.length > 0 && (
          <div>
            <h2 className="text-base font-semibold text-gray-200 mb-3">Tenant Active Packs</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {tenantStatus.active_packs.map((p) => (
                <div key={p.pack_id} className="rounded-lg border border-emerald-800 bg-emerald-900/10 p-3">
                  <p className="text-sm font-medium text-emerald-300">{p.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{p.jurisdiction} · {p.status}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Progress Log */}
        {progressLog.length > 0 && (
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-200">Activity Log</h3>
              {!applying && (
                <button onClick={() => setProgressLog([])} className="text-xs text-gray-500 hover:text-gray-300">Clear</button>
              )}
            </div>
            <div className="font-mono text-xs space-y-1 max-h-40 overflow-y-auto">
              {progressLog.map((line, i) => (
                <p key={i} className={line.includes("Done") || line.includes("enabled") || line.includes("applied") ? "text-emerald-400" : line.includes("Ingesting") || line.includes("Activating") || line.includes("Enabling") ? "text-blue-400" : "text-gray-400"}>
                  {line}
                </p>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        )}
      </div>

      {/* Confirm Modal */}
      {confirmSet && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-2">Apply Pack Set</h3>
            <p className="text-sm text-gray-300 mb-4">
              Apply <span className="text-blue-400 font-semibold">{confirmSet.label}</span> to tenant{" "}
              <span className="font-mono text-gray-200">{tenantId}</span>?
            </p>
            <div className="mb-4">
              <p className="text-xs text-gray-400 mb-2">Packs included:</p>
              <div className="space-y-1">
                {confirmSet.pack_ids.map((pid) => (
                  <div key={pid} className="flex items-center gap-2 text-xs">
                    <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                    <span className="text-gray-200">{pid}</span>
                    {activePacks.has(pid) && <span className="text-emerald-400">(already active)</span>}
                  </div>
                ))}
              </div>
            </div>
            <p className="text-xs text-amber-400 mb-4">This will ingest missing packs and activate them immediately.</p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmSet(null)}
                className="flex-1 py-2 border border-gray-700 rounded-lg text-sm text-gray-300 hover:bg-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => applySet(confirmSet)}
                className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-semibold transition-colors"
              >
                Apply Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
