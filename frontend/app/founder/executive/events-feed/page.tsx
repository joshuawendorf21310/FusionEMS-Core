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

// ── Types ─────────────────────────────────────────────────────────────────────

type DateRangeFilter = 'last_hour' | 'today' | 'last_7_days';

type EventDomain =
  | 'onboarding'
  | 'billing'
  | 'fax'
  | 'edi'
  | 'support'
  | 'provisioning'
  | 'other';

interface PlatformEvent {
  id: string;
  event_type: string;
  tenant_id: string | null;
  tenant_name: string | null;
  entity_type: string | null;
  entity_id: string | null;
  summary: string;
  payload: Record<string, unknown>;
  created_at: string;
  read: boolean;
}

interface EventsFeedResponse {
  events: PlatformEvent[];
  next_cursor: string | null;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const FILTER_PILLS = [
  { label: 'All Event Types', value: '' },
  { label: 'onboarding.*', value: 'onboarding' },
  { label: 'billing.*', value: 'billing' },
  { label: 'fax.*', value: 'fax' },
  { label: 'edi.*', value: 'edi' },
  { label: 'support.*', value: 'support' },
  { label: 'provisioning.*', value: 'provisioning' },
] as const;

const DATE_RANGE_OPTIONS: { label: string; value: DateRangeFilter }[] = [
  { label: 'Last hour', value: 'last_hour' },
  { label: 'Today', value: 'today' },
  { label: 'Last 7 days', value: 'last_7_days' },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function getDomain(eventType: string): EventDomain {
  if (eventType.startsWith('onboarding.')) return 'onboarding';
  if (eventType.startsWith('billing.')) return 'billing';
  if (eventType.startsWith('fax.')) return 'fax';
  if (eventType.startsWith('edi.')) return 'edi';
  if (eventType.startsWith('support.')) return 'support';
  if (eventType.startsWith('provisioning.')) return 'provisioning';
  return 'other';
}

const DOMAIN_COLORS: Record<EventDomain, string> = {
  onboarding: 'var(--color-status-info)',
  billing: 'var(--color-status-active)',
  fax: 'var(--color-brand-orange)',
  edi: 'var(--color-status-warning)',
  support: 'var(--color-system-compliance)',
  provisioning: 'var(--color-system-fleet)',
  other: 'rgba(255,255,255,0.4)',
};

function domainBadgeStyle(domain: EventDomain): React.CSSProperties {
  const color = DOMAIN_COLORS[domain];
  return {
    color,
    borderColor: color.replace(')', ', 0.3)').replace('rgb', 'rgba'),
    backgroundColor: color.replace(')', ', 0.08)').replace('rgb', 'rgba'),
  };
}

function relativeTime(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime();
    if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
    if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
    return `${Math.floor(diff / 86_400_000)}d ago`;
  } catch {
    return '—';
  }
}

function absoluteTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function dateRangeCursor(range: DateRangeFilter): string | null {
  const now = new Date();
  if (range === 'last_hour') {
    return new Date(now.getTime() - 3_600_000).toISOString();
  }
  if (range === 'today') {
    const d = new Date(now);
    d.setHours(0, 0, 0, 0);
    return d.toISOString();
  }
  if (range === 'last_7_days') {
    return new Date(now.getTime() - 7 * 86_400_000).toISOString();
  }
  return null;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function EventRow({
  event,
  onExpand,
  onRead,
}: {
  event: PlatformEvent;
  onExpand: (id: string) => void;
  onRead: (id: string) => void;
}) {
  const domain = getDomain(event.event_type);
  const color = DOMAIN_COLORS[domain];

  function handleClick() {
    onExpand(event.id);
    if (!event.read) onRead(event.id);
  }

  return (
    <tr
      onClick={handleClick}
      className="border-b border-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.03)] cursor-pointer transition-colors"
    >
      {/* Unread dot */}
      <td className="pl-4 pr-2 py-3 w-5">
        {!event.read && (
          <span
            className="inline-block w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: color }}
          />
        )}
      </td>

      {/* Time */}
      <td
        className="pr-4 py-3 whitespace-nowrap text-xs text-[rgba(255,255,255,0.5)]"
        title={absoluteTime(event.created_at)}
      >
        {relativeTime(event.created_at)}
      </td>

      {/* Tenant */}
      <td className="pr-4 py-3 text-xs text-[rgba(255,255,255,0.6)] max-w-[120px] truncate">
        {event.tenant_name || event.tenant_id || (
          <span className="text-[rgba(255,255,255,0.25)]">—</span>
        )}
      </td>

      {/* Event type badge */}
      <td className="pr-4 py-3">
        <span
          className="text-[11px] font-mono px-1.5 py-0.5 rounded-sm border"
          style={domainBadgeStyle(domain)}
        >
          {event.event_type}
        </span>
      </td>

      {/* Entity */}
      <td className="pr-4 py-3 text-xs text-[rgba(255,255,255,0.5)] max-w-[160px]">
        {event.entity_type ? (
          <span className="truncate block">
            <span className="text-[rgba(255,255,255,0.7)]">
              {event.entity_type}
            </span>{' '}
            <span className="text-[rgba(255,255,255,0.3)] font-mono">
              {event.entity_id ? event.entity_id.slice(0, 12) + '…' : ''}
            </span>
          </span>
        ) : (
          <span className="text-[rgba(255,255,255,0.25)]">—</span>
        )}
      </td>

      {/* Summary */}
      <td className="py-3 text-xs text-[rgba(255,255,255,0.6)] max-w-[280px] truncate pr-4">
        {event.summary}
      </td>
    </tr>
  );
}

function ExpandedRow({
  event,
  colSpan,
}: {
  event: PlatformEvent;
  colSpan: number;
}) {
  const json = JSON.stringify(event.payload, null, 2);
  return (
    <tr className="bg-bg-base">
      <td colSpan={colSpan} className="px-6 py-4">
        <pre className="text-xs text-system-billing bg-bg-void border border-border-DEFAULT rounded-sm p-4 overflow-x-auto whitespace-pre-wrap break-words">
          {json}
        </pre>
      </td>
    </tr>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function EventsFeedPage() {
  const [events, setEvents] = useState<PlatformEvent[]>([]);
  const [filter, setFilter] = useState<string>('');
  const [dateRange, setDateRange] = useState<DateRangeFilter>('today');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  const latestCursorRef = useRef<string | null>(null);
  const autoRefreshRef = useRef(autoRefresh);
  const filterRef = useRef(filter);
  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const unreadTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // keep refs in sync
  useEffect(() => { autoRefreshRef.current = autoRefresh; }, [autoRefresh]);
  useEffect(() => { filterRef.current = filter; }, [filter]);

  // ── Fetch initial events ──────────────────────────────────────────────────
  const fetchInitial = useCallback(async (currentFilter: string, range: DateRangeFilter) => {
    setLoading(true);
    setEvents([]);
    latestCursorRef.current = null;
    try {
      const params = new URLSearchParams({ limit: '50' });
      const since = dateRangeCursor(range);
      if (since) params.set('cursor', since);
      if (currentFilter) params.set('event_types[]', currentFilter + '.*');

      const res = await fetch(`${API}/api/v1/events/feed?${params}`, {
        headers: authHeader(),
      });
      if (!res.ok) return;
      const data: EventsFeedResponse = await res.json();
      setEvents(data.events || []);
      if (data.events?.length > 0) {
        latestCursorRef.current = data.events[0].created_at;
      }
    } catch (err: unknown) {
      console.warn("[events-feed]", err);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Refresh — prepend new events ──────────────────────────────────────────
  const fetchNew = useCallback(async () => {
    if (!autoRefreshRef.current) return;
    try {
      const params = new URLSearchParams({ limit: '50' });
      if (latestCursorRef.current) params.set('cursor', latestCursorRef.current);
      if (filterRef.current) params.set('event_types[]', filterRef.current + '.*');

      const res = await fetch(`${API}/api/v1/events/feed?${params}`, {
        headers: authHeader(),
      });
      if (!res.ok) return;
      const data: EventsFeedResponse = await res.json();
      if (data.events?.length > 0) {
        setEvents((prev) => {
          const existingIds = new Set(prev.map((e) => e.id));
          const fresh = data.events.filter((e) => !existingIds.has(e.id));
          if (fresh.length === 0) return prev;
          return [...fresh, ...prev];
        });
        latestCursorRef.current = data.events[0].created_at;
      }
    } catch (err: unknown) {
      console.warn("[events-feed]", err);
    }
  }, []);

  // ── Unread count ──────────────────────────────────────────────────────────
  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/events/unread-count`, {
        headers: authHeader(),
      });
      if (!res.ok) return;
      const data: { count: number } = await res.json();
      setUnreadCount(data.count ?? 0);
    } catch (err: unknown) {
      console.warn("[events-feed]", err);
    }
  }, []);

  // ── Mark single event read ────────────────────────────────────────────────
  const markRead = useCallback(async (eventId: string) => {
    setEvents((prev) =>
      prev.map((e) => (e.id === eventId ? { ...e, read: true } : e))
    );
    setUnreadCount((c) => Math.max(0, c - 1));
    try {
      await fetch(`${API}/api/v1/events/${eventId}/read`, {
        method: 'POST',
        headers: authHeader(),
      });
    } catch (err: unknown) {
      console.warn("[events-feed]", err);
    }
  }, []);

  // ── Mark all read ─────────────────────────────────────────────────────────
  const markAllRead = useCallback(() => {
    const unread = events.filter((e) => !e.read);
    unread.forEach((e) => markRead(e.id));
  }, [events, markRead]);

  // ── Toggle expand ─────────────────────────────────────────────────────────
  const handleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // ── Initial load ──────────────────────────────────────────────────────────
  useEffect(() => {
    fetchInitial(filter, dateRange);
    fetchUnreadCount();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, dateRange]);

  // ── Polling intervals ─────────────────────────────────────────────────────
  useEffect(() => {
    if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    refreshTimerRef.current = setInterval(fetchNew, 15_000);
    return () => {
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    };
  }, [fetchNew]);

  useEffect(() => {
    if (unreadTimerRef.current) clearInterval(unreadTimerRef.current);
    unreadTimerRef.current = setInterval(fetchUnreadCount, 30_000);
    return () => {
      if (unreadTimerRef.current) clearInterval(unreadTimerRef.current);
    };
  }, [fetchUnreadCount]);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-screen px-6 py-6 flex flex-col gap-5"
      style={{ background: 'var(--color-bg-base)', color: 'white' }}
    >
      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-sm font-semibold tracking-widest uppercase text-text-primary">
          Platform Events Feed
          {unreadCount > 0 && (
            <span className="ml-2 text-orange">({unreadCount} unread)</span>
          )}
        </h1>
        <div className="ml-auto flex items-center gap-3 flex-wrap">
          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh((v) => !v)}
            className={`text-xs px-3 py-1.5 rounded-sm border transition-colors ${
              autoRefresh
                ? 'border-[rgba(76,175,80,0.4)] text-status-active bg-[rgba(76,175,80,0.08)]'
                : 'border-border-DEFAULT text-[rgba(255,255,255,0.4)]'
            }`}
          >
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </button>
          {/* Mark all read */}
          <button
            onClick={markAllRead}
            className="text-xs px-3 py-1.5 rounded-sm border border-border-DEFAULT text-[rgba(255,255,255,0.5)] hover:text-text-primary hover:border-[rgba(255,255,255,0.2)] transition-colors"
          >
            Mark all read
          </button>
        </div>
      </div>

      {/* ── Filter pills + date range ──────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Event type pills */}
        <div className="flex flex-wrap gap-1.5">
          {FILTER_PILLS.map((pill) => {
            const active = filter === pill.value;
            return (
              <button
                key={pill.value}
                onClick={() => setFilter(pill.value)}
                className={`text-xs px-3 py-1 rounded-sm border transition-colors font-mono ${
                  active
                    ? 'border-[rgba(255,107,26,0.5)] text-orange bg-[rgba(255,107,26,0.1)]'
                    : 'border-border-DEFAULT text-[rgba(255,255,255,0.4)] hover:text-text-primary hover:border-[rgba(255,255,255,0.2)]'
                }`}
              >
                {pill.label}
              </button>
            );
          })}
        </div>

        {/* Divider */}
        <div className="w-px h-4 bg-[rgba(255,255,255,0.1)] mx-1" />

        {/* Date range */}
        <div className="flex gap-1.5">
          {DATE_RANGE_OPTIONS.map((opt) => {
            const active = dateRange === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => setDateRange(opt.value)}
                className={`text-xs px-3 py-1 rounded-sm border transition-colors ${
                  active
                    ? 'border-[rgba(34,211,238,0.4)] text-system-billing bg-[rgba(34,211,238,0.08)]'
                    : 'border-border-DEFAULT text-[rgba(255,255,255,0.4)] hover:text-text-primary hover:border-[rgba(255,255,255,0.2)]'
                }`}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Events table ──────────────────────────────────────────────────── */}
      <div className="bg-bg-base border border-border-DEFAULT rounded-sm overflow-hidden flex-1">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <span className="text-sm text-[rgba(255,255,255,0.3)]">Loading events…</span>
          </div>
        ) : events.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <span className="text-sm text-[rgba(255,255,255,0.25)]">No events</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-border-DEFAULT">
                  <th className="w-5 pl-4 pr-2 py-2" />
                  <th className="pr-4 py-2 text-left text-[10px] font-semibold tracking-widest uppercase text-[rgba(255,255,255,0.3)] whitespace-nowrap">
                    Time
                  </th>
                  <th className="pr-4 py-2 text-left text-[10px] font-semibold tracking-widest uppercase text-[rgba(255,255,255,0.3)]">
                    Tenant
                  </th>
                  <th className="pr-4 py-2 text-left text-[10px] font-semibold tracking-widest uppercase text-[rgba(255,255,255,0.3)]">
                    Event Type
                  </th>
                  <th className="pr-4 py-2 text-left text-[10px] font-semibold tracking-widest uppercase text-[rgba(255,255,255,0.3)]">
                    Entity
                  </th>
                  <th className="pr-4 py-2 text-left text-[10px] font-semibold tracking-widest uppercase text-[rgba(255,255,255,0.3)]">
                    Summary
                  </th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <React.Fragment key={event.id}>
                    <EventRow
                      event={event}
                      onExpand={handleExpand}
                      onRead={markRead}
                    />
                    {expandedIds.has(event.id) && (
                      <ExpandedRow event={event} colSpan={6} />
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
