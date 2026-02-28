"use client";
import { QuantumTableSkeleton, QuantumCardSkeleton } from '@/components/ui';

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "";

type Template = {
  id: string;
  data: {
    name: string;
    category: string;
    format: string;
    status: string;
    language: string;
    tags: string[];
    is_locked: boolean;
    security_classification: string;
    version: number;
    variables: string[];
  };
  created_at: string;
};

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div
      className="bg-bg-panel border border-border-DEFAULT p-4"
      style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}
    >
      <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-2">{label}</div>
      <div className="text-2xl font-bold" style={{ color: color ?? "var(--color-text-primary)" }}>{value}</div>
    </div>
  );
}

function StatusChip({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "var(--color-brand-orange)",
    approved: "var(--color-status-active)",
    archived: "var(--color-text-muted)",
    rejected: "var(--color-brand-red)",
    pending: "var(--color-status-warning)",
  };
  const color = colors[status] ?? "var(--color-text-muted)";
  return (
    <span
      className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-sm"
      style={{ background: `color-mix(in srgb, ${color} 12%, transparent)`, color, border: `1px solid color-mix(in srgb, ${color} 30%, transparent)` }}
    >
      {status}
    </span>
  );
}

const CATEGORIES = [
  { key: "proposal", label: "Proposal", icon: "P" },
  { key: "contract", label: "Contract", icon: "C" },
  { key: "invoice", label: "Invoice", icon: "I" },
  { key: "appeal", label: "Appeal Letter", icon: "A" },
  { key: "email", label: "Email", icon: "E" },
  { key: "sms", label: "SMS", icon: "S" },
  { key: "voice", label: "Voice Script", icon: "V" },
  { key: "compliance", label: "Compliance", icon: "CO" },
  { key: "report", label: "Report", icon: "R" },
  { key: "general", label: "General", icon: "G" },
];

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [lifecycle, setLifecycle] = useState<Record<string, number>>({});
  const [topPerforming, setTopPerforming] = useState<{ template_id: string; render_count: number }[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCategory, setNewCategory] = useState("general");
  const [newFormat, setNewFormat] = useState("html");
  const [newContent, setNewContent] = useState("");

  useEffect(() => {
    const params = selectedCategory ? `?category=${selectedCategory}` : "";
    fetch(`${API}/api/v1/templates${params}`)
      .then((r) => r.json())
      .then((d) => setTemplates(d.templates ?? []))
      .catch((e: unknown) => { console.warn("[fetch error]", e); })
      .finally(() => setLoading(false));
    fetch(`${API}/api/v1/templates/lifecycle/management`)
      .then((r) => r.json())
      .then(setLifecycle)
      .catch((e: unknown) => { console.warn("[fetch error]", e); });
    fetch(`${API}/api/v1/templates/analytics/top-performing`)
      .then((r) => r.json())
      .then((d) => setTopPerforming(d.top_templates ?? []))
      .catch((e: unknown) => { console.warn("[fetch error]", e); });
  }, [selectedCategory]);

  const handleCreate = async () => {
    try {
      await fetch(`${API}/api/v1/templates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName, category: newCategory, format: newFormat, content: newContent }),
      });
      setCreateOpen(false);
      setNewName("");
      setNewContent("");
    fetch(`${API}/api/v1/templates`)
      .then((r) => r.json())
      .then((d) => setTemplates(d.templates ?? []))
      .catch((e: unknown) => { console.warn("[fetch error]", e); });
    } catch (err: unknown) {
      console.warn("[templates]", err);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await fetch(`${API}/api/v1/templates/${id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template_id: id, action: "approve" }),
      });
      setTemplates((prev) =>
        prev.map((t) => (t.id === id ? { ...t, data: { ...t.data, status: "approved" } } : t))
      );
    } catch (err: unknown) {
      console.warn("[templates]", err);
    }
  };

  const handleArchive = async (id: string) => {
    try {
      await fetch(`${API}/api/v1/templates/${id}`, { method: "DELETE" });
      setTemplates((prev) => prev.filter((t) => t.id !== id));
    } catch (err: unknown) {
      console.warn("[templates]", err);
    }
  };

  return (
    <div className="p-5 space-y-6 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">CATEGORY 6</div>
          <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Template Builder System</h1>
          <p className="text-xs text-text-muted mt-0.5">100-Feature Document Engine · Drag-Drop · Variables · Versioning · Export</p>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="h-9 px-4 bg-[rgba(255,107,26,0.15)] border border-[rgba(255,107,26,0.4)] text-orange text-xs font-semibold rounded-sm hover:bg-[rgba(255,107,26,0.25)] transition-colors"
        >
          + New Template
        </button>
      </div>

      {/* Lifecycle Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MetricCard label="Total Templates" value={String(lifecycle.total ?? templates.length)} color="var(--color-status-info)" />
        <MetricCard label="Draft" value={String(lifecycle.draft ?? "—")} color="var(--color-brand-orange)" />
        <MetricCard label="Approved" value={String(lifecycle.approved ?? "—")} color="var(--color-status-active)" />
        <MetricCard label="Archived" value={String(lifecycle.archived ?? "—")} color="var(--color-text-muted)" />
        <MetricCard label="Locked" value={String(lifecycle.locked ?? "—")} color="var(--color-brand-red)" />
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`h-8 px-3 text-xs font-semibold rounded-sm border transition-colors ${!selectedCategory ? "bg-[rgba(255,107,26,0.2)] border-[rgba(255,107,26,0.5)] text-orange" : "bg-transparent border-border-DEFAULT text-[rgba(255,255,255,0.5)] hover:border-[rgba(255,255,255,0.25)]"}`}
        >
          All
        </button>
        {CATEGORIES.map((cat) => (
          <button
            key={cat.key}
            onClick={() => setSelectedCategory(cat.key)}
            className={`h-8 px-3 text-xs font-semibold rounded-sm border transition-colors ${selectedCategory === cat.key ? "bg-[rgba(255,107,26,0.2)] border-[rgba(255,107,26,0.5)] text-orange" : "bg-transparent border-border-DEFAULT text-[rgba(255,255,255,0.5)] hover:border-[rgba(255,255,255,0.25)]"}`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Template List */}
        <div className="md:col-span-2 space-y-2">
          {loading && <div className="p-6"><QuantumTableSkeleton rows={6} cols={4} /></div>}
          {!loading && templates.length === 0 && (
            <div className="text-xs text-[rgba(255,255,255,0.4)] py-8 text-center">No templates found. Create your first template above.</div>
          )}
          {templates.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-bg-panel border border-border-DEFAULT p-4 hover:border-border-strong transition-colors"
              style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-text-primary truncate">{t.data.name}</span>
                    <StatusChip status={t.data.status} />
                    {t.data.is_locked && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-red-ghost text-red border border-red-ghost rounded-sm font-bold">LOCKED</span>
                    )}
                    {t.data.security_classification !== "standard" && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-[rgba(168,85,247,0.12)] text-system-compliance border border-[rgba(168,85,247,0.3)] rounded-sm font-bold uppercase">{t.data.security_classification}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-1.5 text-[11px] text-[rgba(255,255,255,0.4)]">
                    <span className="uppercase">{t.data.category}</span>
                    <span>·</span>
                    <span className="uppercase">{t.data.format}</span>
                    <span>·</span>
                    <span>v{t.data.version}</span>
                    {t.data.language && t.data.language !== "en" && (
                      <>
                        <span>·</span>
                        <span className="uppercase">{t.data.language}</span>
                      </>
                    )}
                  </div>
                  {t.data.variables.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {t.data.variables.slice(0, 5).map((v) => (
                        <span key={v} className="text-[10px] px-1.5 py-0.5 bg-[rgba(34,211,238,0.08)] text-system-billing border border-[rgba(34,211,238,0.2)] rounded-sm font-mono">{`{{${v}}}`}</span>
                      ))}
                      {t.data.variables.length > 5 && (
                        <span className="text-[10px] text-[rgba(255,255,255,0.3)]">+{t.data.variables.length - 5} more</span>
                      )}
                    </div>
                  )}
                  {t.data.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {t.data.tags.map((tag) => (
                        <span key={tag} className="text-[10px] px-1.5 py-0.5 bg-[rgba(255,255,255,0.05)] text-[rgba(255,255,255,0.4)] rounded-sm">#{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {t.data.status === "draft" && (
                    <button
                      onClick={() => handleApprove(t.id)}
                      className="h-7 px-2 text-[10px] font-semibold border border-[rgba(76,175,80,0.4)] text-status-active rounded-sm hover:bg-[rgba(76,175,80,0.1)] transition-colors"
                    >
                      Approve
                    </button>
                  )}
                  <button
                    onClick={() => handleArchive(t.id)}
                    className="h-7 px-2 text-[10px] font-semibold border border-border-DEFAULT text-[rgba(255,255,255,0.4)] rounded-sm hover:border-[rgba(229,57,53,0.4)] hover:text-red transition-colors"
                  >
                    Archive
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Right Panel */}
        <div className="space-y-4">
          {/* Feature Grid */}
          <div
            className="bg-bg-panel border border-border-DEFAULT p-4"
            style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}
          >
            <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-3">100 Active Features</div>
            <div className="grid grid-cols-2 gap-1.5 text-[10px] text-[rgba(255,255,255,0.55)]">
              {[
                "Drag-drop designer", "Variable injection", "Conditional blocks", "Tenant branding",
                "Module variants", "Role-specific views", "Version history", "Approval workflow",
                "Digital signatures", "E-sign integration", "PDF generation", "DOCX export",
                "Excel output", "PowerPoint builder", "Email templates", "SMS templates",
                "Voice scripts", "AI drafting", "Compliance phrases", "Accreditation mode",
                "Appeal auto-fill", "Proposal builder", "Contract library", "BAA builder",
                "Invoice system", "Payment reminders", "Export notifications", "Audit templates",
                "Legal disclaimers", "Region variations",
              ].map((f) => (
                <div key={f} className="flex items-center gap-1.5">
                  <span className="w-1 h-1 rounded-full bg-status-active flex-shrink-0" />
                  <span className="truncate">{f}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Top Performing */}
          {topPerforming.length > 0 && (
            <div
              className="bg-bg-panel border border-border-DEFAULT p-4"
              style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}
            >
              <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-3">Top Performing</div>
              <div className="space-y-2">
                {topPerforming.slice(0, 5).map((t, i) => (
                  <div key={t.template_id} className="flex items-center justify-between">
                    <span className="text-xs text-[rgba(255,255,255,0.6)] truncate">{t.template_id.slice(0, 8)}…</span>
                    <span className="text-xs font-bold text-system-billing">{t.render_count} renders</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Capabilities */}
          <div
            className="bg-bg-panel border border-border-DEFAULT p-4"
            style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}
          >
            <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-3">Engine Capabilities</div>
            <div className="space-y-2">
              {[
                { label: "Bulk Generation", status: "active" },
                { label: "A/B Testing", status: "active" },
                { label: "Scheduled Delivery", status: "active" },
                { label: "Secure Download Links", status: "active" },
                { label: "Policy Mass Refresh", status: "active" },
                { label: "Dependency Map", status: "active" },
                { label: "AI Tone Optimizer", status: "active" },
                { label: "Version Rollback", status: "active" },
              ].map((cap) => (
                <div key={cap.label} className="flex items-center justify-between">
                  <span className="text-xs text-[rgba(255,255,255,0.6)]">{cap.label}</span>
                  <span className="text-[10px] px-2 py-0.5 bg-[rgba(76,175,80,0.1)] text-status-active border border-[rgba(76,175,80,0.3)] rounded-sm font-bold">ACTIVE</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Create Modal */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(0,0,0,0.7)] p-4">
          <div className="w-full max-w-lg bg-bg-panel border border-[rgba(255,255,255,0.12)] p-6 space-y-4" style={{ clipPath: "polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)" }}>
            <div className="text-sm font-bold text-text-primary uppercase tracking-wider">Create New Template</div>
            <input
              className="w-full bg-bg-void border border-border-DEFAULT text-sm text-text-primary px-3 py-2 rounded-sm focus:outline-none focus:border-orange placeholder-[rgba(255,255,255,0.3)]"
              placeholder="Template name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <div className="grid grid-cols-2 gap-3">
              <select
                className="bg-bg-void border border-border-DEFAULT text-sm text-text-primary px-3 py-2 rounded-sm"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
              >
                {CATEGORIES.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
              </select>
              <select
                className="bg-bg-void border border-border-DEFAULT text-sm text-text-primary px-3 py-2 rounded-sm"
                value={newFormat}
                onChange={(e) => setNewFormat(e.target.value)}
              >
                {["html", "text", "docx", "pdf", "xlsx", "pptx"].map((f) => <option key={f} value={f}>{f.toUpperCase()}</option>)}
              </select>
            </div>
            <textarea
              className="w-full bg-bg-void border border-border-DEFAULT text-sm text-text-primary px-3 py-2 rounded-sm h-28 resize-none focus:outline-none focus:border-orange placeholder-[rgba(255,255,255,0.3)] font-mono"
              placeholder="Template content — use {{variable_name}} for dynamic fields"
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
            />
            <div className="flex justify-end gap-3">
              <button onClick={() => setCreateOpen(false)} className="h-8 px-4 text-xs font-semibold border border-border-DEFAULT text-[rgba(255,255,255,0.5)] rounded-sm hover:border-[rgba(255,255,255,0.25)] transition-colors">Cancel</button>
              <button onClick={handleCreate} disabled={!newName.trim()} className="h-8 px-4 text-xs font-semibold bg-[rgba(255,107,26,0.2)] border border-[rgba(255,107,26,0.5)] text-orange rounded-sm hover:bg-[rgba(255,107,26,0.3)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed">Create Template</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
