"use client";
import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";

const COMPLIANCE_API = "/api/v1/kitlink/compliance";
const KITLINK_API = "/api/v1/kitlink";

const STEPS = [
  {
    id: "choose_compliance_pack",
    title: "Choose Compliance Pack",
    description: "Select and activate a Trans 309 compliance pack for Wisconsin.",
  },
  {
    id: "unit_setup",
    title: "Unit Setup",
    description: "Configure your ambulance unit profile (EMT / AEMT / Paramedic).",
  },
  {
    id: "formulary_quick_setup",
    title: "Formulary Quick Setup",
    description: "Add your medications and IV fluids to the formulary.",
  },
  {
    id: "load_starter_templates",
    title: "Load Starter Templates",
    description: "Clone preconfigured kit templates (Narc Box, Airway, Trauma, IV).",
  },
  {
    id: "create_unit_layout",
    title: "Create Unit Layout",
    description: "Define which kits belong to your unit and in what order.",
  },
  {
    id: "generate_marker_sheets",
    title: "Generate Marker Sheets",
    description: "Create QR code AR markers for each kit on your unit.",
  },
  {
    id: "test_scan",
    title: "Test Scan",
    description: "Verify that marker scan → resolve works correctly.",
  },
  {
    id: "enable_inspection_mode",
    title: "Enable Trans 309 Inspection Mode",
    description: "Activate DOT-ready inspection mode for the compliance pack.",
  },
  {
    id: "go_live",
    title: "Go-Live Checklist",
    description: "Final review — confirm all 9 steps complete. You're live!",
  },
] as const;

type StepId = typeof STEPS[number]["id"];

export default function WizardPage() {
  const params = useSearchParams();
  const router = useRouter();
  const tenantId = params.get("tenant_id") ?? "";

  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<StepId[]>([]);
  const [loading, setLoading] = useState(true);
  const [stepData, setStepData] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState(false);
  const [wizardError, setWizardError] = useState('');

  useEffect(() => {
    if (!tenantId) return;
    fetch(`${COMPLIANCE_API}/wizard/state?tenant_id=${tenantId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.started) {
          setCompletedSteps(data.steps_completed ?? []);
          const nextIdx = STEPS.findIndex((s) => s.id === data.next_step);
          if (nextIdx >= 0) setCurrentStep(nextIdx);
        }
      })
      .catch((e: unknown) => { console.warn('[wizard state error]', e); })
      .finally(() => setLoading(false));
  }, [tenantId]);

  async function completeStep(stepId: StepId, data?: object) {
    setSubmitting(true);
    setWizardError('');
    try {
    await fetch(`${COMPLIANCE_API}/wizard/step?tenant_id=${tenantId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ step: stepId, data: data ?? {} }),
    });
    setCompletedSteps((prev) => (prev.includes(stepId) ? prev : [...prev, stepId]));
    if (currentStep < STEPS.length - 1) setCurrentStep(currentStep + 1);
    } catch (e: unknown) { setWizardError(e instanceof Error ? e.message : 'Step failed'); }
    setSubmitting(false);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-gray-400 text-sm">Loading wizard state…</p>
      </div>
    );
  }

  const goLiveComplete = completedSteps.length === STEPS.length;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="border-b border-gray-800 px-6 py-4 flex items-center gap-3">
        <button onClick={() => router.back()} className="text-gray-400 hover:text-gray-200 text-sm">← Back</button>
        <div className="flex-1">
          <h1 className="text-lg font-bold text-white">1-Day Go-Live Wizard</h1>
          <p className="text-xs text-gray-400">KitLink AR · Trans 309 · Wisconsin</p>
        </div>
        <div className="text-sm text-gray-400">
          {completedSteps.length}/{STEPS.length} steps
        </div>
      </div>

      {goLiveComplete && (
        <div className="mx-6 mt-4 p-4 rounded-lg border border-emerald-700 bg-emerald-900/20 flex items-center gap-3">
          <span className="text-emerald-400 text-xl">✓</span>
          <div>
            <p className="text-sm font-semibold text-emerald-300">Setup Complete — You're Live!</p>
            <p className="text-xs text-emerald-600 mt-0.5">All 9 steps completed. KitLink AR is fully configured.</p>
          </div>
          <a
            href={`/portal/kitlink?tenant_id=${tenantId}`}
            className="ml-auto px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 rounded text-xs font-medium transition-colors"
          >
            Open KitLink
          </a>
        </div>
      )}

      <div className="flex flex-col md:flex-row h-full">
        <div className="w-full md:w-64 border-r border-gray-800 p-4">
          <nav className="space-y-1">
            {STEPS.map((step, idx) => {
              const done = completedSteps.includes(step.id);
              const active = idx === currentStep && !goLiveComplete;
              return (
                <button
                  key={step.id}
                  onClick={() => setCurrentStep(idx)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors text-sm ${
                    active ? "bg-blue-900/40 text-blue-300" : done ? "text-emerald-400 hover:bg-gray-800" : "text-gray-400 hover:bg-gray-800"
                  }`}
                >
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${done ? "bg-emerald-700 text-white" : active ? "bg-blue-700 text-white" : "bg-gray-700 text-gray-400"}`}>
                    {done ? "✓" : idx + 1}
                  </span>
                  <span className="truncate">{step.title}</span>
                </button>
              );
            })}
          </nav>
        </div>

        <div className="flex-1 p-6">
          <StepPanel
            step={STEPS[currentStep]}
            tenantId={tenantId}
            completed={completedSteps.includes(STEPS[currentStep].id)}
            submitting={submitting}
            stepData={stepData}
            setStepData={(d) => setStepData((prev) => ({ ...prev, [STEPS[currentStep].id]: d }))}
            onComplete={(data) => completeStep(STEPS[currentStep].id, data)}
          />
        </div>
      </div>
    </div>
  );
}

function StepPanel({
  step, tenantId, completed, submitting, stepData, setStepData, onComplete,
}: {
  step: typeof STEPS[number];
  tenantId: string;
  completed: boolean;
  submitting: boolean;
  stepData: any;
  setStepData: (d: any) => void;
  onComplete: (data?: object) => void;
}) {
  return (
    <div className="max-w-xl">
      <div className="flex items-start gap-3 mb-5">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${completed ? "bg-emerald-700" : "bg-blue-700"}`}>
          {completed ? "✓" : "→"}
        </div>
        <div>
          <h2 className="text-lg font-bold text-white">{step.title}</h2>
          <p className="text-sm text-gray-400 mt-0.5">{step.description}</p>
        </div>
      </div>

      {step.id === "choose_compliance_pack" && (
        <PackStep tenantId={tenantId} stepData={stepData} setStepData={setStepData} />
      )}
      {step.id === "unit_setup" && (
        <UnitSetupStep stepData={stepData} setStepData={setStepData} />
      )}
      {step.id === "formulary_quick_setup" && (
        <FormularyStep tenantId={tenantId} stepData={stepData} setStepData={setStepData} />
      )}
      {step.id === "load_starter_templates" && (
        <StarterTemplatesStep tenantId={tenantId} stepData={stepData} setStepData={setStepData} />
      )}
      {["create_unit_layout", "generate_marker_sheets", "test_scan", "enable_inspection_mode", "go_live"].includes(step.id) && (
        <GenericStep step={step} />
      )}

      <button
        onClick={() => onComplete(stepData)}
        disabled={submitting}
        className={`mt-5 px-6 py-2.5 rounded-lg text-sm font-semibold transition-colors ${
          completed
            ? "bg-emerald-700/40 text-emerald-400 border border-emerald-700"
            : "bg-blue-600 hover:bg-blue-500 text-white"
        } disabled:opacity-50`}
      >
        {submitting ? "Saving…" : completed ? "Step Completed — Continue" : "Mark Complete & Continue"}
      </button>
    </div>
  );
}

function PackStep({ tenantId, stepData, setStepData }: { tenantId: string; stepData: any; setStepData: (d: any) => void }) {
  const [packs, setPacks] = useState<any[]>([]);
  const [activating, setActivating] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${COMPLIANCE_API}/packs?tenant_id=${tenantId}`)
      .then((r) => r.json())
      .then((d) => setPacks(d.packs ?? []))
      .catch((e: unknown) => { console.warn('[packs fetch error]', e); });
  }, [tenantId]);

  async function activate(packKey: string) {
    setActivating(packKey);
    try {
      await fetch(`${COMPLIANCE_API}/packs/activate?tenant_id=${tenantId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pack_key: packKey, unit_profile: stepData?.unit_profile ?? "PARAMEDIC" }),
      });
      setPacks((prev) => prev.map((p) => ({ ...p, active: p.pack_key === packKey ? true : p.active })));
      setStepData({ ...stepData, pack_key: packKey });
    } catch (err: unknown) {
      console.warn("[wizard]", err);
    }
    setActivating(null);
  }

  return (
    <div className="space-y-3">
      {packs.map((pack) => (
        <div key={pack.pack_key} className={`rounded-lg border p-4 ${pack.active ? "border-emerald-700 bg-emerald-900/20" : "border-gray-800 bg-gray-900"}`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-gray-200">{pack.title}</p>
              <p className="text-xs text-gray-500 mt-0.5">{pack.state} · v{pack.version} · {pack.unit_profiles?.join(", ")}</p>
              <p className="text-xs text-gray-500 mt-1">{pack.rules?.length ?? 0} rules</p>
            </div>
            {pack.active ? (
              <span className="px-2 py-1 bg-emerald-800/50 text-emerald-400 text-xs rounded">Active</span>
            ) : (
              <button
                onClick={() => activate(pack.pack_key)}
                disabled={activating === pack.pack_key}
                className="px-3 py-1.5 bg-blue-700 hover:bg-blue-600 rounded text-xs font-medium transition-colors"
              >
                {activating === pack.pack_key ? "Activating…" : "Activate"}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function UnitSetupStep({ stepData, setStepData }: { stepData: any; setStepData: (d: any) => void }) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-gray-400 block mb-1">Unit ID</label>
        <input
          className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-gray-100 placeholder-gray-500"
          placeholder="e.g. M12"
          value={stepData?.unit_id ?? ""}
          onChange={(e) => setStepData({ ...stepData, unit_id: e.target.value })}
        />
      </div>
      <div>
        <label className="text-xs text-gray-400 block mb-1">Unit Profile</label>
        <select
          className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-gray-100"
          value={stepData?.unit_profile ?? "PARAMEDIC"}
          onChange={(e) => setStepData({ ...stepData, unit_profile: e.target.value })}
        >
          <option>EMT</option>
          <option>AEMT</option>
          <option>PARAMEDIC</option>
        </select>
      </div>
    </div>
  );
}

function FormularyStep({ tenantId, stepData, setStepData }: { tenantId: string; stepData: any; setStepData: (d: any) => void }) {
  const [form, setForm] = useState({ name: "", controlled_schedule: "", unit: "vial", is_fluid: false });
  const [added, setAdded] = useState<string[]>([]);

  async function addItem() {
    try {
      await fetch(`${KITLINK_API}/formulary?tenant_id=${tenantId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      setAdded((prev) => [...prev, form.name]);
      setForm({ name: "", controlled_schedule: "", unit: "vial", is_fluid: false });
    } catch (err: unknown) {
      console.warn("[wizard]", err);
    }
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <input
          className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-gray-100 placeholder-gray-500"
          placeholder="Drug/fluid name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <input
          className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-gray-100 placeholder-gray-500"
          placeholder="Schedule (II, III, IV, V)"
          value={form.controlled_schedule}
          onChange={(e) => setForm({ ...form, controlled_schedule: e.target.value })}
        />
      </div>
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={form.is_fluid} onChange={(e) => setForm({ ...form, is_fluid: e.target.checked })} className="rounded" />
          IV Fluid
        </label>
        <button
          onClick={addItem}
          disabled={!form.name}
          className="px-4 py-1.5 bg-blue-700 hover:bg-blue-600 disabled:opacity-50 rounded text-xs font-medium transition-colors"
        >
          Add to Formulary
        </button>
      </div>
      {added.length > 0 && (
        <div className="p-3 bg-gray-900 rounded border border-gray-800">
          <p className="text-xs text-gray-400 mb-1">Added:</p>
          <div className="flex flex-wrap gap-2">
            {added.map((n) => (
              <span key={n} className="px-2 py-0.5 bg-gray-700 text-gray-300 rounded text-xs">{n}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StarterTemplatesStep({ tenantId, stepData, setStepData }: { tenantId: string; stepData: any; setStepData: (d: any) => void }) {
  const [loading, setLoading] = useState<string | null>(null);
  const [cloned, setCloned] = useState<string[]>([]);
  const starters = [
    { key: "NARC_BOX_V1", label: "Narc Box", desc: "Controlled substances, seals, witness forms" },
    { key: "AIRWAY_KIT_V1", label: "Airway Kit", desc: "BVM, supraglottic airways, intubation" },
    { key: "TRAUMA_KIT_V1", label: "Trauma Kit", desc: "Hemorrhage control, burns, splinting" },
    { key: "IV_KIT_V1", label: "IV / Fluid Kit", desc: "IV access, fluids, tubing" },
  ];

  async function clone(key: string) {
    setLoading(key);
    try {
      await fetch(`${KITLINK_API}/kits/starter/${key}/clone?tenant_id=${tenantId}`, { method: "POST" });
      setCloned((prev) => [...prev, key]);
    } catch (err: unknown) {
      console.warn("[wizard]", err);
    }
    setLoading(null);
  }

  return (
    <div className="space-y-3">
      {starters.map((s) => (
        <div key={s.key} className={`rounded-lg border p-3 flex items-center justify-between gap-3 ${cloned.includes(s.key) ? "border-emerald-800 bg-emerald-900/10" : "border-gray-800 bg-gray-900"}`}>
          <div>
            <p className="text-sm font-medium text-gray-200">{s.label}</p>
            <p className="text-xs text-gray-500">{s.desc}</p>
          </div>
          {cloned.includes(s.key) ? (
            <span className="text-xs text-emerald-400">Loaded</span>
          ) : (
            <button
              onClick={() => clone(s.key)}
              disabled={loading === s.key}
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-xs font-medium transition-colors"
            >
              {loading === s.key ? "Loading…" : "Load"}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function GenericStep({ step }: { step: typeof STEPS[number] }) {
  const hints: Record<string, string> = {
    create_unit_layout: "Go to Unit Layouts tab → create a layout → assign kit templates → publish.",
    generate_marker_sheets: "Go to AR Markers tab → generate a marker for each kit → mark as printed.",
    test_scan: "Use AR Markers tab → Test Marker Resolve → enter a marker code to verify the resolve flow.",
    enable_inspection_mode: "Open Trans 309 Inspection Mode and run a test inspection on your unit.",
    go_live: "All steps complete! Your KitLink setup is verified. Crew can now start scanning.",
  };
  return (
    <div className="p-4 rounded-lg border border-gray-800 bg-gray-900/50 text-sm text-gray-300">
      {hints[step.id] ?? "Complete this step in the KitLink dashboard."}
    </div>
  );
}
