"use client";

import { useEffect, useMemo, useState } from "react";

type Health = { status: string; time: string; version?: string };
type ModuleHealth = { module: string; ok: boolean; detail?: string };
type FounderStatus = {
  founderEmail: string;
  modules: ModuleHealth[];
  realtime: { connected: boolean };
};

const DEFAULT_EMAIL = "josh@yourdomain.com";

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-panel p-5">
      <div className="text-sm font-semibold">{title}</div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || "http://localhost:8000";
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  const text = await res.text();
  const json = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error(json?.detail ?? `Request failed: ${res.status}`);
  return json as T;
}

export default function Founder() {
  const [health, setHealth] = useState<Health | null>(null);
  const [status, setStatus] = useState<FounderStatus | null>(null);
  const [email, setEmail] = useState(DEFAULT_EMAIL);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [keys, setKeys] = useState({
    openai_api_key: "",
    telnyx_api_key: "",
    telnyx_public_key: "",
    stripe_secret_key: "",
    lob_api_key: "",
    ses_from_email: DEFAULT_EMAIL,
  });

  const [doc, setDoc] = useState({ title: "Invoice", body: "Enter content…" });

  useEffect(() => {
    api<Health>("/api/v1/health").then(setHealth).catch(() => api<Health>("/health").then(setHealth).catch(() => null));
    api<FounderStatus>("/api/v1/founder/status").then(s => { setStatus(s); setEmail(s.founderEmail || DEFAULT_EMAIL); }).catch(() => null);
  }, []);

  async function saveSettings() {
    setErr(null);
    setSaving(true);
    try {
      await api("/api/v1/founder/settings", { method: "POST", body: JSON.stringify({ founder_email: email, keys }) });
      const s = await api<FounderStatus>("/api/v1/founder/status");
      setStatus(s);
    } catch (e: any) {
      setErr(e?.message ?? "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function createDoc(kind: "word" | "excel" | "invoice") {
    setErr(null);
    try {
      const res = await api<{ download_url: string }>("/api/v1/founder/documents", {
        method: "POST",
        body: JSON.stringify({ kind, title: doc.title, body: doc.body })
      });
      window.open(res.download_url, "_blank");
    } catch (e: any) {
      setErr(e?.message ?? "Failed to create document");
    }
  }

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-border bg-panel p-6">
        <div className="text-xl font-semibold">Founder Command Center</div>
        <div className="mt-2 text-sm text-muted">
          Single-operator billing + communication control wall. Real-time ready. Keys configured here.
        </div>
        {health && (
          <div className="mt-4 text-xs text-muted">Backend Health: {health.status} · {health.time}</div>
        )}
        {err && <div className="mt-4 rounded-xl border border-[rgba(239,68,68,0.35)] bg-[rgba(239,68,68,0.10)] p-3 text-sm">{err}</div>}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Panel title="Identity & Email">
          <div className="space-y-3">
            <label className="block text-xs text-muted">Founder email (display + notifications)</label>
            <input value={email} onChange={e => setEmail(e.target.value)} className="w-full rounded-xl border border-border bg-panel2 px-3 py-2 text-sm" />
            <div className="text-xs text-muted">Used for receipts, statement notifications, and system alerts.</div>
          </div>
        </Panel>

        <Panel title="Module Health">
          <div className="space-y-2 text-sm">
            {(status?.modules ?? []).map(m => (
              <div key={m.module} className="flex items-center justify-between rounded-xl border border-border bg-panel2 px-3 py-2">
                <div className="text-muted">{m.module}</div>
                <div className={m.ok ? "text-[rgba(34,211,238,0.95)]" : "text-[rgba(251,146,60,0.95)]"}>
                  {m.ok ? "OK" : "Needs config"}
                </div>
              </div>
            ))}
            {!status && <div className="text-xs text-muted">Status will populate after first save.</div>}
          </div>
        </Panel>

        <Panel title="API Keys (validated on save)">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {Object.entries(keys).map(([k,v]) => (
              <div key={k} className="space-y-1">
                <div className="text-xs text-muted">{k}</div>
                <input
                  value={v}
                  onChange={e => setKeys(prev => ({ ...prev, [k]: e.target.value }))}
                  className="w-full rounded-xl border border-border bg-panel2 px-3 py-2 text-sm"
                />
              </div>
            ))}
          </div>
          <button
            onClick={saveSettings}
            disabled={saving}
            className="mt-4 rounded-xl bg-billing px-4 py-2 text-sm font-semibold text-black disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save & Validate Keys"}
          </button>
          <div className="mt-2 text-xs text-muted">Keys are stored encrypted at rest on the backend. Never stored in browser storage.</div>
        </Panel>

        <Panel title="Documents: Word / Excel / Invoice Creator">
          <div className="space-y-3">
            <input
              value={doc.title}
              onChange={e => setDoc(prev => ({ ...prev, title: e.target.value }))}
              className="w-full rounded-xl border border-border bg-panel2 px-3 py-2 text-sm"
              placeholder="Document title"
            />
            <textarea
              value={doc.body}
              onChange={e => setDoc(prev => ({ ...prev, body: e.target.value }))}
              className="h-36 w-full rounded-xl border border-border bg-panel2 px-3 py-2 text-sm"
            />
            <div className="flex flex-wrap gap-2">
              <button onClick={() => createDoc("word")} className="rounded-xl border border-border px-4 py-2 text-sm">Create Word</button>
              <button onClick={() => createDoc("excel")} className="rounded-xl border border-border px-4 py-2 text-sm">Create Excel</button>
              <button onClick={() => createDoc("invoice")} className="rounded-xl border border-border px-4 py-2 text-sm">Create Invoice PDF</button>
            </div>
            <div className="text-xs text-muted">Created files are generated server-side and returned as signed download URLs.</div>
          </div>
        </Panel>
      </div>

      <div className="rounded-2xl border border-border bg-panel p-5">
        <div className="text-sm font-semibold">AI Operations Console (Governed)</div>
        <div className="mt-2 text-xs text-muted">
          This console is designed for supervised actions only. No automatic financial posting or clinical edits without confirmation.
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <a className="rounded-xl border border-border bg-panel2 px-4 py-3 text-sm" href="/billing/dashboard">Billing War Room</a>
          <a className="rounded-xl border border-border bg-panel2 px-4 py-3 text-sm" href="/billing/claims">Claims Queue</a>
          <a className="rounded-xl border border-border bg-panel2 px-4 py-3 text-sm" href="/billing/reports">Revenue Analytics</a>
        </div>
      </div>
    </div>
  );
}
