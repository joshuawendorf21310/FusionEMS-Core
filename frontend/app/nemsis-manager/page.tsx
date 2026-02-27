"use client";

import { useState, useEffect, useCallback } from "react";
import * as Tabs from "@radix-ui/react-tabs";

const BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type SchemaElement = {
  label: string;
  required: boolean;
  type: string;
  section: string;
  phi?: boolean;
};

type SchemaOverview = {
  version: string;
  total_elements: number;
  required_count: number;
  sections: string[];
  schema: Record<string, SchemaElement>;
};

type ReadinessScore = {
  state: string;
  completeness_pct: number;
  required_count: number;
  provided_required: number;
  missing_required: number;
  ready_for_submission: boolean;
  score_label: string;
};

type ValidationResult = {
  valid: boolean;
  errors: string[];
  warnings: string[];
  missing_required?: string[];
  completeness_pct?: number;
};

type ExportDashboard = {
  total_jobs: number;
  total_batches: number;
  total_rejections: number;
  jobs_by_status: Record<string, number>;
  pending_batches: number;
};

type CertificationReadiness = {
  certification_ready: boolean;
  checks_passed: number;
  total_checks: number;
  checks: Array<{ check: string; passed: boolean }>;
};

type IntegrityScore = {
  integrity_score: number;
  grade: string;
  valid_count: number;
  total: number;
};

type HierarchyData = {
  hierarchy: Record<string, Array<{ id: string; label: string; required: boolean; type: string }>>;
  sections: string[];
};

type ExportBatch = {
  id: string;
  data: { batch_size?: number; status?: string; state_code?: string };
};

type StateRejection = {
  id: string;
  data: { state_code?: string; rejection_reason?: string; resolved?: boolean };
};

type SchemaDiff = {
  version_a: string;
  version_b: string;
  diff: Array<{ element: string; status: string; change_detail?: string; notes?: string }>;
  total_changes: number;
};

type UpgradeImpact = {
  from_version: string;
  to_version: string;
  breaking_changes: Array<{ element: string; change: string }>;
  impacted_records: number;
  migration_required: boolean;
};

type ValidationHistoryItem = {
  id: string;
  data: { valid?: boolean; validation_type?: string; errors?: string[] };
};

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "green" | "red" | "yellow";
}) {
  const accents = { green: "text-green-400", red: "text-red-400", yellow: "text-yellow-400" };
  return (
    <div className="rounded-xl border border-border bg-panel p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-bold ${accent ? accents[accent] : ""}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-muted">{sub}</div>}
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return (
    <div className="text-sm font-semibold text-muted uppercase tracking-wide mb-3">{title}</div>
  );
}

function Badge({ color, label }: { color: string; label: string }) {
  const colors: Record<string, string> = {
    green: "bg-green-900/40 text-green-300 border-green-700",
    red: "bg-red-900/40 text-red-300 border-red-700",
    yellow: "bg-yellow-900/40 text-yellow-300 border-yellow-700",
    blue: "bg-blue-900/40 text-blue-300 border-blue-700",
    gray: "bg-gray-800 text-gray-300 border-gray-600",
  };
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs border font-medium ${
        colors[color] ?? colors.gray
      }`}
    >
      {label}
    </span>
  );
}

function ValidationResultDisplay({ result }: { result: ValidationResult }) {
  return (
    <div
      className={`rounded-lg border p-4 ${
        result.valid ? "border-green-700 bg-green-900/20" : "border-red-700 bg-red-900/20"
      }`}
    >
      <div
        className={`font-semibold text-sm ${result.valid ? "text-green-300" : "text-red-300"}`}
      >
        {result.valid ? "VALID" : "INVALID"}{" "}
        {result.completeness_pct !== undefined && `(${result.completeness_pct}% complete)`}
      </div>
      {result.errors.length > 0 && (
        <div className="mt-2">
          <div className="text-xs font-semibold text-red-300 mb-1">
            Errors ({result.errors.length})
          </div>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {result.errors.map((e, i) => (
              <div key={i} className="text-xs text-red-200">
                {e}
              </div>
            ))}
          </div>
        </div>
      )}
      {result.missing_required && result.missing_required.length > 0 && (
        <div className="mt-2">
          <div className="text-xs font-semibold text-yellow-300 mb-1">
            Missing Required ({result.missing_required.length})
          </div>
          <div className="flex flex-wrap gap-1">
            {result.missing_required.slice(0, 20).map((e) => (
              <span
                key={e}
                className="rounded bg-yellow-900/30 px-1.5 py-0.5 text-xs text-yellow-300"
              >
                {e}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function NEMSISManagerPage() {
  const [activeTab, setActiveTab] = useState("overview");
  const [schema, setSchema] = useState<SchemaOverview | null>(null);
  const [hierarchy, setHierarchy] = useState<HierarchyData | null>(null);
  const [exportDash, setExportDash] = useState<ExportDashboard | null>(null);
  const [certReadiness, setCertReadiness] = useState<CertificationReadiness | null>(null);
  const [integrityScore, setIntegrityScore] = useState<IntegrityScore | null>(null);
  const [schemaDiff, setSchemaDiff] = useState<SchemaDiff | null>(null);
  const [upgradeImpact, setUpgradeImpact] = useState<UpgradeImpact | null>(null);
  const [exportBatches, setExportBatches] = useState<ExportBatch[]>([]);
  const [rejections, setRejections] = useState<StateRejection[]>([]);
  const [validationHistory, setValidationHistory] = useState<ValidationHistoryItem[]>([]);

  const [readinessResult, setReadinessResult] = useState<ReadinessScore | null>(null);
  const [liveValidResult, setLiveValidResult] = useState<ValidationResult | null>(null);
  const [narrativeResult, setNarrativeResult] = useState<Record<string, unknown> | null>(null);
  const [medNecessityResult, setMedNecessityResult] = useState<Record<string, unknown> | null>(null);
  const [codingSuggestResult, setCodingSuggestResult] = useState<Record<string, unknown> | null>(null);
  const [normResult, setNormResult] = useState<Record<string, unknown> | null>(null);
  const [simResult, setSimResult] = useState<Record<string, unknown> | null>(null);
  const [fieldResult, setFieldResult] = useState<Record<string, unknown> | null>(null);
  const [autoPopResult, setAutoPopResult] = useState<Record<string, unknown> | null>(null);
  const [reportableFlagResult, setReportableFlagResult] = useState<Record<string, unknown> | null>(null);

  const [elementsInput, setElementsInput] = useState(
    "eRecord.01,eRecord.02,eRecord.03,eRecord.04,eTimes.01,eTimes.03,eTimes.05,eTimes.06,eTimes.09,eTimes.11,eTimes.13,ePatient.01,ePatient.02,ePatient.04,ePatient.05,ePatient.13"
  );
  const [stateCode, setStateCode] = useState("CA");
  const [narrativeInput, setNarrativeInput] = useState(
    "Patient presented with chest pain radiating to left arm. Initial assessment revealed altered mental status. Treatment included oxygen therapy and 12-lead ECG. Patient transported to St. Mary's Hospital."
  );
  const [fieldId, setFieldId] = useState("ePatient.04");
  const [fieldValue, setFieldValue] = useState("45");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedSection, setSelectedSection] = useState("all");

  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("access_token") || "demo-token"
      : "demo-token";
  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

  const api = useCallback(
    async (path: string, method = "GET", body?: unknown) => {
      try {
        const res = await fetch(`${BASE}${path}`, {
          method,
          headers,
          body: body ? JSON.stringify(body) : undefined,
        });
        if (!res.ok) return null;
        return res.json();
      } catch {
        return null;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const loadData = useCallback(async () => {
    const [s, h, ed, cr, is_, sd, ui, eb, rj, vh] = await Promise.all([
      api("/api/v1/nemsis-manager/schema"),
      api("/api/v1/nemsis-manager/schema/hierarchy"),
      api("/api/v1/nemsis-manager/export/dashboard"),
      api("/api/v1/nemsis-manager/certification-readiness"),
      api("/api/v1/nemsis-manager/integrity-score"),
      api("/api/v1/nemsis-manager/schema/diff"),
      api("/api/v1/nemsis-manager/upgrade-impact", "POST", {
        from_version: "3.4.0",
        to_version: "3.5.1",
      }),
      api("/api/v1/nemsis-manager/export/batches"),
      api("/api/v1/nemsis-manager/state-rejections"),
      api("/api/v1/nemsis-manager/audit-log"),
    ]);
    if (s) setSchema(s);
    if (h) setHierarchy(h);
    if (ed) setExportDash(ed);
    if (cr) setCertReadiness(cr);
    if (is_) setIntegrityScore(is_);
    if (sd) setSchemaDiff(sd);
    if (ui) setUpgradeImpact(ui);
    if (Array.isArray(eb)) setExportBatches(eb);
    if (Array.isArray(rj)) setRejections(rj);
    if (Array.isArray(vh)) setValidationHistory(vh);
  }, [api]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const runReadiness = async () => {
    const provided = elementsInput.split(",").map((e) => e.trim()).filter(Boolean);
    const res = await api("/api/v1/nemsis-manager/readiness-score", "POST", {
      provided_elements: provided,
      state_code: stateCode,
    });
    if (res) setReadinessResult(res);
  };

  const runLiveValidation = async () => {
    const provided = elementsInput.split(",").map((e) => e.trim()).filter(Boolean);
    const res = await api("/api/v1/nemsis-manager/validate/live", "POST", {
      provided_elements: provided,
    });
    if (res) setLiveValidResult(res);
  };

  const runNarrativeCheck = async () => {
    const res = await api("/api/v1/nemsis-manager/validate/narrative", "POST", {
      narrative: narrativeInput,
    });
    if (res) setNarrativeResult(res);
  };

  const runMedNecessity = async () => {
    const res = await api("/api/v1/nemsis-manager/validate/medical-necessity", "POST", {
      narrative: narrativeInput,
    });
    if (res) setMedNecessityResult(res);
  };

  const runCodingSuggest = async () => {
    const res = await api("/api/v1/nemsis-manager/coding-suggest", "POST", {
      narrative: narrativeInput,
    });
    if (res) setCodingSuggestResult(res);
  };

  const runFieldValidation = async () => {
    const res = await api("/api/v1/nemsis-manager/validate/field", "POST", {
      element_id: fieldId,
      value: fieldValue,
    });
    if (res) setFieldResult(res);
  };

  const runAutoPopulate = async () => {
    const res = await api("/api/v1/nemsis-manager/auto-populate", "POST", {
      incident: { state: "California" },
    });
    if (res) setAutoPopResult(res);
  };

  const runNormalize = async () => {
    const res = await api("/api/v1/nemsis-manager/normalize", "POST", {
      record: { "ePatient.13": "M", "eDispatch.02": true, "eTimes.01": "2026-02-26" },
    });
    if (res) setNormResult(res);
  };

  const runExportSimulation = async () => {
    const provided = elementsInput.split(",").map((e) => e.trim()).filter(Boolean);
    const incident: Record<string, string> = {};
    provided.forEach((e) => {
      incident[e] = "test_value";
    });
    const res = await api("/api/v1/nemsis-manager/export/simulate", "POST", {
      incident,
      patient: {},
    });
    if (res) setSimResult(res);
  };

  const runReportableFlag = async () => {
    const res = await api("/api/v1/nemsis-manager/reportable-flag", "POST", {
      incident: {
        "eSituation.13": "Critical",
        "eDisposition.12": "Patient Treated",
        "eNarrative.01": narrativeInput,
      },
    });
    if (res) setReportableFlagResult(res);
  };

  const filteredElements = schema
    ? Object.entries(schema.schema).filter(([id, elem]) => {
        const matchSearch =
          !searchTerm ||
          id.toLowerCase().includes(searchTerm.toLowerCase()) ||
          elem.label.toLowerCase().includes(searchTerm.toLowerCase());
        const matchSection = selectedSection === "all" || elem.section === selectedSection;
        return matchSearch && matchSection;
      })
    : [];

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "schema", label: "Schema Browser" },
    { id: "validate", label: "Validation" },
    { id: "narrative", label: "Narrative & Coding" },
    { id: "export", label: "Exports" },
    { id: "compliance", label: "Compliance" },
    { id: "tools", label: "Data Tools" },
  ];

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-border bg-panel p-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="text-xl font-bold">NEMSIS 3.5.1 Dataset Manager</div>
            <div className="text-sm text-muted mt-1">
              Full schema management, real-time validation, state submission readiness, and
              certification tooling
            </div>
          </div>
          <div className="flex items-center gap-2">
            {schema && <Badge color="green" label={`NEMSIS v${schema.version}`} />}
            {integrityScore && (
              <div
                className={`rounded-lg border px-3 py-1 text-xs font-bold ${
                  integrityScore.grade === "A"
                    ? "border-green-700 bg-green-900/40 text-green-300"
                    : integrityScore.grade === "B"
                    ? "border-blue-700 bg-blue-900/40 text-blue-300"
                    : "border-yellow-700 bg-yellow-900/40 text-yellow-300"
                }`}
              >
                Grade {integrityScore.grade}
              </div>
            )}
          </div>
        </div>
      </div>

      <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
        <Tabs.List className="flex gap-1 flex-wrap border-b border-border pb-2 mb-4">
          {tabs.map((t) => (
            <Tabs.Trigger
              key={t.id}
              value={t.id}
              className="rounded-lg px-3 py-2 text-xs font-medium text-muted hover:text-text data-[state=active]:bg-[rgba(255,255,255,0.08)] data-[state=active]:text-text"
            >
              {t.label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        <Tabs.Content value="overview">
          <div className="space-y-6">
            {schema && (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <StatCard label="Schema Version" value={schema.version} />
                <StatCard label="Total Elements" value={schema.total_elements} />
                <StatCard label="Required Elements" value={schema.required_count} accent="yellow" />
                <StatCard label="Sections" value={schema.sections.length} />
              </div>
            )}

            {integrityScore && (
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Data Integrity Score" />
                <div className="flex items-end gap-4">
                  <div
                    className={`text-5xl font-bold ${
                      integrityScore.grade === "A"
                        ? "text-green-400"
                        : integrityScore.grade === "B"
                        ? "text-blue-400"
                        : "text-yellow-400"
                    }`}
                  >
                    {integrityScore.integrity_score}%
                  </div>
                  <div>
                    <div
                      className={`text-2xl font-bold ${
                        integrityScore.grade === "A" ? "text-green-400" : "text-yellow-400"
                      }`}
                    >
                      Grade {integrityScore.grade}
                    </div>
                    <div className="text-xs text-muted mt-1">
                      {integrityScore.valid_count} of {integrityScore.total} valid
                    </div>
                  </div>
                </div>
                <div className="mt-3 h-3 rounded-full bg-[rgba(255,255,255,0.08)] overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      integrityScore.grade === "A"
                        ? "bg-green-500"
                        : integrityScore.grade === "B"
                        ? "bg-blue-500"
                        : "bg-yellow-500"
                    }`}
                    style={{ width: `${integrityScore.integrity_score}%` }}
                  />
                </div>
              </div>
            )}

            {certReadiness && (
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Certification Readiness" />
                <div className="flex items-center gap-3 mb-4">
                  <Badge
                    color={certReadiness.certification_ready ? "green" : "red"}
                    label={certReadiness.certification_ready ? "CERTIFIED READY" : "NOT READY"}
                  />
                  <span className="text-sm text-muted">
                    {certReadiness.checks_passed}/{certReadiness.total_checks} checks passed
                  </span>
                </div>
                <div className="space-y-2">
                  {certReadiness.checks.map((check, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <span
                        className={`h-4 w-4 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                          check.passed ? "bg-green-500 text-white" : "bg-red-500 text-white"
                        }`}
                      >
                        {check.passed ? "✓" : "✗"}
                      </span>
                      <span className={check.passed ? "text-text" : "text-muted"}>
                        {check.check}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {exportDash && (
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Export Dashboard" />
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <StatCard label="Total Export Jobs" value={exportDash.total_jobs} />
                  <StatCard label="Export Batches" value={exportDash.total_batches} />
                  <StatCard
                    label="Pending Batches"
                    value={exportDash.pending_batches}
                    accent={exportDash.pending_batches > 0 ? "yellow" : "green"}
                  />
                  <StatCard
                    label="State Rejections"
                    value={exportDash.total_rejections}
                    accent={exportDash.total_rejections > 0 ? "red" : "green"}
                  />
                </div>
                {Object.keys(exportDash.jobs_by_status).length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {Object.entries(exportDash.jobs_by_status).map(([status, count]) => (
                      <div key={status} className="rounded-lg border border-border px-3 py-1 text-xs">
                        <span className="text-muted">{status}: </span>
                        <span className="font-semibold">{count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {schemaDiff && (
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle
                  title={`Schema Diff v${schemaDiff.version_a} → v${schemaDiff.version_b}`}
                />
                <div className="space-y-2">
                  {schemaDiff.diff.map((d, i) => (
                    <div key={i} className="flex items-center gap-3 text-sm">
                      <Badge
                        color={
                          d.status === "added"
                            ? "green"
                            : d.status === "deprecated"
                            ? "red"
                            : "yellow"
                        }
                        label={d.status}
                      />
                      <code className="text-xs bg-[rgba(255,255,255,0.06)] px-2 py-0.5 rounded">
                        {d.element}
                      </code>
                      <span className="text-xs text-muted">{d.notes || d.change_detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="schema">
          <div className="space-y-4">
            {schema && (
              <>
                <div className="flex flex-wrap gap-3">
                  <input
                    className="flex-1 min-w-48 rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none"
                    placeholder="Search elements by ID or label..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                  <select
                    className="rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm"
                    value={selectedSection}
                    onChange={(e) => setSelectedSection(e.target.value)}
                  >
                    <option value="all">All Sections</option>
                    {schema.sections.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="text-xs text-muted">{filteredElements.length} elements shown</div>
                <div className="rounded-xl border border-border bg-panel overflow-hidden">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border bg-[rgba(255,255,255,0.02)]">
                        <th className="py-2 px-3 text-left text-muted font-medium">Element ID</th>
                        <th className="py-2 px-3 text-left text-muted font-medium">Label</th>
                        <th className="py-2 px-3 text-left text-muted font-medium">Section</th>
                        <th className="py-2 px-3 text-left text-muted font-medium">Type</th>
                        <th className="py-2 px-3 text-left text-muted font-medium">Flags</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredElements.slice(0, 60).map(([id, elem]) => (
                        <tr
                          key={id}
                          className="border-b border-border/50 hover:bg-[rgba(255,255,255,0.02)]"
                        >
                          <td className="py-2 px-3 font-mono">{id}</td>
                          <td className="py-2 px-3">{elem.label}</td>
                          <td className="py-2 px-3 text-muted">{elem.section}</td>
                          <td className="py-2 px-3 text-muted">{elem.type}</td>
                          <td className="py-2 px-3">
                            <div className="flex gap-1 flex-wrap">
                              <Badge
                                color={elem.required ? "red" : "gray"}
                                label={elem.required ? "Required" : "Optional"}
                              />
                              {elem.phi && <Badge color="yellow" label="PHI" />}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {filteredElements.length > 60 && (
                    <div className="py-2 px-3 text-xs text-muted border-t border-border">
                      Showing 60 of {filteredElements.length} elements
                    </div>
                  )}
                </div>
                {hierarchy && (
                  <div className="rounded-xl border border-border bg-panel p-4">
                    <SectionTitle title="Section Summary" />
                    <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                      {hierarchy.sections.map((section) => {
                        const sectionElems = hierarchy.hierarchy[section] || [];
                        const reqCount = sectionElems.filter((e) => e.required).length;
                        return (
                          <div key={section} className="rounded-lg border border-border p-3">
                            <div className="font-semibold text-xs">{section}</div>
                            <div className="mt-1 text-xs text-muted">
                              {sectionElems.length} elements · {reqCount} required
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="validate">
          <div className="space-y-5">
            <div className="rounded-xl border border-border bg-panel p-5">
              <SectionTitle title="Live Validation Engine" />
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-muted">Provided Elements (comma-separated)</label>
                  <textarea
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-xs font-mono outline-none"
                    rows={3}
                    value={elementsInput}
                    onChange={(e) => setElementsInput(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs text-muted">State Code</label>
                  <input
                    className="mt-1 w-24 rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none"
                    value={stateCode}
                    onChange={(e) => setStateCode(e.target.value)}
                    placeholder="CA"
                  />
                </div>
                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={runLiveValidation}
                    className="rounded-lg bg-billing px-4 py-2 text-sm font-semibold text-black hover:opacity-90"
                  >
                    Validate Live
                  </button>
                  <button
                    onClick={runReadiness}
                    className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-[rgba(255,255,255,0.05)]"
                  >
                    Readiness Score
                  </button>
                  <button
                    onClick={runExportSimulation}
                    className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-[rgba(255,255,255,0.05)]"
                  >
                    Export Simulation
                  </button>
                </div>
              </div>
              {liveValidResult && (
                <div className="mt-3">
                  <ValidationResultDisplay result={liveValidResult} />
                </div>
              )}
              {readinessResult && (
                <div className="mt-3 rounded-lg border border-border p-4">
                  <SectionTitle title="Readiness Score" />
                  <div className="flex items-end gap-3 mb-3">
                    <div
                      className={`text-4xl font-bold ${
                        readinessResult.completeness_pct === 100
                          ? "text-green-400"
                          : readinessResult.completeness_pct >= 80
                          ? "text-yellow-400"
                          : "text-red-400"
                      }`}
                    >
                      {readinessResult.completeness_pct}%
                    </div>
                    <Badge
                      color={readinessResult.ready_for_submission ? "green" : "red"}
                      label={readinessResult.score_label}
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs text-muted">
                    <span>Required: {readinessResult.required_count}</span>
                    <span>Provided: {readinessResult.provided_required}</span>
                    <span className="text-red-300">Missing: {readinessResult.missing_required}</span>
                  </div>
                </div>
              )}
              {simResult && (
                <div
                  className={`mt-3 rounded-lg border p-4 ${
                    (simResult as Record<string, boolean>).can_export
                      ? "border-green-700 bg-green-900/20"
                      : "border-red-700 bg-red-900/20"
                  }`}
                >
                  <div
                    className={`font-semibold text-sm ${
                      (simResult as Record<string, boolean>).can_export
                        ? "text-green-300"
                        : "text-red-300"
                    }`}
                  >
                    Export{" "}
                    {(simResult as Record<string, boolean>).can_export ? "READY" : "NOT READY"} —{" "}
                    {String((simResult as Record<string, unknown>).missing_count)} missing
                  </div>
                </div>
              )}
            </div>

            <div className="rounded-xl border border-border bg-panel p-5">
              <SectionTitle title="Field-Level Validation" />
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <label className="text-xs text-muted">Element ID</label>
                  <input
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none font-mono"
                    value={fieldId}
                    onChange={(e) => setFieldId(e.target.value)}
                    placeholder="e.g. ePatient.04"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted">Value</label>
                  <input
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none"
                    value={fieldValue}
                    onChange={(e) => setFieldValue(e.target.value)}
                    placeholder="Test value"
                  />
                </div>
              </div>
              <button
                onClick={runFieldValidation}
                className="mt-3 rounded-lg bg-billing px-4 py-2 text-sm font-semibold text-black hover:opacity-90"
              >
                Validate Field
              </button>
              {fieldResult && (
                <div
                  className={`mt-3 rounded-lg border p-3 text-sm ${
                    (fieldResult as Record<string, boolean>).valid
                      ? "border-green-700 bg-green-900/20 text-green-300"
                      : "border-red-700 bg-red-900/20 text-red-300"
                  }`}
                >
                  <div className="font-semibold">
                    {String(fieldResult.label || fieldResult.element_id)}:{" "}
                    {(fieldResult as Record<string, boolean>).valid ? "VALID" : "INVALID"}
                  </div>
                  {((fieldResult.errors as string[]) || []).map((e: string, i: number) => (
                    <div key={i} className="text-xs mt-1">
                      {e}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-xl border border-border bg-panel p-4">
              <SectionTitle title={`Validation History (${validationHistory.length})`} />
              {validationHistory.length === 0 ? (
                <div className="text-sm text-muted">No validation history yet.</div>
              ) : (
                <div className="space-y-2">
                  {[...validationHistory].reverse().slice(0, 10).map((v) => (
                    <div
                      key={v.id}
                      className="flex items-center gap-2 text-xs rounded-lg border border-border px-3 py-2"
                    >
                      <Badge
                        color={v.data.valid ? "green" : "red"}
                        label={v.data.valid ? "VALID" : "INVALID"}
                      />
                      <span className="text-muted">{v.data.validation_type}</span>
                      {(v.data.errors || []).length > 0 && (
                        <span className="text-red-300">
                          {(v.data.errors || []).length} error(s)
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Tabs.Content>

        <Tabs.Content value="narrative">
          <div className="space-y-5">
            <div className="rounded-xl border border-border bg-panel p-5">
              <SectionTitle title="Narrative & Medical Necessity Analysis" />
              <div>
                <label className="text-xs text-muted">PCR Narrative (eNarrative.01)</label>
                <textarea
                  className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none"
                  rows={4}
                  value={narrativeInput}
                  onChange={(e) => setNarrativeInput(e.target.value)}
                />
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                <button
                  onClick={runNarrativeCheck}
                  className="rounded-lg bg-billing px-4 py-2 text-sm font-semibold text-black hover:opacity-90"
                >
                  Narrative Check
                </button>
                <button
                  onClick={runMedNecessity}
                  className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-[rgba(255,255,255,0.05)]"
                >
                  Medical Necessity
                </button>
                <button
                  onClick={runCodingSuggest}
                  className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-[rgba(255,255,255,0.05)]"
                >
                  Auto-Code Suggest
                </button>
                <button
                  onClick={runReportableFlag}
                  className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-[rgba(255,255,255,0.05)]"
                >
                  Reportable Flag
                </button>
              </div>

              {narrativeResult && (
                <div
                  className={`mt-3 rounded-lg border p-3 ${
                    (narrativeResult as Record<string, boolean>).valid
                      ? "border-green-700 bg-green-900/20"
                      : "border-red-700 bg-red-900/20"
                  }`}
                >
                  <div
                    className={`font-semibold text-sm ${
                      (narrativeResult as Record<string, boolean>).valid
                        ? "text-green-300"
                        : "text-red-300"
                    }`}
                  >
                    Narrative:{" "}
                    {(narrativeResult as Record<string, boolean>).valid ? "VALID" : "INSUFFICIENT"}
                  </div>
                  <div className="mt-1 text-xs text-muted">
                    Length: {String(narrativeResult.length)} | Min:{" "}
                    {String(narrativeResult.min_length)} | Required phrases:{" "}
                    {String(narrativeResult.required_phrases_present)}
                  </div>
                </div>
              )}

              {medNecessityResult && (
                <div
                  className={`mt-3 rounded-lg border p-3 ${
                    (medNecessityResult as Record<string, boolean>).has_medical_necessity
                      ? "border-green-700 bg-green-900/20"
                      : "border-yellow-700 bg-yellow-900/20"
                  }`}
                >
                  <div
                    className={`font-semibold text-sm ${
                      (medNecessityResult as Record<string, boolean>).has_medical_necessity
                        ? "text-green-300"
                        : "text-yellow-300"
                    }`}
                  >
                    Medical Necessity:{" "}
                    {(medNecessityResult as Record<string, boolean>).has_medical_necessity
                      ? "DOCUMENTED"
                      : "INSUFFICIENT"}
                  </div>
                  {(
                    (medNecessityResult as Record<string, string[]>)
                      .medical_necessity_keywords_found || []
                  ).length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {(
                        (medNecessityResult as Record<string, string[]>)
                          .medical_necessity_keywords_found || []
                      ).map((kw) => (
                        <span
                          key={kw}
                          className="rounded bg-green-900/40 px-1.5 py-0.5 text-xs text-green-300"
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="mt-1 text-xs text-muted">
                    {String(medNecessityResult.recommendation)}
                  </div>
                </div>
              )}

              {codingSuggestResult && (
                <div className="mt-3 rounded-lg border border-border p-3">
                  <div className="font-semibold text-sm mb-2">
                    Coding Suggestions ({String(codingSuggestResult.count)})
                  </div>
                  {(
                    (
                      codingSuggestResult as Record<
                        string,
                        Array<{
                          element: string;
                          suggested_code: string;
                          label: string;
                          trigger: string;
                        }>
                      >
                    ).suggestions || []
                  ).map((s, i) => (
                    <div
                      key={i}
                      className="text-xs rounded border border-border px-2 py-1.5 mb-1"
                    >
                      <span className="font-mono text-muted">{s.element}: </span>
                      <span className="font-semibold">{s.suggested_code}</span>
                      <span className="text-muted"> ({s.label})</span>
                      <span className="ml-2 text-blue-300">← &quot;{s.trigger}&quot;</span>
                    </div>
                  ))}
                  {(codingSuggestResult.count as number) === 0 && (
                    <div className="text-sm text-muted">No coding triggers found in narrative</div>
                  )}
                </div>
              )}

              {reportableFlagResult && (
                <div
                  className={`mt-3 rounded-lg border p-3 ${
                    (reportableFlagResult as Record<string, boolean>).reportable
                      ? "border-red-700 bg-red-900/20"
                      : "border-border"
                  }`}
                >
                  <div
                    className={`font-semibold text-sm ${
                      (reportableFlagResult as Record<string, boolean>).reportable
                        ? "text-red-300"
                        : "text-muted"
                    }`}
                  >
                    Reportable Incident:{" "}
                    {(reportableFlagResult as Record<string, boolean>).reportable
                      ? "YES — FLAG TRIGGERED"
                      : "No flags triggered"}
                  </div>
                  {(
                    (
                      reportableFlagResult as Record<
                        string,
                        Array<{ flag: string; reason: string }>
                      >
                    ).flags || []
                  ).map((f, i) => (
                    <div key={i} className="mt-1 text-xs text-red-200">
                      {f.flag}: {f.reason}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Tabs.Content>

        <Tabs.Content value="export">
          <div className="space-y-5">
            {exportDash && (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <StatCard label="Total Jobs" value={exportDash.total_jobs} />
                <StatCard label="Batches" value={exportDash.total_batches} />
                <StatCard
                  label="Pending"
                  value={exportDash.pending_batches}
                  accent={exportDash.pending_batches > 0 ? "yellow" : "green"}
                />
                <StatCard
                  label="Rejections"
                  value={exportDash.total_rejections}
                  accent={exportDash.total_rejections > 0 ? "red" : "green"}
                />
              </div>
            )}
            <div className="rounded-xl border border-border bg-panel p-4">
              <SectionTitle title={`Export Batches (${exportBatches.length})`} />
              {exportBatches.length === 0 ? (
                <div className="text-sm text-muted">No export batches created yet.</div>
              ) : (
                <div className="space-y-2">
                  {exportBatches.map((b) => (
                    <div
                      key={b.id}
                      className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm"
                    >
                      <div>
                        <span className="font-medium">Batch</span>
                        <span className="ml-2 text-xs text-muted">
                          {b.data.batch_size} incidents · {b.data.state_code}
                        </span>
                      </div>
                      <Badge
                        color={
                          b.data.status === "completed"
                            ? "green"
                            : b.data.status === "queued"
                            ? "yellow"
                            : "red"
                        }
                        label={b.data.status || "queued"}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="rounded-xl border border-border bg-panel p-4">
              <SectionTitle title={`State Rejections (${rejections.length})`} />
              {rejections.length === 0 ? (
                <div className="text-sm text-muted">No state rejections recorded.</div>
              ) : (
                <div className="space-y-2">
                  {rejections.map((r) => (
                    <div key={r.id} className="rounded-lg border border-border p-3 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{r.data.state_code}</span>
                        <Badge
                          color={r.data.resolved ? "green" : "red"}
                          label={r.data.resolved ? "Resolved" : "Open"}
                        />
                      </div>
                      {r.data.rejection_reason && (
                        <div className="text-xs text-muted mt-1">{r.data.rejection_reason}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Tabs.Content>

        <Tabs.Content value="compliance">
          <div className="space-y-5">
            {certReadiness && (
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Certification Checks" />
                <div className="space-y-2">
                  {certReadiness.checks.map((check, i) => (
                    <div
                      key={i}
                      className={`rounded-lg border p-3 flex items-center gap-3 ${
                        check.passed
                          ? "border-green-700 bg-green-900/10"
                          : "border-red-700 bg-red-900/10"
                      }`}
                    >
                      <span
                        className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                          check.passed ? "bg-green-500 text-white" : "bg-red-500 text-white"
                        }`}
                      >
                        {check.passed ? "✓" : "✗"}
                      </span>
                      <span className={`text-sm ${check.passed ? "" : "text-muted"}`}>
                        {check.check}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {upgradeImpact && (
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Upgrade Impact Analysis" />
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-sm text-muted">v{upgradeImpact.from_version}</span>
                  <span className="text-muted">→</span>
                  <span className="text-sm font-semibold">v{upgradeImpact.to_version}</span>
                  <Badge
                    color={upgradeImpact.migration_required ? "yellow" : "green"}
                    label={
                      upgradeImpact.migration_required ? "Migration Required" : "No Migration"
                    }
                  />
                </div>
                {upgradeImpact.breaking_changes.map((c, i) => (
                  <div
                    key={i}
                    className="text-xs rounded border border-yellow-700 bg-yellow-900/10 px-3 py-2 mb-1"
                  >
                    <span className="font-mono">{c.element}</span>:{" "}
                    <span className="text-yellow-300">{c.change}</span>
                  </div>
                ))}
                <div className="mt-2 text-xs text-muted">
                  Impacted records: {upgradeImpact.impacted_records}
                </div>
              </div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="tools">
          <div className="space-y-5">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Auto-Populate Fields" />
                <div className="text-xs text-muted mb-3">
                  Detect missing standard fields from incident context
                </div>
                <button
                  onClick={runAutoPopulate}
                  className="rounded-lg bg-billing px-4 py-2 text-sm font-semibold text-black hover:opacity-90"
                >
                  Run Auto-Populate
                </button>
                {autoPopResult && (
                  <div className="mt-3 space-y-1">
                    <div className="text-xs text-muted">
                      {String(autoPopResult.count)} fields auto-populated
                    </div>
                    {Object.entries(
                      (autoPopResult as Record<string, Record<string, string>>).auto_populated || {}
                    ).map(([k, v]) => (
                      <div key={k} className="text-xs rounded border border-border px-2 py-1">
                        <span className="font-mono text-muted">{k}: </span>
                        <span className="text-green-300">{v}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Data Normalization" />
                <div className="text-xs text-muted mb-3">
                  Normalize values to NEMSIS 3.5.1 standards
                </div>
                <button
                  onClick={runNormalize}
                  className="rounded-lg bg-billing px-4 py-2 text-sm font-semibold text-black hover:opacity-90"
                >
                  Normalize Sample
                </button>
                {normResult && (
                  <div className="mt-3">
                    <div className="text-xs text-muted mb-1">
                      {String(normResult.change_count)} fields normalized
                    </div>
                    {Object.entries(
                      (
                        normResult as Record<
                          string,
                          Record<string, { from: unknown; to: unknown }>
                        >
                      ).changes || {}
                    ).map(([k, v]) => (
                      <div key={k} className="text-xs rounded border border-border px-2 py-1 mb-1">
                        <span className="font-mono">{k}: </span>
                        <span className="text-red-300 line-through">{String(v.from)}</span>
                        <span className="text-muted"> → </span>
                        <span className="text-green-300">{String(v.to)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {schema && (
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Required Elements Quick Reference" />
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  {schema.sections.map((section) => {
                    const required = Object.entries(schema.schema).filter(
                      ([, e]) => e.section === section && e.required
                    );
                    if (required.length === 0) return null;
                    return (
                      <div key={section} className="rounded-lg border border-border p-3">
                        <div className="font-semibold text-xs mb-2">
                          {section} ({required.length})
                        </div>
                        <div className="space-y-0.5">
                          {required.map(([id, e]) => (
                            <div key={id} className="flex items-center gap-2 text-xs">
                              <span className="font-mono text-muted w-28 shrink-0">{id}</span>
                              <span className="truncate">{e.label}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
