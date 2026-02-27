"use client";
import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";

const API = "/api/v1/kitlink/compliance";
const KITLINK_API = "/api/v1/kitlink";

const MANDATORY_ITEMS = [
  { id: "FIRE_EXT_1", label: "Fire Extinguisher #1" },
  { id: "FIRE_EXT_2", label: "Fire Extinguisher #2" },
  { id: "LIGHTS", label: "Emergency Lights" },
  { id: "O2", label: "Oxygen System" },
  { id: "SUCTION", label: "Suction Unit" },
  { id: "AED", label: "AED" },
  { id: "SPINE_BOARD", label: "Spine Board" },
  { id: "JUMP_BAG", label: "Jump Bag" },
  { id: "NARC_BOX", label: "Narcotics Box" },
  { id: "DRUG_BOX", label: "Drug Box" },
];

type CheckValue = boolean | "fail" | null;

interface Responses {
  EXPIRATION_SWEEP: CheckValue;
  NARC_SEAL_INTACT: CheckValue;
  [key: string]: CheckValue;
}

export default function InspectionPage() {
  const params = useSearchParams();
  const tenantId = params.get("tenant_id") ?? "";

  const [unitId, setUnitId] = useState("");
  const [unitProfile, setUnitProfile] = useState("PARAMEDIC");
  const [packKey, setPackKey] = useState("WI_TRANS_309_V2");
  const [inspectionId, setInspectionId] = useState<string | null>(null);
  const [responses, setResponses] = useState<Responses>({
    EXPIRATION_SWEEP: null,
    NARC_SEAL_INTACT: null,
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [phase, setPhase] = useState<"setup" | "checklist" | "result">("setup");

  async function startInspection() {
    const r = await fetch(`${API}/inspections?tenant_id=${tenantId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ unit_id: unitId, unit_profile: unitProfile, pack_key: packKey }),
    });
    const data = await r.json();
    setInspectionId(data.id);
    const init: Responses = { EXPIRATION_SWEEP: null, NARC_SEAL_INTACT: null };
    for (const item of MANDATORY_ITEMS) {
      init[item.id] = null;
    }
    setResponses(init);
    setPhase("checklist");
  }

  async function submitInspection() {
    if (!inspectionId) return;
    setSubmitting(true);
    const r = await fetch(`${API}/inspections/${inspectionId}/submit?tenant_id=${tenantId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ responses }),
    });
    const data = await r.json();
    setResult(data);
    setPhase("result");
    setSubmitting(false);
  }

  function setCheck(key: string, value: boolean) {
    setResponses((prev) => ({ ...prev, [key]: value }));
  }

  const allAnswered = Object.values(responses).every((v) => v !== null);

  if (phase === "setup") {
    return (
      <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="mb-6 text-center">
            <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center text-lg font-bold mx-auto mb-3">309</div>
            <h1 className="text-xl font-bold text-white">Trans 309 Inspection</h1>
            <p className="text-sm text-gray-400 mt-1">Wisconsin DOT Compliance Mode</p>
          </div>

          <div className="rounded-xl border border-gray-800 bg-gray-900 p-5 space-y-4">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Unit ID</label>
              <input
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-gray-100 placeholder-gray-500"
                placeholder="e.g. M12"
                value={unitId}
                onChange={(e) => setUnitId(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Unit Profile</label>
              <select
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-gray-100"
                value={unitProfile}
                onChange={(e) => setUnitProfile(e.target.value)}
              >
                <option>EMT</option>
                <option>AEMT</option>
                <option>PARAMEDIC</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Compliance Pack</label>
              <select
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-gray-100"
                value={packKey}
                onChange={(e) => setPackKey(e.target.value)}
              >
                <option value="WI_TRANS_309_V1">WI Trans 309 v1</option>
                <option value="WI_TRANS_309_V2">WI Trans 309 v2 (current)</option>
              </select>
            </div>
            <button
              onClick={startInspection}
              disabled={!unitId}
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-sm font-semibold transition-colors"
            >
              Start Inspection
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (phase === "checklist") {
    return (
      <div className="min-h-screen bg-gray-950 text-gray-100 p-4 max-w-lg mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => setPhase("setup")} className="text-gray-400 hover:text-gray-200 text-sm">← Back</button>
          <div>
            <h1 className="text-lg font-bold text-white">Unit {unitId} — {unitProfile}</h1>
            <p className="text-xs text-gray-400">{packKey} · Inspection ID: {inspectionId?.slice(0, 8)}…</p>
          </div>
        </div>

        <div className="space-y-3">
          <CheckRow
            label="Expiration Sweep"
            sublabel="No expired medications or IV fluids on unit"
            id="EXPIRATION_SWEEP"
            value={responses.EXPIRATION_SWEEP}
            hardFail
            onChange={(v) => setCheck("EXPIRATION_SWEEP", v)}
          />

          <CheckRow
            label="Narcotics Seal Intact"
            sublabel="Seal verified — code matches record"
            id="NARC_SEAL_INTACT"
            value={responses.NARC_SEAL_INTACT}
            onChange={(v) => setCheck("NARC_SEAL_INTACT", v)}
          />

          <div className="pt-2 pb-1">
            <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">Mandatory Equipment (10 items)</p>
          </div>

          {MANDATORY_ITEMS.map((item) => (
            <CheckRow
              key={item.id}
              label={item.label}
              id={item.id}
              value={responses[item.id]}
              onChange={(v) => setCheck(item.id, v)}
            />
          ))}
        </div>

        <div className="mt-6 pb-8">
          <button
            onClick={submitInspection}
            disabled={!allAnswered || submitting}
            className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded-xl text-sm font-semibold transition-colors"
          >
            {submitting ? "Submitting…" : allAnswered ? "Submit Inspection" : `Answer all items (${Object.values(responses).filter((v) => v !== null).length}/${Object.keys(responses).length})`}
          </button>
        </div>
      </div>
    );
  }

  if (phase === "result" && result) {
    const passed = result.result_status === "pass" || result.result_status === "pass_with_warnings";
    return (
      <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className={`rounded-xl border p-6 text-center ${passed ? "border-emerald-700 bg-emerald-900/20" : "border-red-700 bg-red-900/20"}`}>
            <div className={`text-5xl mb-3 ${passed ? "text-emerald-400" : "text-red-400"}`}>
              {passed ? "✓" : "✗"}
            </div>
            <h2 className="text-xl font-bold text-white mb-1">
              {result.result_status === "pass" ? "PASS" : result.result_status === "pass_with_warnings" ? "PASS WITH WARNINGS" : "FAIL"}
            </h2>
            {result.hard_fail && (
              <p className="text-sm text-red-400 mb-3">HARD FAIL — Expired medications or fluids found</p>
            )}
            <p className="text-sm text-gray-400">Unit {unitId} · {new Date().toLocaleDateString()}</p>

            {result.findings?.length > 0 && (
              <div className="mt-4 text-left space-y-2">
                <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">Findings ({result.findings.length})</p>
                {result.findings.map((f: any) => (
                  <div key={f.id} className="flex items-start gap-2 text-xs">
                    <span className="mt-0.5 text-red-400">●</span>
                    <span className="text-gray-300">{f.rule_id}</span>
                  </div>
                ))}
              </div>
            )}

            {result.warnings?.length > 0 && (
              <div className="mt-3 text-left space-y-2">
                <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">Warnings ({result.warnings.length})</p>
                {result.warnings.map((w: any) => (
                  <div key={w.id} className="flex items-start gap-2 text-xs">
                    <span className="mt-0.5 text-amber-400">●</span>
                    <span className="text-gray-300">{w.rule_id}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-5 grid grid-cols-2 gap-3">
              <button
                onClick={() => { setPhase("setup"); setResult(null); setInspectionId(null); }}
                className="py-2 border border-gray-700 rounded-lg text-sm text-gray-300 hover:bg-gray-800 transition-colors"
              >
                New Inspection
              </button>
              <button
                className="py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition-colors"
                onClick={() => window.print()}
              >
                Print Report
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

function CheckRow({
  label, sublabel, id, value, hardFail = false, onChange,
}: {
  label: string;
  sublabel?: string;
  id: string;
  value: CheckValue;
  hardFail?: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className={`rounded-lg border p-3 ${value === null ? "border-gray-800 bg-gray-900" : value === true ? "border-emerald-800 bg-emerald-900/20" : "border-red-800 bg-red-900/20"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <p className="text-sm text-gray-200 font-medium">
            {label}
            {hardFail && <span className="ml-2 text-xs text-red-400 font-normal">hard fail if NO</span>}
          </p>
          {sublabel && <p className="text-xs text-gray-500 mt-0.5">{sublabel}</p>}
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <button
            onClick={() => onChange(true)}
            className={`w-12 py-1 rounded text-xs font-semibold transition-colors ${value === true ? "bg-emerald-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-emerald-900/40 hover:text-emerald-400"}`}
          >
            YES
          </button>
          <button
            onClick={() => onChange(false)}
            className={`w-12 py-1 rounded text-xs font-semibold transition-colors ${value === false ? "bg-red-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-red-900/40 hover:text-red-400"}`}
          >
            NO
          </button>
        </div>
      </div>
    </div>
  );
}
