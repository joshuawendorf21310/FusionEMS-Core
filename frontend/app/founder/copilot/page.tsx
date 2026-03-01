'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';

const API = '/api/v1/founder/copilot';

type Role = 'user' | 'assistant' | 'system';
interface Message {
  id: string;
  role: Role;
  content_text: string;
  content_json: ActionPlan | null;
  created_at: string;
}
interface Session {
  id: string;
  title: string;
  updated_at: string;
}
interface ActionPlan {
  intent: string;
  summary: string;
  risk_level?: string;
  actions: Action[];
  acceptance_tests: string[];
  notes?: string;
}
interface Action {
  type: string;
  payload: Record<string, unknown>;
}
interface GateResult {
  [key: string]: boolean;
}
interface Run {
  id: string;
  session_id: string;
  status: string;
  plan_json: ActionPlan | null;
  release_gate_results_json: GateResult | null;
  diff_text: string | null;
  gh_run_id: string | null;
  gh_run_url: string | null;
  created_at: string;
  updated_at: string;
}

type RightTab = 'plan' | 'diff' | 'migrations' | 'cloudformation' | 'gate' | 'notes';

const RISK_COLORS: Record<string, string> = {
  low: 'var(--color-status-active)',
  medium: 'var(--color-status-warning)',
  high: 'var(--color-brand-red)',
};

const STATUS_COLORS: Record<string, string> = {
  proposed: 'var(--color-text-muted)',
  running: 'var(--color-status-info)',
  blocked: 'var(--color-brand-red)',
  passed: 'var(--color-status-active)',
  failed: 'var(--color-brand-red)',
  approved: 'var(--color-system-compliance)',
  merged: 'var(--color-brand-orange)',
};

function authHeaders(): HeadersInit {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token') || '';
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch(path: string, opts: RequestInit = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(opts.headers || {}) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function PlanPanel({ plan }: { plan: ActionPlan }) {
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest bg-[rgba(255,107,26,0.15)] text-orange rounded">
          {plan.intent}
        </span>
        {plan.risk_level && (
          <span
            className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest rounded"
            style={{ background: `color-mix(in srgb, ${RISK_COLORS[plan.risk_level]} 13%, transparent)`, color: RISK_COLORS[plan.risk_level] }}
          >
            {plan.risk_level} risk
          </span>
        )}
      </div>
      <p className="text-sm text-[rgba(255,255,255,0.85)]">{plan.summary}</p>

      <div>
        <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-2">
          Actions ({plan.actions.length})
        </div>
        <div className="space-y-2">
          {plan.actions.map((a, i) => (
            <div key={i} className="bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT rounded p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-mono font-bold text-status-info">{a.type}</span>
              </div>
              <pre className="text-[10px] text-[rgba(255,255,255,0.55)] whitespace-pre-wrap break-all">
                {JSON.stringify(a.payload, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-2">
          Acceptance Tests
        </div>
        <div className="space-y-1">
          {plan.acceptance_tests.map((t, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-status-active text-xs">✓</span>
              <code className="text-xs text-[rgba(255,255,255,0.7)] font-mono">{t}</code>
            </div>
          ))}
        </div>
      </div>

      {plan.notes && (
        <div className="bg-[rgba(255,107,26,0.06)] border border-[rgba(255,107,26,0.15)] rounded p-3">
          <div className="text-[10px] uppercase tracking-widest text-orange-dim mb-1">Notes</div>
          <p className="text-xs text-text-secondary">{plan.notes}</p>
        </div>
      )}
    </div>
  );
}

function GatePanel({ results }: { results: GateResult | null }) {
  if (!results) {
    return (
      <div className="p-4 text-sm text-[rgba(255,255,255,0.35)] italic">
        No gate results yet. Execute the run to trigger release gates.
      </div>
    );
  }
  const entries = Object.entries(results);
  const allPassed = entries.every(([, v]) => v);
  return (
    <div className="p-4 space-y-3">
      <div
        className="text-xs font-bold uppercase tracking-widest px-3 py-2 rounded"
        style={{
          background: allPassed ? 'rgba(76,175,80,0.1)' : 'rgba(229,57,53,0.1)',
          color: allPassed ? 'var(--color-status-active)' : 'var(--color-brand-red)',
          border: `1px solid ${allPassed ? 'rgba(76,175,80,0.3)' : 'rgba(229,57,53,0.3)'}`,
        }}
      >
        {allPassed ? '✓ All gates passed' : `✗ ${entries.filter(([, v]) => !v).length} gate(s) failed`}
      </div>
      <div className="space-y-1">
        {entries.map(([gate, passed]) => (
          <div key={gate} className="flex items-center gap-3 py-1.5 border-b border-border-subtle">
            <span className={`text-sm ${passed ? 'text-status-active' : 'text-red'}`}>
              {passed ? '✓' : '✗'}
            </span>
            <span className="text-xs font-mono text-[rgba(255,255,255,0.7)]">{gate}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DiffPanel({ diffText }: { diffText: string | null }) {
  if (!diffText) {
    return (
      <div className="p-4 text-sm text-[rgba(255,255,255,0.35)] italic">
        No diff available yet.
      </div>
    );
  }
  return (
    <div className="p-4">
      <pre className="text-[11px] font-mono whitespace-pre-wrap break-all leading-5">
        {diffText.split('\n').map((line, i) => {
          let color = 'rgba(255,255,255,0.6)';
          if (line.startsWith('+') && !line.startsWith('+++')) color = 'var(--color-status-active)';
          else if (line.startsWith('-') && !line.startsWith('---')) color = 'var(--color-brand-red)';
          else if (line.startsWith('@@')) color = 'var(--color-status-info)';
          return (
            <span key={i} style={{ color }} className="block">
              {line}
            </span>
          );
        })}
      </pre>
    </div>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      {!isUser && (
        <div className="w-6 h-6 flex-shrink-0 rounded-full bg-[rgba(255,107,26,0.2)] border border-[rgba(255,107,26,0.4)] flex items-center justify-center text-[9px] font-bold text-orange mr-2 mt-0.5">
          AI
        </div>
      )}
      <div
        className={`max-w-[80%] px-3 py-2 rounded text-sm leading-relaxed ${
          isUser
            ? 'bg-orange-ghost border border-[rgba(255,107,26,0.2)] text-text-primary'
            : 'bg-[rgba(255,255,255,0.05)] border border-border-DEFAULT text-[rgba(255,255,255,0.85)]'
        }`}
      >
        <p className="whitespace-pre-wrap">{msg.content_text}</p>
        {msg.content_json && (
          <div className="mt-2 pt-2 border-t border-border-DEFAULT">
            <span className="text-[10px] text-orange font-semibold uppercase tracking-wider">
              ▣ Action plan attached — see right panel
            </span>
          </div>
        )}
        <div className="mt-1 text-[10px] text-[rgba(255,255,255,0.25)]">
          {new Date(msg.created_at).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}

export default function FounderCopilotPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [rightTab, setRightTab] = useState<RightTab>('plan');
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    apiFetch(`${API}/sessions`)
      .then((d) => setSessions(d.sessions || []))
      .catch((e: unknown) => { setError(e instanceof Error ? e.message : "Request failed"); });
  }, []);

  const loadMessages = useCallback(async (sessionId: string) => {
    try {
      const d = await apiFetch(`${API}/sessions/${sessionId}/messages`);
      setMessages(d.messages || []);
    } catch (e: unknown) { console.warn("[fetch error]", e); }
  }, []);

  const selectSession = useCallback(
    async (session: Session) => {
      setActiveSession(session);
      setActiveRun(null);
      await loadMessages(session.id);
    },
    [loadMessages]
  );

  const newSession = useCallback(async () => {
    try {
      const s = await apiFetch(`${API}/sessions`, {
        method: 'POST',
        body: JSON.stringify({ title: 'New session' }),
      });
      setSessions((prev) => [s, ...prev]);
      setActiveSession(s);
      setMessages([]);
      setActiveRun(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create session');
    }
  }, []);

  const sendMessage = useCallback(async () => {
    if (!activeSession || !inputText.trim() || sending) return;
    const text = inputText.trim();
    setInputText('');
    setSending(true);
    setError(null);
    const tempMsg: Message = {
      id: `tmp-${Date.now()}`,
      role: 'user',
      content_text: text,
      content_json: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempMsg]);
    try {
      const d = await apiFetch(`${API}/sessions/${activeSession.id}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content: text }),
      });
      const assistantMsg: Message = d.message;
      if (d.action_plan) assistantMsg.content_json = d.action_plan;
      setMessages((prev) => [...prev.filter((m) => m.id !== tempMsg.id), assistantMsg]);
      if (d.action_plan) setRightTab('plan');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to send message');
      setMessages((prev) => prev.filter((m) => m.id !== tempMsg.id));
    } finally {
      setSending(false);
    }
  }, [activeSession, inputText, sending]);

  const proposeRun = useCallback(async () => {
    if (!activeSession) return;
    const lastPlan = [...messages].reverse().find((m) => m.content_json);
    if (!lastPlan?.content_json) {
      setError('No action plan in this session yet. Ask the AI to propose a change first.');
      return;
    }
    try {
      const run = await apiFetch(`${API}/sessions/${activeSession.id}/runs/propose`, {
        method: 'POST',
        body: JSON.stringify({ plan: lastPlan.content_json }),
      });
      setActiveRun(run);
      setRightTab('plan');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to propose run');
    }
  }, [activeSession, messages]);

  const executeRun = useCallback(async () => {
    if (!activeRun) return;
    setExecuting(true);
    setError(null);
    try {
      const result = await apiFetch(`${API}/runs/${activeRun.id}/execute`, {
        method: 'POST',
        body: JSON.stringify({ ref: 'verdent-upgrades' }),
      });
      setActiveRun((prev) => prev ? { ...prev, status: result.status, gh_run_id: result.gh_run_id, gh_run_url: result.gh_run_url } : prev);
      setRightTab('gate');
      startPolling(activeRun.id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to execute run');
    } finally {
      setExecuting(false);
    }
  }, [activeRun]);

  const startPolling = useCallback((runId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const d = await apiFetch(`${API}/runs/${runId}`);
        setActiveRun(d.run);
        if (['passed', 'blocked', 'failed', 'approved', 'merged'].includes(d.run.status)) {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch (e: unknown) { console.warn("[fetch error]", e); }
    }, 5000);
  }, []);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const approveRun = useCallback(async () => {
    if (!activeRun) return;
    try {
      const result = await apiFetch(`${API}/runs/${activeRun.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      setActiveRun((prev) => prev ? { ...prev, status: result.status } : prev);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to approve run');
    }
  }, [activeRun]);

  const mergeRun = useCallback(async () => {
    if (!activeRun) return;
    try {
      const result = await apiFetch(`${API}/runs/${activeRun.id}/merge`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      setActiveRun((prev) => prev ? { ...prev, status: result.status } : prev);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to merge run');
    }
  }, [activeRun]);

  const exportPatch = useCallback(() => {
    if (!activeRun?.diff_text) return;
    const blob = new Blob([activeRun.diff_text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `patch-${activeRun.id.slice(0, 8)}.diff`;
    a.click();
    URL.revokeObjectURL(url);
  }, [activeRun]);

  const currentPlan = activeRun?.plan_json ?? [...messages].reverse().find((m) => m.content_json)?.content_json ?? null;

  const RIGHT_TABS: { id: RightTab; label: string }[] = [
    { id: 'plan', label: 'Plan' },
    { id: 'diff', label: 'Diff' },
    { id: 'migrations', label: 'Migrations' },
    { id: 'cloudformation', label: 'CloudFormation' },
    { id: 'gate', label: 'Release Gate' },
    { id: 'notes', label: 'Deploy Notes' },
  ];

  return (
    <div className="flex h-full bg-bg-base text-text-primary overflow-hidden" style={{ minHeight: 0 }}>
      {/* Session list */}
      <aside className="w-52 flex-shrink-0 border-r border-border-subtle flex flex-col bg-bg-void">
        <div className="flex items-center justify-between px-3 py-3 border-b border-border-subtle">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,107,26,0.9)]">
            Copilot Sessions
          </span>
          <button
            onClick={newSession}
            className="w-6 h-6 bg-[rgba(255,107,26,0.15)] border border-[rgba(255,107,26,0.3)] text-orange text-xs rounded hover:bg-[rgba(255,107,26,0.25)] transition-colors flex items-center justify-center"
            title="New session"
          >
            +
          </button>
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {sessions.length === 0 && (
            <div className="px-3 py-4 text-xs text-[rgba(255,255,255,0.3)] italic">No sessions yet</div>
          )}
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => selectSession(s)}
              className={`w-full text-left px-3 py-2 border-b border-border-subtle transition-colors ${
                activeSession?.id === s.id
                  ? 'bg-orange-ghost text-text-primary border-l-2 border-l-[var(--color-brand-orange)]'
                  : 'text-[rgba(255,255,255,0.55)] hover:bg-[rgba(255,255,255,0.04)] hover:text-text-primary'
              }`}
            >
              <div className="text-xs truncate">{s.title}</div>
              <div className="text-[10px] text-[rgba(255,255,255,0.25)] mt-0.5">
                {new Date(s.updated_at).toLocaleDateString()}
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* Chat column */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Chat header */}
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border-subtle bg-bg-void flex-shrink-0">
          <div>
            <div className="text-sm font-semibold">Founder Copilot</div>
            <div className="text-[10px] text-[rgba(255,255,255,0.35)]">
              {activeSession ? activeSession.title : 'Select or start a session'}
            </div>
          </div>
          {activeRun && (
            <div className="ml-auto flex items-center gap-2">
              <span className="text-[10px] text-[rgba(255,255,255,0.4)]">RUN</span>
              <span
                className="px-2 py-0.5 text-[10px] font-bold uppercase rounded"
                style={{
                  background: `color-mix(in srgb, ${STATUS_COLORS[activeRun.status] || 'var(--color-text-muted)'} 13%, transparent)`,
                  color: STATUS_COLORS[activeRun.status] || 'var(--color-text-muted)',
                    border: `1px solid color-mix(in srgb, ${STATUS_COLORS[activeRun.status] || 'var(--color-text-muted)'} 27%, transparent)`,
                }}
              >
                {activeRun.status}
              </span>
              {activeRun.gh_run_url && (
                <a
                  href={activeRun.gh_run_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-status-info hover:underline"
                >
                  GH Actions ↗
                </a>
              )}
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {!activeSession && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-12 h-12 bg-[rgba(255,107,26,0.1)] border border-[rgba(255,107,26,0.2)] rounded-full flex items-center justify-center mb-4">
                <span className="text-2xl">◈</span>
              </div>
              <p className="text-sm text-[rgba(255,255,255,0.5)] mb-2">Founder Copilot</p>
              <p className="text-xs text-[rgba(255,255,255,0.3)] max-w-sm">
                Start a new session to ask questions, generate plans, or propose code changes. All changes are staged and require your approval.
              </p>
              <button
                onClick={newSession}
                className="mt-4 px-4 py-2 bg-[rgba(255,107,26,0.15)] border border-[rgba(255,107,26,0.3)] text-orange text-xs font-semibold rounded hover:bg-[rgba(255,107,26,0.25)] transition-colors"
              >
                + New Session
              </button>
            </div>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Error */}
        {error && (
          <div className="mx-4 mb-2 px-3 py-2 bg-red-ghost border border-red-ghost rounded text-xs text-red-bright flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-2 text-[rgba(255,255,255,0.4)] hover:text-text-primary">✕</button>
          </div>
        )}

        {/* Action bar */}
        {activeSession && (
          <div className="flex-shrink-0 px-4 pb-4 space-y-2">
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={proposeRun}
                disabled={!messages.some((m) => m.content_json)}
                className="px-3 py-1.5 text-xs font-semibold bg-orange-ghost border border-[rgba(255,107,26,0.3)] text-orange rounded hover:bg-[rgba(255,107,26,0.2)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Propose Changes
              </button>
              <button
                onClick={executeRun}
                disabled={!activeRun || !['proposed', 'blocked'].includes(activeRun.status) || executing}
                className="px-3 py-1.5 text-xs font-semibold bg-[rgba(41,182,246,0.12)] border border-[rgba(41,182,246,0.3)] text-status-info rounded hover:bg-[rgba(41,182,246,0.2)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {executing ? 'Executing…' : 'Execute in Sandbox'}
              </button>
              <button
                onClick={approveRun}
                disabled={!activeRun || activeRun.status !== 'passed'}
                className="px-3 py-1.5 text-xs font-semibold bg-[rgba(168,85,247,0.12)] border border-[rgba(168,85,247,0.3)] text-system-compliance rounded hover:bg-[rgba(168,85,247,0.2)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Approve
              </button>
              <button
                onClick={mergeRun}
                disabled={!activeRun || activeRun.status !== 'approved'}
                className="px-3 py-1.5 text-xs font-semibold bg-orange-ghost border border-[rgba(255,107,26,0.4)] text-orange rounded hover:bg-[rgba(255,107,26,0.2)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Merge when Green
              </button>
              <button
                onClick={exportPatch}
                disabled={!activeRun?.diff_text}
                className="px-3 py-1.5 text-xs font-semibold bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.12)] text-[rgba(255,255,255,0.6)] rounded hover:bg-[rgba(255,255,255,0.09)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Export Patch
              </button>
            </div>

            <div className="flex gap-2">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="Ask Founder Copilot… (Shift+Enter for newline)"
                rows={2}
                className="flex-1 bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT px-3 py-2 text-sm text-text-primary placeholder-[rgba(255,255,255,0.25)] rounded resize-none focus:outline-none focus:border-orange transition-colors"
              />
              <button
                onClick={sendMessage}
                disabled={sending || !inputText.trim()}
                className="px-4 bg-orange text-text-inverse text-xs font-bold rounded hover:bg-orange-bright transition-colors disabled:opacity-40 disabled:cursor-not-allowed self-stretch"
              >
                {sending ? '…' : 'Send'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Right panel */}
      <aside className="w-96 flex-shrink-0 border-l border-border-subtle flex flex-col bg-bg-void">
        <div className="flex border-b border-border-subtle overflow-x-auto flex-shrink-0">
          {RIGHT_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setRightTab(tab.id)}
              className={`px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wider whitespace-nowrap transition-colors flex-shrink-0 ${
                rightTab === tab.id
                  ? 'text-orange border-b-2 border-orange'
                  : 'text-[rgba(255,255,255,0.35)] hover:text-[rgba(255,255,255,0.7)]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto">
          {rightTab === 'plan' && (currentPlan ? <PlanPanel plan={currentPlan} /> : (
            <div className="p-4 text-sm text-[rgba(255,255,255,0.35)] italic">No plan yet. Ask the copilot to propose a change.</div>
          ))}
          {rightTab === 'diff' && <DiffPanel diffText={activeRun?.diff_text ?? null} />}
          {rightTab === 'migrations' && (
            <div className="p-4 space-y-3">
              {currentPlan?.actions.filter((a) => a.type === 'GENERATE_MIGRATION').length ? (
                currentPlan.actions.filter((a) => a.type === 'GENERATE_MIGRATION').map((a, i) => (
                  <div key={i} className="bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT rounded p-3">
                    <div className="text-[10px] text-status-info font-bold mb-1">GENERATE_MIGRATION</div>
                    <pre className="text-[10px] text-[rgba(255,255,255,0.6)] whitespace-pre-wrap">{JSON.stringify(a.payload, null, 2)}</pre>
                  </div>
                ))
              ) : (
                <div className="text-sm text-[rgba(255,255,255,0.35)] italic">No migration actions in this plan.</div>
              )}
            </div>
          )}
          {rightTab === 'cloudformation' && (
            <div className="p-4 space-y-3">
              {currentPlan?.actions.filter((a) => a.type === 'UPDATE_CLOUDFORMATION').length ? (
                currentPlan.actions.filter((a) => a.type === 'UPDATE_CLOUDFORMATION').map((a, i) => (
                  <div key={i} className="bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT rounded p-3">
                    <div className="text-[10px] text-status-warning font-bold mb-1">UPDATE_CLOUDFORMATION</div>
                    <pre className="text-[10px] text-[rgba(255,255,255,0.6)] whitespace-pre-wrap">{String((a.payload as Record<string, unknown>).patch || JSON.stringify(a.payload, null, 2))}</pre>
                  </div>
                ))
              ) : (
                <div className="text-sm text-[rgba(255,255,255,0.35)] italic">No CloudFormation actions in this plan.</div>
              )}
            </div>
          )}
          {rightTab === 'gate' && <GatePanel results={activeRun?.release_gate_results_json ?? null} />}
          {rightTab === 'notes' && (
            <div className="p-4 space-y-3">
              {activeRun ? (
                <>
                  <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-2">Run Details</div>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between"><span className="text-[rgba(255,255,255,0.4)]">Run ID</span><code className="text-[rgba(255,255,255,0.7)] font-mono text-[10px]">{activeRun.id.slice(0, 12)}…</code></div>
                    <div className="flex justify-between"><span className="text-[rgba(255,255,255,0.4)]">Status</span><span style={{ color: STATUS_COLORS[activeRun.status] || 'var(--color-text-muted)' }} className="font-semibold">{activeRun.status}</span></div>
                    <div className="flex justify-between"><span className="text-[rgba(255,255,255,0.4)]">Created</span><span className="text-[rgba(255,255,255,0.7)]">{new Date(activeRun.created_at).toLocaleString()}</span></div>
                    {activeRun.gh_run_url && <div className="pt-2"><a href={activeRun.gh_run_url} target="_blank" rel="noopener noreferrer" className="text-status-info hover:underline text-xs">View GitHub Actions run ↗</a></div>}
                  </div>
                  {currentPlan?.summary && (
                    <div className="mt-4 p-3 bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT rounded">
                      <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-1">Summary</div>
                      <p className="text-xs text-[rgba(255,255,255,0.7)]">{currentPlan.summary}</p>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-sm text-[rgba(255,255,255,0.35)] italic">No run active.</div>
              )}
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
