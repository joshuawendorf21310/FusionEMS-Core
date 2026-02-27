'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return 'Bearer ' + (localStorage.getItem('qs_token') || '');
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

type ThreadStatus = 'open' | 'escalated' | 'resolved';
type FilterTab = 'all' | 'escalated' | 'open' | 'resolved';

interface SupportThread {
  id: string;
  status: ThreadStatus;
  unread: boolean;
  escalated: boolean;
  updated_at: string;
  data: {
    title?: string;
    context?: {
      agency_name?: string;
    };
    last_message?: string;
  };
}

interface SupportMessage {
  id: string;
  sender_role: 'agency' | 'founder' | 'ai';
  content: string;
  created_at: string;
}

// ─── Toast ────────────────────────────────────────────────────────────────────
interface ToastItem {
  id: number;
  msg: string;
  type: 'success' | 'error';
}

function Toast({ items }: { items: ToastItem[] }) {
  if (!items.length) return null;
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
      {items.map((t) => (
        <div
          key={t.id}
          className="px-4 py-2.5 rounded-sm text-xs font-semibold shadow-lg"
          style={{
            background: t.type === 'success' ? 'rgba(76,175,80,0.18)' : 'rgba(229,57,53,0.18)',
            border: `1px solid ${t.type === 'success' ? 'rgba(76,175,80,0.4)' : 'rgba(229,57,53,0.4)'}`,
            color: t.type === 'success' ? '#4caf50' : '#e53935',
          }}
        >
          {t.msg}
        </div>
      ))}
    </div>
  );
}

function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const push = useCallback((msg: string, type: 'success' | 'error' = 'success') => {
    const id = ++counter.current;
    setToasts((prev) => [...prev, { id, msg, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3000);
  }, []);

  return { toasts, push };
}

// ─── Status badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: ThreadStatus }) {
  const map: Record<ThreadStatus, { label: string; color: string; bg: string }> = {
    open: { label: 'OPEN', color: '#22d3ee', bg: 'rgba(34,211,238,0.12)' },
    escalated: { label: 'ESCALATED', color: '#e53935', bg: 'rgba(229,57,53,0.12)' },
    resolved: { label: 'RESOLVED', color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.06)' },
  };
  const s = map[status];
  return (
    <span
      className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
      style={{ color: s.color, background: s.bg }}
    >
      {s.label}
    </span>
  );
}

export default function SupportInboxPage() {
  const [threads, setThreads] = useState<SupportThread[]>([]);
  const [filter, setFilter] = useState<FilterTab>('all');
  const [activeThread, setActiveThread] = useState<SupportThread | null>(null);
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [replyText, setReplyText] = useState('');
  const [summary, setSummary] = useState<string | null>(null);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sendingReply, setSendingReply] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [summarizing, setSummarizing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toasts, push: pushToast } = useToast();

  // ── Fetch threads ──────────────────────────────────────────────────────────
  const fetchThreads = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/support/founder/inbox?status=open&limit=50`, {
        headers: { Authorization: getToken() },
      });
      if (!res.ok) throw new Error('Failed to load threads');
      const data = await res.json();
      setThreads(Array.isArray(data) ? data : data.threads ?? []);
    } catch {
      // silently keep stale data on auto-refresh
    }
  }, []);

  useEffect(() => {
    fetchThreads();
    const interval = setInterval(fetchThreads, 30000);
    return () => clearInterval(interval);
  }, [fetchThreads]);

  // ── Fetch messages for selected thread ────────────────────────────────────
  const fetchMessages = useCallback(async (threadId: string) => {
    setLoadingMessages(true);
    setSummary(null);
    setSummaryOpen(false);
    try {
      const res = await fetch(`${API}/api/v1/support/founder/threads/${threadId}/messages`, {
        headers: { Authorization: getToken() },
      });
      if (!res.ok) throw new Error('Failed to load messages');
      const data = await res.json();
      setMessages(Array.isArray(data) ? data : data.messages ?? []);
    } catch {
      pushToast('Failed to load messages', 'error');
    } finally {
      setLoadingMessages(false);
    }
  }, [pushToast]);

  useEffect(() => {
    if (activeThread) fetchMessages(activeThread.id);
  }, [activeThread, fetchMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Send reply ─────────────────────────────────────────────────────────────
  async function sendReply() {
    if (!activeThread || !replyText.trim()) return;
    setSendingReply(true);
    try {
      const res = await fetch(`${API}/api/v1/support/founder/threads/${activeThread.id}/reply`, {
        method: 'POST',
        headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: replyText.trim() }),
      });
      if (!res.ok) throw new Error();
      setReplyText('');
      await fetchMessages(activeThread.id);
      pushToast('Reply sent', 'success');
    } catch {
      pushToast('Failed to send reply', 'error');
    } finally {
      setSendingReply(false);
    }
  }

  // ── Resolve thread ─────────────────────────────────────────────────────────
  async function resolveThread(thread: SupportThread) {
    setResolvingId(thread.id);
    try {
      const res = await fetch(`${API}/api/v1/support/founder/threads/${thread.id}/resolve`, {
        method: 'POST',
        headers: { Authorization: getToken() },
      });
      if (!res.ok) throw new Error();
      pushToast('Thread resolved', 'success');
      await fetchThreads();
      if (activeThread?.id === thread.id) {
        setActiveThread((prev) => prev ? { ...prev, status: 'resolved' } : null);
      }
    } catch {
      pushToast('Failed to resolve thread', 'error');
    } finally {
      setResolvingId(null);
    }
  }

  // ── AI Summarize ───────────────────────────────────────────────────────────
  async function summarizeThread() {
    if (!activeThread) return;
    setSummarizing(true);
    try {
      const res = await fetch(`${API}/api/v1/support/founder/threads/${activeThread.id}/summarize`, {
        method: 'POST',
        headers: { Authorization: getToken() },
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setSummary(data.summary ?? data.content ?? JSON.stringify(data));
      setSummaryOpen(true);
    } catch {
      pushToast('Summarize failed', 'error');
    } finally {
      setSummarizing(false);
    }
  }

  // ── Derived data ───────────────────────────────────────────────────────────
  const filteredThreads = threads.filter((t) => {
    if (filter === 'all') return true;
    if (filter === 'escalated') return t.escalated || t.status === 'escalated';
    return t.status === filter;
  });

  const unreadCount = threads.filter((t) => t.unread).length;

  function agencyName(t: SupportThread): string {
    return t.data?.context?.agency_name || t.data?.title || 'Unknown Agency';
  }

  function lastPreview(t: SupportThread): string {
    const raw = t.data?.last_message ?? '';
    return raw.length > 60 ? raw.slice(0, 60) + '…' : raw;
  }

  const FILTER_TABS: { key: FilterTab; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'escalated', label: 'Escalated' },
    { key: 'open', label: 'Open' },
    { key: 'resolved', label: 'Resolved' },
  ];

  return (
    <div className="min-h-screen bg-[#07090d] text-white flex flex-col">
      <Toast items={toasts} />

      {/* Page header */}
      <div className="px-5 pt-5 pb-4 border-b border-[rgba(255,255,255,0.06)]">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-black uppercase tracking-[0.18em] text-white">
            SUPPORT INBOX
          </h1>
          {unreadCount > 0 && (
            <span
              className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-sm"
              style={{ background: 'rgba(255,107,26,0.18)', color: '#ff6b1a' }}
            >
              {unreadCount} unread
            </span>
          )}
          <div className="ml-auto flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#4caf50] animate-pulse" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#4caf50]">LIVE</span>
          </div>
        </div>
        <p className="text-[11px] text-[rgba(255,255,255,0.38)] mt-0.5">
          Agency support threads · real-time · AI assist
        </p>
      </div>

      {/* Two-panel layout */}
      <div className="flex flex-1 overflow-hidden" style={{ height: 'calc(100vh - 90px)' }}>

        {/* ── LEFT: Thread list (300px) ───────────────────────────────────── */}
        <div
          className="flex flex-col border-r border-[rgba(255,255,255,0.08)]"
          style={{ width: 300, minWidth: 300, flexShrink: 0 }}
        >
          {/* Filter tabs */}
          <div className="flex border-b border-[rgba(255,255,255,0.06)] px-2 pt-2 pb-0 gap-0.5">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key)}
                className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider transition-colors"
                style={{
                  color: filter === tab.key ? '#ff6b1a' : 'rgba(255,255,255,0.38)',
                  borderBottom: filter === tab.key ? '2px solid #ff6b1a' : '2px solid transparent',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Thread list */}
          <div className="flex-1 overflow-y-auto">
            {filteredThreads.length === 0 && (
              <div className="p-4 text-[11px] text-[rgba(255,255,255,0.3)] text-center mt-8">
                No threads in this view
              </div>
            )}
            {filteredThreads.map((thread) => {
              const isActive = activeThread?.id === thread.id;
              return (
                <button
                  key={thread.id}
                  onClick={() => setActiveThread(thread)}
                  className="w-full text-left px-3 py-3 border-b border-[rgba(255,255,255,0.05)] transition-colors hover:bg-[rgba(255,255,255,0.03)]"
                  style={{
                    background: isActive ? 'rgba(255,107,26,0.06)' : 'transparent',
                    borderLeft: isActive ? '3px solid #ff6b1a' : '3px solid transparent',
                  }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-white truncate flex-1">
                      {agencyName(thread)}
                    </span>
                    {thread.unread && (
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: '#ff6b1a' }} />
                    )}
                    {(thread.escalated || thread.status === 'escalated') && (
                      <span
                        className="px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider rounded-sm flex-shrink-0"
                        style={{ background: 'rgba(229,57,53,0.15)', color: '#e53935' }}
                      >
                        ESC
                      </span>
                    )}
                  </div>
                  <div className="flex items-end justify-between gap-2">
                    <p className="text-[11px] text-[rgba(255,255,255,0.45)] leading-snug flex-1 min-w-0 truncate">
                      {lastPreview(thread)}
                    </p>
                    <span className="text-[10px] text-[rgba(255,255,255,0.28)] whitespace-nowrap flex-shrink-0">
                      {relativeTime(thread.updated_at)}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* ── RIGHT: Messages panel ───────────────────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {!activeThread ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-2">
                <div className="text-3xl text-[rgba(255,255,255,0.06)]">&#9656;</div>
                <p className="text-[11px] text-[rgba(255,255,255,0.3)] uppercase tracking-wider">
                  Select a thread
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Thread header */}
              <div className="px-4 py-3 border-b border-[rgba(255,255,255,0.08)] flex items-center gap-3 flex-wrap">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <span className="text-sm font-bold text-white truncate">
                    {agencyName(activeThread)}
                  </span>
                  <StatusBadge status={activeThread.status} />
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={summarizeThread}
                    disabled={summarizing}
                    className="h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm transition-colors"
                    style={{
                      background: 'rgba(34,211,238,0.10)',
                      border: '1px solid rgba(34,211,238,0.25)',
                      color: '#22d3ee',
                      opacity: summarizing ? 0.6 : 1,
                    }}
                  >
                    {summarizing ? 'Summarizing…' : 'Summarize AI'}
                  </button>
                  {activeThread.status !== 'resolved' && (
                    <button
                      onClick={() => resolveThread(activeThread)}
                      disabled={resolvingId === activeThread.id}
                      className="h-7 px-3 text-[10px] font-semibold uppercase tracking-wider rounded-sm transition-colors"
                      style={{
                        background: 'rgba(76,175,80,0.10)',
                        border: '1px solid rgba(76,175,80,0.25)',
                        color: '#4caf50',
                        opacity: resolvingId === activeThread.id ? 0.6 : 1,
                      }}
                    >
                      {resolvingId === activeThread.id ? 'Resolving…' : 'Resolve'}
                    </button>
                  )}
                </div>
              </div>

              {/* AI Summary collapsible panel */}
              {summary && (
                <div
                  className="border-b border-[rgba(34,211,238,0.15)]"
                  style={{ background: 'rgba(34,211,238,0.04)' }}
                >
                  <button
                    className="w-full flex items-center justify-between px-4 py-2 text-left"
                    onClick={() => setSummaryOpen((v) => !v)}
                  >
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-[#22d3ee]">
                      AI Summary
                    </span>
                    <span className="text-[10px] text-[rgba(255,255,255,0.35)]">
                      {summaryOpen ? '▲ Collapse' : '▼ Expand'}
                    </span>
                  </button>
                  {summaryOpen && (
                    <div className="px-4 pb-3 text-[11px] text-[rgba(255,255,255,0.7)] leading-relaxed">
                      {summary}
                    </div>
                  )}
                </div>
              )}

              {/* Messages list */}
              <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
                {loadingMessages && (
                  <div className="text-center text-[11px] text-[rgba(255,255,255,0.3)] py-8">
                    Loading messages…
                  </div>
                )}
                {!loadingMessages && messages.length === 0 && (
                  <div className="text-center text-[11px] text-[rgba(255,255,255,0.3)] py-8">
                    No messages yet
                  </div>
                )}
                {messages.map((msg) => {
                  const isAgency = msg.sender_role === 'agency';
                  return (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${isAgency ? 'items-end' : 'items-start'}`}
                    >
                      <div
                        className="max-w-[72%] px-3 py-2 rounded-sm text-xs leading-relaxed"
                        style={{
                          background: isAgency
                            ? 'rgba(255,107,26,0.12)'
                            : 'rgba(255,255,255,0.05)',
                          border: `1px solid ${isAgency ? 'rgba(255,107,26,0.18)' : 'rgba(255,255,255,0.07)'}`,
                          color: 'rgba(255,255,255,0.85)',
                        }}
                      >
                        {msg.content}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5 px-0.5">
                        <span className="text-[10px] text-[rgba(255,255,255,0.3)] uppercase tracking-wider">
                          {msg.sender_role}
                        </span>
                        <span className="text-[10px] text-[rgba(255,255,255,0.22)]">
                          {relativeTime(msg.created_at)}
                        </span>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Reply box */}
              <div className="border-t border-[rgba(255,255,255,0.08)] px-4 py-3">
                <div className="flex gap-2 items-end">
                  <textarea
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) sendReply();
                    }}
                    placeholder="Type a reply… (Ctrl+Enter to send)"
                    rows={3}
                    className="flex-1 bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none resize-none placeholder:text-[rgba(255,255,255,0.22)] focus:border-[rgba(255,107,26,0.4)]"
                  />
                  <button
                    onClick={sendReply}
                    disabled={sendingReply || !replyText.trim()}
                    className="h-9 px-4 text-[10px] font-bold uppercase tracking-widest rounded-sm transition-all"
                    style={{
                      background: replyText.trim() && !sendingReply ? '#ff6b1a' : 'rgba(255,107,26,0.2)',
                      color: replyText.trim() && !sendingReply ? '#000' : 'rgba(255,107,26,0.5)',
                    }}
                  >
                    {sendingReply ? '…' : 'Send'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
