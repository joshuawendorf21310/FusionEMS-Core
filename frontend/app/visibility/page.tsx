"use client";

import { useState, useEffect, useCallback } from "react";
import * as Tabs from "@radix-ui/react-tabs";

const BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type Rule = {
  id: string;
  data: {
    rule_name?: string;
    role?: string;
    action?: string;
    fields?: string[];
    status?: string;
    conditions?: Record<string, string>;
  };
};

type DashboardStats = {
  total_rules: number;
  active_rules: number;
  audit_events: number;
  pending_approvals: number;
  active_locks: number;
  compliance_locked: boolean;
};

type ViewModes = {
  role: string;
  modes: Record<string, boolean>;
};

type ModuleGates = {
  role: string;
  accessible_modules: string[];
  all_modules: string[];
};

type AccessAlert = {
  id: string;
  data: { alert_type?: string; severity?: string; description?: string };
};

type AnomalyEvent = {
  id: string;
  data: { anomaly_type?: string; severity?: string; description?: string };
};

type ApprovalRequest = {
  id: string;
  data: { requested_by?: string; justification?: string; status?: string };
};

type ComplianceLock = {
  id: string;
  data: { lock_type?: string; locked_by?: string; active?: boolean };
};

type TimeWindow = {
  id: string;
  data: { field?: string; start_utc?: string; end_utc?: string; roles?: string[] };
};

type ElevatedAccess = {
  id: string;
  data: { target_user_id?: string; duration_minutes?: number; granted_by?: string; status?: string };
};

type Policy = {
  id: string;
  data: { policy_name?: string; version?: string; active?: boolean };
};

type PhiFields = {
  phi_fields: string[];
  masked_for_role: string;
  masked: string[];
};

type RoleMatrix = {
  matrix: Record<string, string[]>;
  roles: string[];
};

type ZeroTrustResult = {
  resource: string;
  allowed: boolean;
  trust_score: number;
  requires_mfa: boolean;
  mfa_provided: boolean;
};

type KillSwitchStatus = {
  kill_switch_active: boolean;
  latest_event: null | { data: Record<string, unknown> };
};

type AccessScore = {
  access_score: number;
  risk_level: string;
  anomaly_count: number;
};

type Heatmap = {
  heatmap: Array<{ field: string; rule_count: number }>;
};

type EvaluateResult = {
  visible_fields: string[];
  masked_fields: string[];
  denied_fields: string[];
  applied_rules: string[];
};

type EndpointRestrictions = {
  role: string;
  accessible_endpoints: Record<string, string[]>;
};

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-border bg-panel p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
      {sub && <div className="mt-1 text-xs text-muted">{sub}</div>}
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <div className="text-sm font-semibold text-muted uppercase tracking-wide mb-3">{title}</div>;
}

function Badge({ color, label }: { color: string; label: string }) {
  const colors: Record<string, string> = {
    green: "bg-green-900/40 text-green-300 border-green-700",
    red: "bg-red-900/40 text-red-300 border-red-700",
    yellow: "bg-yellow-900/40 text-yellow-300 border-yellow-700",
    blue: "bg-blue-900/40 text-blue-300 border-blue-700",
    gray: "bg-bg-raised text-text-secondary border-border-strong",
  };
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs border font-medium ${colors[color] ?? colors.gray}`}>
      {label}
    </span>
  );
}

function RuleCard({ rule, onDelete }: { rule: Rule; onDelete: (id: string) => void }) {
  const d = rule.data;
  const actionColor = d.action === "show" ? "green" : d.action === "mask" ? "yellow" : "red";
  return (
    <div className="rounded-xl border border-border bg-panel p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-sm">{d.rule_name || "Unnamed Rule"}</span>
        <div className="flex items-center gap-2">
          <Badge color={actionColor} label={d.action || "show"} />
          <Badge color={d.status === "active" ? "green" : "gray"} label={d.status || "active"} />
        </div>
      </div>
      {d.role && <div className="text-xs text-muted">Role: <span className="text-text">{d.role}</span></div>}
      {d.fields && d.fields.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {d.fields.map((f) => (
            <span key={f} className="rounded bg-[rgba(255,255,255,0.07)] px-2 py-0.5 text-xs">{f}</span>
          ))}
        </div>
      )}
      <button
        onClick={() => onDelete(rule.id)}
        className="mt-1 self-end text-xs text-red-400 hover:text-red-300"
      >
        Delete
      </button>
    </div>
  );
}

export default function VisibilityRuleMakerPage() {
  const [activeTab, setActiveTab] = useState("dashboard");

  const [dashboard, setDashboard] = useState<DashboardStats | null>(null);
  const [rules, setRules] = useState<Rule[]>([]);
  const [viewModes, setViewModes] = useState<ViewModes | null>(null);
  const [moduleGates, setModuleGates] = useState<ModuleGates | null>(null);
  const [phiFields, setPhiFields] = useState<PhiFields | null>(null);
  const [roleMatrix, setRoleMatrix] = useState<RoleMatrix | null>(null);
  const [killSwitchStatus, setKillSwitchStatus] = useState<KillSwitchStatus | null>(null);
  const [accessScore, setAccessScore] = useState<AccessScore | null>(null);
  const [heatmap, setHeatmap] = useState<Heatmap | null>(null);
  const [endpointRestrictions, setEndpointRestrictions] = useState<EndpointRestrictions | null>(null);
  const [alerts, setAlerts] = useState<AccessAlert[]>([]);
  const [anomalies, setAnomalyEvents] = useState<AnomalyEvent[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [complianceLocks, setComplianceLocks] = useState<ComplianceLock[]>([]);
  const [timeWindows, setTimeWindows] = useState<TimeWindow[]>([]);
  const [elevatedAccess, setElevatedAccess] = useState<ElevatedAccess[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);

  const [newRule, setNewRule] = useState({ rule_name: "", role: "ems", action: "show", fields: "", explanation: "" });
  const [evalContext, setEvalContext] = useState({ role: "ems", claim_status: "", payer_type: "" });
  const [evalResult, setEvalResult] = useState<EvaluateResult | null>(null);
  const [sandboxRule, setSandboxRule] = useState({ role: "billing", action: "mask", fields: "ssn,dob" });
  const [sandboxContext, setSandboxContext] = useState({ role: "billing", claim_status: "denied" });
  const [sandboxResult, setSandboxResult] = useState<Record<string, unknown> | null>(null);
  const [zeroTrustInput, setZeroTrustInput] = useState({ resource: "phi_data", mfa_verified: false, device_trusted: false, ip_allowed: true });
  const [zeroTrustResult, setZeroTrustResult] = useState<ZeroTrustResult | null>(null);
  const [redactionRecord, setRedactionRecord] = useState(`{"patient_name":"John Doe","dob":"1985-01-01","ssn":"123-45-6789","claim_id":"CL-001","amount":1250}`);
  const [redactionTemplate, setRedactionTemplate] = useState("standard");
  const [redactionResult, setRedactionResult] = useState<Record<string, unknown> | null>(null);
  const [deidentInput, setDeidentInput] = useState(`{"patient_name":"Jane Smith","dob":"1990-05-15","ssn":"987-65-4321","incident_id":"INC-001"}`);
  const [deidentResult, setDeidentResult] = useState<Record<string, unknown> | null>(null);
  const [simRole, setSimRole] = useState("billing");
  const [simResult, setSimResult] = useState<Record<string, unknown> | null>(null);
  const [minimizePurpose, setMinimizePurpose] = useState("billing");
  const [minimizeFields, setMinimizeFields] = useState("claim_id,patient_id,amount,ssn,narrative,dob");
  const [minimizeResult, setMinimizeResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const token = typeof window !== "undefined" ? (localStorage.getItem("access_token") || "") : "";
  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

  const api = useCallback(async (path: string, method = "GET", body?: unknown) => {
    const res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) return null;
    return res.json();
  }, []);

  const loadDashboard = useCallback(async () => {
    try {
      const [dash, r, vm, mg, phi, rm, ks, as_, hm, er, al, an, ap, cl, tw, ea, pol] = await Promise.all([
        api("/api/v1/visibility/dashboard"),
        api("/api/v1/visibility/rules"),
        api("/api/v1/visibility/view-modes"),
        api("/api/v1/visibility/module-gates"),
        api("/api/v1/visibility/phi-fields"),
        api("/api/v1/visibility/role-matrix"),
        api("/api/v1/visibility/kill-switch/status"),
        api("/api/v1/visibility/access-score"),
        api("/api/v1/visibility/heatmap"),
        api("/api/v1/visibility/endpoint-restrictions"),
        api("/api/v1/visibility/access-alerts"),
        api("/api/v1/visibility/anomaly-events"),
        api("/api/v1/visibility/approval-requests"),
        api("/api/v1/visibility/compliance-lock/status"),
        api("/api/v1/visibility/time-windows"),
        api("/api/v1/visibility/elevated-access"),
        api("/api/v1/visibility/policies"),
      ]);
      if (dash) setDashboard(dash);
      if (Array.isArray(r)) setRules(r);
      if (vm) setViewModes(vm);
      if (mg) setModuleGates(mg);
      if (phi) setPhiFields(phi);
      if (rm) setRoleMatrix(rm);
      if (ks) setKillSwitchStatus(ks);
      if (as_) setAccessScore(as_);
      if (hm) setHeatmap(hm);
      if (er) setEndpointRestrictions(er);
      if (Array.isArray(al)) setAlerts(al);
      if (Array.isArray(an)) setAnomalyEvents(an);
      if (Array.isArray(ap)) setApprovals(ap);
      if (cl) setComplianceLocks(cl.locks || []);
      if (Array.isArray(tw)) setTimeWindows(tw);
      if (Array.isArray(ea)) setElevatedAccess(ea);
      if (Array.isArray(pol)) setPolicies(pol);
    } catch (err: unknown) {
      console.warn("[visibility]", err);
    }
  }, [api]);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  const createRule = async () => {
    setLoading(true);
    const fields = newRule.fields.split(",").map((f) => f.trim()).filter(Boolean);
    const res = await api("/api/v1/visibility/rules", "POST", {
      rule_name: newRule.rule_name,
      role: newRule.role,
      action: newRule.action,
      fields,
      explanation: newRule.explanation,
      status: "active",
    });
    setLoading(false);
    if (res) {
      setMsg("Rule created successfully");
      loadDashboard();
    }
  };

  const deleteRule = async (id: string) => {
    await api(`/api/v1/visibility/rules/${id}`, "DELETE");
    loadDashboard();
  };

  const evaluateRules = async () => {
    const res = await api("/api/v1/visibility/evaluate", "POST", { context: evalContext });
    if (res) setEvalResult(res);
  };

  const runSandbox = async () => {
    const res = await api("/api/v1/visibility/rules/sandbox-test", "POST", {
      rule: { ...sandboxRule, fields: sandboxRule.fields.split(",").map((f) => f.trim()) },
      test_context: sandboxContext,
    });
    if (res) setSandboxResult(res);
  };

  const runZeroTrust = async () => {
    const res = await api("/api/v1/visibility/zero-trust/check", "POST", {
      resource: zeroTrustInput.resource,
      action: "read",
      context: zeroTrustInput,
    });
    if (res) setZeroTrustResult(res);
  };

  const runRedaction = async () => {
    try {
      const record = JSON.parse(redactionRecord);
      const res = await api("/api/v1/visibility/redaction-preview", "POST", { record, template: redactionTemplate });
      if (res) setRedactionResult(res);
    } catch { setMsg("Invalid JSON in record input"); }
  };

  const runDeidentify = async () => {
    try {
      const record = JSON.parse(deidentInput);
      const res = await api("/api/v1/visibility/deidentify", "POST", { record });
      if (res) setDeidentResult(res);
    } catch { setMsg("Invalid JSON"); }
  };

  const runRoleSimulation = async () => {
    const res = await api("/api/v1/visibility/role-simulation", "POST", { role: simRole });
    if (res) setSimResult(res);
  };

  const runMinimization = async () => {
    const fields = minimizeFields.split(",").map((f) => f.trim()).filter(Boolean);
    const res = await api("/api/v1/visibility/data-minimization/check", "POST", {
      requested_fields: fields,
      purpose: minimizePurpose,
    });
    if (res) setMinimizeResult(res);
  };

  const triggerKillSwitch = async (activated: boolean) => {
    await api("/api/v1/visibility/kill-switch", "POST", { activated, reason: "Manual toggle from dashboard" });
    loadDashboard();
  };

  const tabs = [
    { id: "dashboard", label: "Dashboard" },
    { id: "rules", label: "Rules" },
    { id: "evaluate", label: "Evaluate" },
    { id: "phi", label: "PHI & Masking" },
    { id: "access", label: "Access Control" },
    { id: "sandbox", label: "Sandbox" },
    { id: "policies", label: "Policies" },
    { id: "alerts", label: "Alerts" },
    { id: "advanced", label: "Advanced" },
  ];

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-border bg-panel p-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xl font-bold">Visibility Rule Maker</div>
            <div className="text-sm text-muted mt-1">Role-based field visibility, PHI masking, zero-trust enforcement, and policy management</div>
          </div>
          <div className="flex items-center gap-2">
            {killSwitchStatus && (
              <div className={`rounded-lg px-3 py-1 text-xs font-semibold border ${killSwitchStatus.kill_switch_active ? "bg-red-900/40 border-red-700 text-red-300" : "bg-green-900/40 border-green-700 text-green-300"}`}>
                Kill Switch: {killSwitchStatus.kill_switch_active ? "ACTIVE" : "OFF"}
              </div>
            )}
          </div>
        </div>
      </div>

      {msg && (
        <div className="rounded-xl border border-green-700 bg-green-900/20 px-4 py-3 text-sm text-green-300 flex items-center justify-between">
          <span>{msg}</span>
          <button onClick={() => setMsg("")} className="text-green-400 hover:text-green-200">×</button>
        </div>
      )}

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

        {/* DASHBOARD */}
        <Tabs.Content value="dashboard">
          <div className="space-y-6">
            {dashboard && (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
                <StatCard label="Total Rules" value={dashboard.total_rules} />
                <StatCard label="Active Rules" value={dashboard.active_rules} />
                <StatCard label="Audit Events" value={dashboard.audit_events} />
                <StatCard label="Pending Approvals" value={dashboard.pending_approvals} />
                <StatCard label="Active Locks" value={dashboard.active_locks} />
                <StatCard label="Compliance Lock" value={dashboard.compliance_locked ? "LOCKED" : "OPEN"} sub={dashboard.compliance_locked ? "Restricted" : "Normal"} />
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {viewModes && (
                <div className="rounded-xl border border-border bg-panel p-4">
                  <SectionTitle title="View Mode Permissions" />
                  <div className="space-y-2">
                    {Object.entries(viewModes.modes).map(([k, v]) => (
                      <div key={k} className="flex items-center justify-between text-sm">
                        <span className="text-muted">{k.replace(/_/g, " ")}</span>
                        <Badge color={v ? "green" : "red"} label={v ? "Allowed" : "Denied"} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {moduleGates && (
                <div className="rounded-xl border border-border bg-panel p-4">
                  <SectionTitle title="Module Access Gates" />
                  <div className="flex flex-wrap gap-2">
                    {moduleGates.all_modules.map((m) => (
                      <Badge
                        key={m}
                        color={moduleGates.accessible_modules.includes(m) ? "green" : "red"}
                        label={m}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {accessScore && (
                <div className="rounded-xl border border-border bg-panel p-4">
                  <SectionTitle title="Access Trust Score" />
                  <div className="flex items-end gap-3">
                    <div className="text-4xl font-bold">{accessScore.access_score}</div>
                    <Badge color={accessScore.risk_level === "low" ? "green" : accessScore.risk_level === "medium" ? "yellow" : "red"} label={accessScore.risk_level.toUpperCase()} />
                  </div>
                  <div className="mt-2 text-xs text-muted">{accessScore.anomaly_count} anomaly events on record</div>
                </div>
              )}

              {heatmap && heatmap.heatmap.length > 0 && (
                <div className="rounded-xl border border-border bg-panel p-4">
                  <SectionTitle title="Visibility Heatmap (Top Fields)" />
                  <div className="space-y-1.5">
                    {heatmap.heatmap.slice(0, 8).map((h) => (
                      <div key={h.field} className="flex items-center gap-2 text-xs">
                        <span className="w-28 truncate text-muted">{h.field}</span>
                        <div className="flex-1 rounded bg-[rgba(255,255,255,0.06)] h-2">
                          <div className="h-2 rounded bg-billing" style={{ width: `${Math.min(h.rule_count * 20, 100)}%` }} />
                        </div>
                        <span className="w-6 text-right">{h.rule_count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {endpointRestrictions && (
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Accessible Endpoints (Current Role: {endpointRestrictions.role})" />
                <div className="space-y-2">
                  {Object.entries(endpointRestrictions.accessible_endpoints).map(([ep, roles]) => (
                    <div key={ep} className="flex items-center gap-2 text-xs">
                      <code className="rounded bg-[rgba(255,255,255,0.06)] px-2 py-0.5 text-muted">{ep}</code>
                      <div className="flex flex-wrap gap-1">
                        {roles.map((r) => <Badge key={r} color="blue" label={r} />)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="rounded-xl border border-border bg-panel p-4">
              <SectionTitle title="Global Kill-Switch" />
              <div className="flex items-center gap-4">
                <div className="text-sm text-muted">Emergency visibility shutdown for all non-founder roles</div>
                <div className="flex gap-2 ml-auto">
                  <button onClick={() => triggerKillSwitch(true)} className="rounded-lg bg-red-700 px-4 py-2 text-xs font-semibold text-text-primary hover:bg-red-600">
                    Activate Kill Switch
                  </button>
                  <button onClick={() => triggerKillSwitch(false)} className="rounded-lg border border-border px-4 py-2 text-xs hover:bg-[rgba(255,255,255,0.05)]">
                    Deactivate
                  </button>
                </div>
              </div>
            </div>
          </div>
        </Tabs.Content>

        {/* RULES */}
        <Tabs.Content value="rules">
          <div className="space-y-5">
            <div className="rounded-xl border border-border bg-panel p-5">
              <SectionTitle title="Create Visibility Rule" />
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <input
                  className="rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none"
                  placeholder="Rule name"
                  value={newRule.rule_name}
                  onChange={(e) => setNewRule({ ...newRule, rule_name: e.target.value })}
                />
                <select
                  className="rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm"
                  value={newRule.role}
                  onChange={(e) => setNewRule({ ...newRule, role: e.target.value })}
                >
                  {["founder", "agency_admin", "billing", "ems", "compliance", "viewer"].map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
                <select
                  className="rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm"
                  value={newRule.action}
                  onChange={(e) => setNewRule({ ...newRule, action: e.target.value })}
                >
                  <option value="show">Show</option>
                  <option value="mask">Mask</option>
                  <option value="deny">Deny</option>
                </select>
                <input
                  className="rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none"
                  placeholder="Fields (comma-separated): ssn, dob, patient_name"
                  value={newRule.fields}
                  onChange={(e) => setNewRule({ ...newRule, fields: e.target.value })}
                />
                <input
                  className="rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none md:col-span-2"
                  placeholder="Explanation (optional)"
                  value={newRule.explanation}
                  onChange={(e) => setNewRule({ ...newRule, explanation: e.target.value })}
                />
              </div>
              <button
                onClick={createRule}
                disabled={loading}
                className="mt-3 rounded-lg bg-billing px-5 py-2 text-sm font-semibold text-text-inverse hover:opacity-90 disabled:opacity-50"
              >
                {loading ? "Creating..." : "Create Rule"}
              </button>
            </div>

            <div>
              <SectionTitle title={`Active Rules (${rules.length})`} />
              {rules.length === 0 ? (
                <div className="rounded-xl border border-border bg-panel p-6 text-center text-sm text-muted">No rules created yet. Create your first rule above.</div>
              ) : (
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  {rules.map((rule) => (
                    <RuleCard key={rule.id} rule={rule} onDelete={deleteRule} />
                  ))}
                </div>
              )}
            </div>

            {roleMatrix && (
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Role-Field Visibility Matrix" />
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="py-2 text-left text-muted font-medium">Role</th>
                        <th className="py-2 text-left text-muted font-medium">Visible Fields</th>
                      </tr>
                    </thead>
                    <tbody>
                      {roleMatrix.roles.map((role) => (
                        <tr key={role} className="border-b border-border/50">
                          <td className="py-2 font-medium">{role}</td>
                          <td className="py-2">
                            {(roleMatrix.matrix[role] || []).length === 0 ? (
                              <span className="text-muted">No fields defined</span>
                            ) : (
                              <div className="flex flex-wrap gap-1">
                                {(roleMatrix.matrix[role] || []).map((f) => (
                                  <span key={f} className="rounded bg-[rgba(255,255,255,0.06)] px-1.5 py-0.5">{f}</span>
                                ))}
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </Tabs.Content>

        {/* EVALUATE */}
        <Tabs.Content value="evaluate">
          <div className="space-y-5">
            <div className="rounded-xl border border-border bg-panel p-5">
              <SectionTitle title="Evaluate Rules Against Context" />
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                <div>
                  <label className="text-xs text-muted">Role</label>
                  <select
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm"
                    value={evalContext.role}
                    onChange={(e) => setEvalContext({ ...evalContext, role: e.target.value })}
                  >
                    {["founder", "agency_admin", "billing", "ems", "compliance", "viewer"].map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted">Claim Status</label>
                  <input
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none"
                    placeholder="e.g. denied, approved"
                    value={evalContext.claim_status}
                    onChange={(e) => setEvalContext({ ...evalContext, claim_status: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-muted">Payer Type</label>
                  <input
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none"
                    placeholder="e.g. medicare, medicaid"
                    value={evalContext.payer_type}
                    onChange={(e) => setEvalContext({ ...evalContext, payer_type: e.target.value })}
                  />
                </div>
              </div>
              <button
                onClick={evaluateRules}
                className="mt-3 rounded-lg bg-billing px-5 py-2 text-sm font-semibold text-text-inverse hover:opacity-90"
              >
                Evaluate
              </button>

              {evalResult && (
                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
                  <div className="rounded-lg border border-green-700 bg-green-900/20 p-3">
                    <div className="text-xs font-semibold text-green-300 mb-2">Visible Fields ({evalResult.visible_fields.length})</div>
                    {evalResult.visible_fields.length === 0 ? <div className="text-xs text-muted">None</div> : evalResult.visible_fields.map((f) => <div key={f} className="text-xs">{f}</div>)}
                  </div>
                  <div className="rounded-lg border border-yellow-700 bg-yellow-900/20 p-3">
                    <div className="text-xs font-semibold text-yellow-300 mb-2">Masked Fields ({evalResult.masked_fields.length})</div>
                    {evalResult.masked_fields.length === 0 ? <div className="text-xs text-muted">None</div> : evalResult.masked_fields.map((f) => <div key={f} className="text-xs">{f}</div>)}
                  </div>
                  <div className="rounded-lg border border-red-700 bg-red-900/20 p-3">
                    <div className="text-xs font-semibold text-red-300 mb-2">Denied Fields ({evalResult.denied_fields.length})</div>
                    {evalResult.denied_fields.length === 0 ? <div className="text-xs text-muted">None</div> : evalResult.denied_fields.map((f) => <div key={f} className="text-xs">{f}</div>)}
                  </div>
                </div>
              )}
            </div>

            <div className="rounded-xl border border-border bg-panel p-5">
              <SectionTitle title="Data Minimization Check" />
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <label className="text-xs text-muted">Purpose</label>
                  <select
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm"
                    value={minimizePurpose}
                    onChange={(e) => setMinimizePurpose(e.target.value)}
                  >
                    {["billing", "clinical", "compliance", "general"].map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted">Requested Fields (comma-separated)</label>
                  <input
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none"
                    value={minimizeFields}
                    onChange={(e) => setMinimizeFields(e.target.value)}
                  />
                </div>
              </div>
              <button onClick={runMinimization} className="mt-3 rounded-lg bg-billing px-5 py-2 text-sm font-semibold text-text-inverse hover:opacity-90">
                Check Minimization
              </button>
              {minimizeResult && (
                <div className={`mt-3 rounded-lg border p-3 text-sm ${(minimizeResult as Record<string, unknown>).compliant ? "border-green-700 bg-green-900/20 text-green-300" : "border-red-700 bg-red-900/20 text-red-300"}`}>
                  <div className="font-semibold">{(minimizeResult as Record<string, unknown>).compliant ? "Compliant - No excessive fields" : "Non-compliant - Excessive fields detected"}</div>
                  {((minimizeResult as Record<string, unknown[]>).excessive_fields || []).length > 0 && (
                    <div className="mt-1 text-xs">Excessive: {((minimizeResult as Record<string, string[]>).excessive_fields || []).join(", ")}</div>
                  )}
                  <div className="mt-1 text-xs text-muted">Minimum for '{String(minimizeResult.purpose)}': {((minimizeResult as Record<string, string[]>).minimum_fields || []).join(", ")}</div>
                </div>
              )}
            </div>
          </div>
        </Tabs.Content>

        {/* PHI & MASKING */}
        <Tabs.Content value="phi">
          <div className="space-y-5">
            {phiFields && (
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="PHI Field Classification" />
                <div className="mb-3 text-xs text-muted">Role: <span className="text-text font-medium">{phiFields.masked_for_role}</span> | Masked fields: <span className="text-yellow-300">{phiFields.masked.length}</span></div>
                <div className="flex flex-wrap gap-2">
                  {phiFields.phi_fields.map((f) => (
                    <span key={f} className={`rounded px-2 py-1 text-xs border ${phiFields.masked.includes(f) ? "border-yellow-700 bg-yellow-900/20 text-yellow-300" : "border-green-700 bg-green-900/20 text-green-300"}`}>
                      {phiFields.masked.includes(f) ? "*** " : ""}{f}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="rounded-xl border border-border bg-panel p-5">
              <SectionTitle title="Data Redaction Preview" />
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <label className="text-xs text-muted">Template</label>
                  <select
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm"
                    value={redactionTemplate}
                    onChange={(e) => setRedactionTemplate(e.target.value)}
                  >
                    {["standard", "hipaa_strict", "billing_safe", "export_safe"].map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted">Record JSON</label>
                  <textarea
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-xs font-mono outline-none"
                    rows={3}
                    value={redactionRecord}
                    onChange={(e) => setRedactionRecord(e.target.value)}
                  />
                </div>
              </div>
              <button onClick={runRedaction} className="mt-3 rounded-lg bg-billing px-5 py-2 text-sm font-semibold text-text-inverse hover:opacity-90">
                Preview Redaction
              </button>
              {redactionResult && (
                <div className="mt-3 rounded-lg border border-border bg-[rgba(255,255,255,0.03)] p-3">
                  <div className="text-xs font-semibold text-muted mb-2">Redacted Output</div>
                  <pre className="text-xs overflow-auto">{JSON.stringify((redactionResult as Record<string, unknown>).redacted, null, 2)}</pre>
                </div>
              )}
            </div>

            <div className="rounded-xl border border-border bg-panel p-5">
              <SectionTitle title="De-identification" />
              <div>
                <label className="text-xs text-muted">Record JSON</label>
                <textarea
                  className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-xs font-mono outline-none"
                  rows={3}
                  value={deidentInput}
                  onChange={(e) => setDeidentInput(e.target.value)}
                />
              </div>
              <button onClick={runDeidentify} className="mt-3 rounded-lg bg-billing px-5 py-2 text-sm font-semibold text-text-inverse hover:opacity-90">
                De-identify
              </button>
              {deidentResult && (
                <div className="mt-3 rounded-lg border border-border bg-[rgba(255,255,255,0.03)] p-3">
                  <div className="text-xs font-semibold text-muted mb-1">Fields removed: {String((deidentResult as Record<string, unknown>).fields_removed)}</div>
                  <pre className="text-xs overflow-auto">{JSON.stringify((deidentResult as Record<string, unknown>).deidentified, null, 2)}</pre>
                </div>
              )}
            </div>
          </div>
        </Tabs.Content>

        {/* ACCESS CONTROL */}
        <Tabs.Content value="access">
          <div className="space-y-5">
            <div className="rounded-xl border border-border bg-panel p-5">
              <SectionTitle title="Zero-Trust Access Check" />
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <label className="text-xs text-muted">Resource</label>
                  <select
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm"
                    value={zeroTrustInput.resource}
                    onChange={(e) => setZeroTrustInput({ ...zeroTrustInput, resource: e.target.value })}
                  >
                    {["phi_data", "financial_reports", "founder_view", "audit_logs", "incidents", "billing_dashboard"].map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  {[
                    { key: "mfa_verified", label: "MFA Verified" },
                    { key: "device_trusted", label: "Device Trusted" },
                    { key: "ip_allowed", label: "IP Allowed" },
                  ].map(({ key, label }) => (
                    <label key={key} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={zeroTrustInput[key as keyof typeof zeroTrustInput] as boolean}
                        onChange={(e) => setZeroTrustInput({ ...zeroTrustInput, [key]: e.target.checked })}
                        className="rounded"
                      />
                      <span className="text-sm">{label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <button onClick={runZeroTrust} className="mt-3 rounded-lg bg-billing px-5 py-2 text-sm font-semibold text-text-inverse hover:opacity-90">
                Check Zero-Trust
              </button>
              {zeroTrustResult && (
                <div className={`mt-3 rounded-lg border p-4 ${zeroTrustResult.allowed ? "border-green-700 bg-green-900/20" : "border-red-700 bg-red-900/20"}`}>
                  <div className={`font-semibold text-sm ${zeroTrustResult.allowed ? "text-green-300" : "text-red-300"}`}>
                    {zeroTrustResult.allowed ? "ACCESS GRANTED" : "ACCESS DENIED"}
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted">
                    <span>Trust Score: <strong className="text-text">{zeroTrustResult.trust_score}</strong></span>
                    <span>MFA Required: <strong className="text-text">{zeroTrustResult.requires_mfa ? "Yes" : "No"}</strong></span>
                  </div>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Elevated Access Grants" />
                {elevatedAccess.length === 0 ? (
                  <div className="text-sm text-muted">No active elevated access</div>
                ) : (
                  elevatedAccess.map((ea) => (
                    <div key={ea.id} className="rounded-lg border border-border p-3 text-xs space-y-1">
                      <div>Target: {ea.data.target_user_id}</div>
                      <div>Duration: {ea.data.duration_minutes}m</div>
                      <Badge color={ea.data.status === "active" ? "green" : "gray"} label={ea.data.status || "active"} />
                    </div>
                  ))
                )}
              </div>

              <div className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title="Time-Based Windows" />
                {timeWindows.length === 0 ? (
                  <div className="text-sm text-muted">No time windows configured</div>
                ) : (
                  timeWindows.slice(0, 5).map((tw) => (
                    <div key={tw.id} className="rounded-lg border border-border p-3 text-xs space-y-1 mb-2">
                      <div>Field: {tw.data.field}</div>
                      <div className="text-muted">{tw.data.start_utc} → {tw.data.end_utc}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </Tabs.Content>

        {/* SANDBOX */}
        <Tabs.Content value="sandbox">
          <div className="space-y-5">
            <div className="rounded-xl border border-border bg-panel p-5">
              <SectionTitle title="Rule Testing Sandbox" />
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-muted">Test Rule</label>
                    <div className="mt-1 grid grid-cols-2 gap-2">
                      <select
                        className="rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm"
                        value={sandboxRule.role}
                        onChange={(e) => setSandboxRule({ ...sandboxRule, role: e.target.value })}
                      >
                        {["billing", "ems", "compliance", "viewer"].map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                      <select
                        className="rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm"
                        value={sandboxRule.action}
                        onChange={(e) => setSandboxRule({ ...sandboxRule, action: e.target.value })}
                      >
                        <option value="show">show</option>
                        <option value="mask">mask</option>
                        <option value="deny">deny</option>
                      </select>
                    </div>
                    <input
                      className="mt-2 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none"
                      placeholder="Fields: ssn, dob, ..."
                      value={sandboxRule.fields}
                      onChange={(e) => setSandboxRule({ ...sandboxRule, fields: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-3">
                  <label className="text-xs text-muted">Test Context</label>
                  <select
                    className="w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm"
                    value={sandboxContext.role}
                    onChange={(e) => setSandboxContext({ ...sandboxContext, role: e.target.value })}
                  >
                    {["billing", "ems", "compliance", "viewer"].map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                  <input
                    className="w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none"
                    placeholder="claim_status"
                    value={sandboxContext.claim_status}
                    onChange={(e) => setSandboxContext({ ...sandboxContext, claim_status: e.target.value })}
                  />
                </div>
              </div>
              <button onClick={runSandbox} className="mt-3 rounded-lg bg-billing px-5 py-2 text-sm font-semibold text-text-inverse hover:opacity-90">
                Test Rule
              </button>
              {sandboxResult && (
                <div className={`mt-3 rounded-lg border p-4 ${sandboxResult.would_apply ? "border-green-700 bg-green-900/20" : "border-border bg-[rgba(255,255,255,0.03)]"}`}>
                  <div className={`font-semibold text-sm ${sandboxResult.would_apply ? "text-green-300" : "text-muted"}`}>
                    Rule would {sandboxResult.would_apply ? "" : "NOT "}apply
                  </div>
                  <div className="mt-2 text-xs text-muted">
                    Action: <span className="text-text">{String(sandboxResult.action)}</span> | Role Match: {String(sandboxResult.role_match)} | Conditions: {String(sandboxResult.conditions_match)}
                  </div>
                </div>
              )}
            </div>

            <div className="rounded-xl border border-border bg-panel p-5">
              <SectionTitle title="Role Simulation Testing" />
              <div className="flex items-end gap-3">
                <div className="flex-1">
                  <label className="text-xs text-muted">Simulate as Role</label>
                  <select
                    className="mt-1 w-full rounded-lg border border-border bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm"
                    value={simRole}
                    onChange={(e) => setSimRole(e.target.value)}
                  >
                    {["billing", "ems", "compliance", "viewer", "agency_admin"].map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
                <button onClick={runRoleSimulation} className="rounded-lg bg-billing px-5 py-2 text-sm font-semibold text-text-inverse hover:opacity-90">
                  Simulate
                </button>
              </div>
              {simResult && (
                <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
                  {["visible", "masked", "denied"].map((type) => (
                    <div key={type} className={`rounded-lg border p-3 ${type === "visible" ? "border-green-700 bg-green-900/20" : type === "masked" ? "border-yellow-700 bg-yellow-900/20" : "border-red-700 bg-red-900/20"}`}>
                      <div className={`text-xs font-semibold mb-2 ${type === "visible" ? "text-green-300" : type === "masked" ? "text-yellow-300" : "text-red-300"}`}>
                        {type.charAt(0).toUpperCase() + type.slice(1)} ({((simResult as Record<string, string[]>)[type] || []).length})
                      </div>
                      {((simResult as Record<string, string[]>)[type] || []).length === 0 ? (
                        <div className="text-xs text-muted">None</div>
                      ) : (
                        ((simResult as Record<string, string[]>)[type] || []).map((f) => <div key={f} className="text-xs">{f}</div>)
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Tabs.Content>

        {/* POLICIES */}
        <Tabs.Content value="policies">
          <div className="space-y-5">
            <div className="rounded-xl border border-border bg-panel p-4">
              <SectionTitle title="Visibility Policies" />
              {policies.length === 0 ? (
                <div className="text-sm text-muted">No policies created yet.</div>
              ) : (
                <div className="space-y-2">
                  {policies.map((p) => (
                    <div key={p.id} className="rounded-lg border border-border p-3 flex items-center justify-between text-sm">
                      <div>
                        <span className="font-medium">{p.data.policy_name || "Unnamed"}</span>
                        <span className="ml-2 text-xs text-muted">v{p.data.version}</span>
                      </div>
                      <Badge color={p.data.active ? "green" : "gray"} label={p.data.active ? "Active" : "Inactive"} />
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-xl border border-border bg-panel p-4">
              <SectionTitle title="Compliance Locks" />
              {complianceLocks.length === 0 ? (
                <div className="text-sm text-muted">No compliance locks active.</div>
              ) : (
                complianceLocks.map((lock) => (
                  <div key={lock.id} className="rounded-lg border border-border p-3 text-sm mb-2">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{lock.data.lock_type} lock</span>
                      <Badge color={lock.data.active ? "red" : "gray"} label={lock.data.active ? "LOCKED" : "Released"} />
                    </div>
                    <div className="text-xs text-muted mt-1">By: {lock.data.locked_by}</div>
                  </div>
                ))
              )}
            </div>

            <div className="rounded-xl border border-border bg-panel p-4">
              <SectionTitle title="Approval Queue" />
              {approvals.length === 0 ? (
                <div className="text-sm text-muted">No pending approvals.</div>
              ) : (
                approvals.map((a) => (
                  <div key={a.id} className="rounded-lg border border-border p-3 text-sm mb-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted">By: {a.data.requested_by}</span>
                      <Badge color={a.data.status === "pending" ? "yellow" : a.data.status === "approved" ? "green" : "red"} label={a.data.status || "pending"} />
                    </div>
                    {a.data.justification && <div className="mt-1 text-xs">{a.data.justification}</div>}
                  </div>
                ))
              )}
            </div>
          </div>
        </Tabs.Content>

        {/* ALERTS */}
        <Tabs.Content value="alerts">
          <div className="space-y-5">
            <div className="rounded-xl border border-border bg-panel p-4">
              <SectionTitle title={`Access Alerts (${alerts.length})`} />
              {alerts.length === 0 ? (
                <div className="text-sm text-muted">No access alerts.</div>
              ) : (
                <div className="space-y-2">
                  {alerts.map((a) => (
                    <div key={a.id} className="rounded-lg border border-border p-3 flex items-start justify-between text-sm">
                      <div>
                        <div className="font-medium">{a.data.alert_type}</div>
                        {a.data.description && <div className="text-xs text-muted mt-0.5">{a.data.description}</div>}
                      </div>
                      <Badge color={a.data.severity === "critical" ? "red" : a.data.severity === "high" ? "red" : a.data.severity === "medium" ? "yellow" : "blue"} label={a.data.severity || "info"} />
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-xl border border-border bg-panel p-4">
              <SectionTitle title={`Anomaly Events (${anomalies.length})`} />
              {anomalies.length === 0 ? (
                <div className="text-sm text-muted">No anomaly events detected.</div>
              ) : (
                <div className="space-y-2">
                  {anomalies.map((a) => (
                    <div key={a.id} className="rounded-lg border border-border p-3 flex items-start justify-between text-sm">
                      <div>
                        <div className="font-medium">{a.data.anomaly_type}</div>
                        {a.data.description && <div className="text-xs text-muted mt-0.5">{a.data.description}</div>}
                      </div>
                      <Badge color={a.data.severity === "high" ? "red" : a.data.severity === "medium" ? "yellow" : "blue"} label={a.data.severity || "low"} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Tabs.Content>

        {/* ADVANCED */}
        <Tabs.Content value="advanced">
          <div className="space-y-4">
            {[
              { title: "Demo Mode", config: { phi_replaced_with_synthetic: true, financial_data_zeroed: true, tenant_id_anonymized: true, safe_to_share_screen: true } },
              { title: "Training Mode", config: { uses_synthetic_data: true, mutations_blocked: true, exports_disabled: true, watermark: "TRAINING DATA - NOT FOR CLINICAL USE" } },
            ].map(({ title, config }) => (
              <div key={title} className="rounded-xl border border-border bg-panel p-4">
                <SectionTitle title={title} />
                <div className="flex flex-wrap gap-2">
                  {Object.entries(config).map(([k, v]) => (
                    <div key={k} className="rounded-lg border border-border px-3 py-1.5 text-xs">
                      <span className="text-muted">{k.replace(/_/g, " ")}: </span>
                      <span className="text-text font-medium">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            <div className="rounded-xl border border-border bg-panel p-4">
              <SectionTitle title="Classification Labels" />
              <div className="flex flex-wrap gap-3">
                {[
                  { label: "PHI", color: "bg-red-900/40 text-red-300 border-red-700", desc: "HIPAA Protected Health Information" },
                  { label: "PII", color: "bg-orange-900/40 text-orange-300 border-orange-700", desc: "Personally Identifiable Information" },
                  { label: "FINANCIAL", color: "bg-yellow-900/40 text-yellow-300 border-yellow-700", desc: "PCI / financial policy" },
                  { label: "OPERATIONAL", color: "bg-blue-900/40 text-blue-300 border-blue-700", desc: "Internal use" },
                  { label: "PUBLIC", color: "bg-green-900/40 text-green-300 border-green-700", desc: "Non-sensitive" },
                ].map(({ label, color, desc }) => (
                  <div key={label} className={`rounded-lg border px-3 py-2 text-xs ${color}`}>
                    <div className="font-semibold">{label}</div>
                    <div className="mt-0.5 opacity-80">{desc}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-border bg-panel p-4">
              <SectionTitle title="Clipboard & Screenshot Policies" />
              <div className="space-y-2 text-sm">
                {[
                  { label: "PHI copy blocked", value: "Always" },
                  { label: "Financial copy restriction", value: "billing+ roles only" },
                  { label: "Screenshot warning", value: "Enabled on sensitive views" },
                  { label: "Read-only safe mode", value: "Available for all roles" },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
                    <span className="text-muted">{label}</span>
                    <span className="text-xs font-medium">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
