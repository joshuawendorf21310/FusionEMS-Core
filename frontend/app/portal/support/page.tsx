'use client';
import { QuantumTableSkeleton, QuantumCardSkeleton } from '@/components/ui';

import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
} from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function authHeader(): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: 'Bearer ' + (localStorage.getItem('qs_token') || ''),
  };
}

type ThreadType =
  | 'General Support'
  | 'Billing Question'
  | 'Technical Issue'
  | 'Compliance';

type ThreadStatus = 'open' | 'escalated' | 'resolved';

interface SupportThread {
  id: string;
  title: string;
  thread_type: ThreadType;
  status: ThreadStatus;
  last_message_preview: string;
  last_message_at: string;
  unread_count?: number;
}

interface SupportMessage {
  id: string;
  sender_type: 'agency' | 'ai' | 'founder';
  sender_label: string;
  content: string;
  created_at: string;
}

const THREAD_TYPES: ThreadType[] = [
  'General Support',
  'Billing Question',
  'Technical Issue',
  'Compliance',
];

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    const now = Date.now();
    const diff = now - d.getTime();
    if (diff < 60_000) return 'just now';
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
    if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
    return d.toLocaleDateString();
  } catch {
    return '';
  }
}

function StatusBadge({ status }: { status: ThreadStatus }) {
  if (status === 'open')
    return (
      <span className="text-[10px] px-1.5 py-0.5 rounded-sm border border-[rgba(34,211,238,0.3)] text-system-billing bg-[rgba(34,211,238,0.08)]">
        open
      </span>
    );
  if (status === 'escalated')
    return (
      <span className="text-[10px] px-1.5 py-0.5 rounded-sm border border-red-ghost text-red bg-[rgba(229,57,53,0.08)] animate-pulse">
        escalated
      </span>
    );
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded-sm border border-[rgba(255,255,255,0.12)] text-[rgba(255,255,255,0.4)] bg-[rgba(255,255,255,0.04)]">
      resolved
    </span>
  );
}

// ── New Conversation Modal ──────────────────────────────────────────────────

interface NewThreadModalProps {
  onClose: () => void;
  onCreate: (thread: SupportThread) => void;
}

function NewThreadModal({ onClose, onCreate }: NewThreadModalProps) {
  const [threadType, setThreadType] = useState<ThreadType>('General Support');
  const [title, setTitle] = useState('');
  const [initialMessage, setInitialMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !initialMessage.trim()) {
      setError('Title and message are required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/v1/support/threads`, {
        method: 'POST',
        headers: authHeader(),
        body: JSON.stringify({
          thread_type: threadType,
          title: title.trim(),
          initial_message: initialMessage.trim(),
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: SupportThread = await res.json();
      onCreate(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Request failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-bg-base border border-border-DEFAULT rounded-sm w-full max-w-md mx-4 p-6">
        <h2 className="text-sm font-semibold text-text-primary tracking-widest uppercase mb-5">
          New Conversation
        </h2>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Type */}
          <div>
            <label className="block text-[11px] text-[rgba(255,255,255,0.5)] uppercase tracking-wider mb-1.5">
              Type
            </label>
            <select
              value={threadType}
              onChange={(e) => setThreadType(e.target.value as ThreadType)}
              className="w-full bg-bg-void border border-border-DEFAULT rounded-sm text-sm text-text-primary px-3 py-2 focus:outline-none focus:border-[rgba(255,107,26,0.4)]"
            >
              {THREAD_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {/* Title */}
          <div>
            <label className="block text-[11px] text-[rgba(255,255,255,0.5)] uppercase tracking-wider mb-1.5">
              Subject
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Brief description of your issue"
              className="w-full bg-bg-void border border-border-DEFAULT rounded-sm text-sm text-text-primary px-3 py-2 placeholder-[rgba(255,255,255,0.2)] focus:outline-none focus:border-[rgba(255,107,26,0.4)]"
            />
          </div>

          {/* Initial message */}
          <div>
            <label className="block text-[11px] text-[rgba(255,255,255,0.5)] uppercase tracking-wider mb-1.5">
              Message
            </label>
            <textarea
              rows={4}
              value={initialMessage}
              onChange={(e) => setInitialMessage(e.target.value)}
              placeholder="Describe your issue in detail…"
              className="w-full bg-bg-void border border-border-DEFAULT rounded-sm text-sm text-text-primary px-3 py-2 placeholder-[rgba(255,255,255,0.2)] focus:outline-none focus:border-[rgba(255,107,26,0.4)] resize-none"
            />
          </div>

          {error && (
            <p className="text-xs text-red">{error}</p>
          )}

          <div className="flex gap-3 justify-end mt-1">
            <button
              type="button"
              onClick={onClose}
              className="text-sm px-4 py-2 rounded-sm border border-border-DEFAULT text-[rgba(255,255,255,0.5)] hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="text-sm px-4 py-2 rounded-sm bg-orange text-text-primary font-medium hover:bg-orange-dim transition-colors disabled:opacity-50"
            >
              {loading ? 'Creating…' : 'Start Conversation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function AgencySupportPage() {
  const [threads, setThreads] = useState<SupportThread[]>([]);
  const [selectedThread, setSelectedThread] = useState<SupportThread | null>(null);
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const selectedThreadRef = useRef<SupportThread | null>(null);

  // keep ref in sync
  useEffect(() => {
    selectedThreadRef.current = selectedThread;
  }, [selectedThread]);

  // ── Fetch threads ──────────────────────────────────────────────────────────
  const fetchThreads = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/support/threads`, {
        headers: authHeader(),
      });
      if (!res.ok) return;
      const data: SupportThread[] = await res.json();
      setThreads(data);
    } catch (err: unknown) {
      console.warn("[support]", err);
    }
  }, []);

  // ── Fetch messages for active thread ──────────────────────────────────────
  const fetchMessages = useCallback(async (threadId: string) => {
    try {
      const res = await fetch(
        `${API}/api/v1/support/threads/${threadId}/messages`,
        { headers: authHeader() }
      );
      if (!res.ok) return;
      const data: SupportMessage[] = await res.json();
      setMessages(data);
    } catch (err: unknown) {
      console.warn("[support]", err);
    }
  }, []);

  // ── Poll for new messages every 10s ──────────────────────────────────────
  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => {
      if (selectedThreadRef.current) {
        fetchMessages(selectedThreadRef.current.id);
      }
    }, 10_000);
  }, [fetchMessages]);

  useEffect(() => {
    setLoadingThreads(true);
    fetchThreads().finally(() => setLoadingThreads(false));
    startPolling();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchThreads, startPolling]);

  // ── Select thread ──────────────────────────────────────────────────────────
  const handleSelectThread = useCallback(
    async (thread: SupportThread) => {
      setSelectedThread(thread);
      setMessages([]);
      setLoadingMessages(true);
      await fetchMessages(thread.id);
      setLoadingMessages(false);
    },
    [fetchMessages]
  );

  // ── Auto-scroll ──────────────────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Send message ──────────────────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    if (!selectedThread || !input.trim() || sending) return;
    const content = input.trim();
    setInput('');
    setSending(true);
    try {
      const res = await fetch(
        `${API}/api/v1/support/threads/${selectedThread.id}/messages`,
        {
          method: 'POST',
          headers: authHeader(),
          body: JSON.stringify({ content }),
        }
      );
      if (!res.ok) throw new Error();
      await fetchMessages(selectedThread.id);
    } catch {
      setInput(content); // restore on failure
    } finally {
      setSending(false);
    }
  }, [selectedThread, input, sending, fetchMessages]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // ── Thread created callback ────────────────────────────────────────────────
  const handleThreadCreated = useCallback(
    (thread: SupportThread) => {
      setThreads((prev) => [thread, ...prev]);
      setShowModal(false);
      handleSelectThread(thread);
    },
    [handleSelectThread]
  );

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ background: 'var(--color-bg-void)', color: 'white' }}
    >
      {/* ── Left sidebar ─────────────────────────────────────────────────── */}
      <aside
        className="flex flex-col border-r border-border-DEFAULT shrink-0"
        style={{ width: 240 }}
      >
        {/* Header */}
        <div className="px-4 pt-5 pb-3 border-b border-border-DEFAULT">
          <p className="text-[11px] font-semibold tracking-widest text-[rgba(255,255,255,0.4)] uppercase mb-3">
            Support
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="w-full text-sm py-2 rounded-sm bg-orange text-text-primary font-medium hover:bg-orange-dim transition-colors"
          >
            + New Conversation
          </button>
        </div>

        {/* Thread type legend */}
        <div className="px-4 pt-3 pb-2">
          {THREAD_TYPES.map((t) => (
            <p
              key={t}
              className="text-[11px] text-[rgba(255,255,255,0.3)] py-0.5"
            >
              {t}
            </p>
          ))}
        </div>

        {/* Thread list */}
        <div className="flex-1 overflow-y-auto">
          {loadingThreads && (
            <p className="text-xs text-[rgba(255,255,255,0.3)] px-4 py-3">
              Loading…
            </p>
          )}
          {!loadingThreads && threads.length === 0 && (
            <p className="text-xs text-[rgba(255,255,255,0.3)] px-4 py-3">
              No conversations yet.
            </p>
          )}
          {threads.map((t) => {
            const active = selectedThread?.id === t.id;
            return (
              <button
                key={t.id}
                onClick={() => handleSelectThread(t)}
                className={`w-full text-left px-4 py-3 border-b border-[rgba(255,255,255,0.05)] transition-colors ${
                  active
                    ? 'bg-orange-ghost'
                    : 'hover:bg-[rgba(255,255,255,0.03)]'
                }`}
              >
                <div className="flex items-center justify-between gap-1 mb-0.5">
                  <span
                    className="text-xs font-medium text-text-primary truncate"
                    style={{ maxWidth: 140 }}
                  >
                    {t.title}
                  </span>
                  <StatusBadge status={t.status} />
                </div>
                <p className="text-[11px] text-[rgba(255,255,255,0.3)] truncate mb-1">
                  {t.last_message_preview}
                </p>
                <p className="text-[10px] text-[rgba(255,255,255,0.2)]">
                  {formatTime(t.last_message_at)}
                </p>
              </button>
            );
          })}
        </div>
      </aside>

      {/* ── Main panel ───────────────────────────────────────────────────── */}
      <main className="flex flex-col flex-1 overflow-hidden">
        {!selectedThread ? (
          // Empty state
          <div className="flex-1 flex items-center justify-center">
            <p className="text-sm text-[rgba(255,255,255,0.25)]">
              Select a conversation or start a new one
            </p>
          </div>
        ) : (
          <>
            {/* Thread header */}
            <div className="px-6 py-4 border-b border-border-DEFAULT flex items-center gap-3 shrink-0">
              <span className="text-sm font-semibold text-text-primary">
                {selectedThread.title}
              </span>
              <span className="text-[11px] text-[rgba(255,255,255,0.4)]">
                {selectedThread.thread_type}
              </span>
              <div className="ml-auto">
                <StatusBadge status={selectedThread.status} />
              </div>
            </div>

            {/* Escalation banner */}
            {selectedThread.status === 'escalated' && (
              <div className="mx-6 mt-3 px-4 py-2.5 rounded-sm border border-[rgba(255,152,0,0.3)] bg-[rgba(255,152,0,0.08)] text-xs text-status-warning shrink-0">
                This thread has been escalated to the FusionEMS team. A team
                member will respond shortly.
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-2">
              {loadingMessages && (
                <p className="text-xs text-[rgba(255,255,255,0.3)] text-center py-6">
                  Loading messages…
                </p>
              )}
              {!loadingMessages && messages.length === 0 && (
                <p className="text-xs text-[rgba(255,255,255,0.3)] text-center py-6">
                  No messages yet.
                </p>
              )}
              {messages.map((msg) => {
                const isAgency = msg.sender_type === 'agency';
                const isAI = msg.sender_type === 'ai';
                return (
                  <div
                    key={msg.id}
                    className={`flex flex-col gap-0.5 ${
                      isAgency ? 'items-end' : 'items-start'
                    }`}
                  >
                    {/* Sender label row */}
                    <div
                      className={`flex items-center gap-1.5 ${
                        isAgency ? 'flex-row-reverse' : ''
                      }`}
                    >
                      <span className="text-[10px] text-[rgba(255,255,255,0.35)]">
                        {msg.sender_label}
                      </span>
                      {isAI && (
                        <span className="text-[9px] px-1 py-0.5 rounded-sm bg-[rgba(34,211,238,0.12)] border border-[rgba(34,211,238,0.25)] text-system-billing font-medium">
                          AI
                        </span>
                      )}
                    </div>
                    {/* Bubble */}
                    <div
                      className={`px-3 py-2 rounded-sm text-sm text-text-primary max-w-[70%] ${
                        isAgency
                          ? 'bg-[rgba(255,107,26,0.15)] border border-[rgba(255,107,26,0.2)]'
                          : 'bg-[rgba(255,255,255,0.05)] border border-border-DEFAULT'
                      }`}
                    >
                      {msg.content}
                    </div>
                    {/* Timestamp */}
                    <span className="text-[10px] text-[rgba(255,255,255,0.2)]">
                      {formatTime(msg.created_at)}
                    </span>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="px-6 pb-5 pt-3 border-t border-border-DEFAULT shrink-0">
              <div className="flex gap-2 items-end">
                {/* File attachment button (UI only) */}
                <button
                  type="button"
                  title="Attach file"
                  className="shrink-0 mb-0.5 p-2 rounded-sm border border-border-DEFAULT text-[rgba(255,255,255,0.3)] hover:text-text-primary hover:border-[rgba(255,255,255,0.2)] transition-colors"
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M21.44 11.05L12.25 20.24a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.41 17.41a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                </button>

                <textarea
                  rows={3}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a message… (Enter to send, Shift+Enter for new line)"
                  disabled={selectedThread.status === 'resolved'}
                  className="flex-1 bg-bg-base border border-border-DEFAULT rounded-sm text-sm text-text-primary px-3 py-2 placeholder-[rgba(255,255,255,0.2)] focus:outline-none focus:border-[rgba(255,107,26,0.4)] resize-none disabled:opacity-40"
                />

                <button
                  onClick={handleSend}
                  disabled={!input.trim() || sending || selectedThread.status === 'resolved'}
                  className="shrink-0 mb-0.5 px-4 py-2 rounded-sm bg-orange text-text-primary text-sm font-medium hover:bg-orange-dim transition-colors disabled:opacity-40"
                >
                  {sending ? '…' : 'Send'}
                </button>
              </div>
              {selectedThread.status === 'resolved' && (
                <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-1.5">
                  This conversation is resolved. Start a new one if you need
                  further assistance.
                </p>
              )}
            </div>
          </>
        )}
      </main>

      {/* Modal */}
      {showModal && (
        <NewThreadModal
          onClose={() => setShowModal(false)}
          onCreate={handleThreadCreated}
        />
      )}
    </div>
  );
}
