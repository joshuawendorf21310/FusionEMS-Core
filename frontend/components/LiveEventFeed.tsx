'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getWSClient, RealtimeEvent, initWSClient } from '../services/websocket';

const EVENT_ICONS: Record<string, string> = {
  'claim.status_changed': '📋',
  'payment.confirmed': '💳',
  'letter.viewed': '📬',
  'export.completed': '📤',
  'authorization.verified': '✅',
  'ai.completed': '🤖',
  'incident.updated': '🚑',
  'incident.created': '🚑',
  'billing.case.validated': '🏥',
  'letter.sent': '✉️',
  'letter.failed': '⚠️',
};

const EVENT_COLORS: Record<string, string> = {
  'payment.confirmed': 'border-l-green-500',
  'claim.status_changed': 'border-l-blue-500',
  'authorization.verified': 'border-l-emerald-500',
  'letter.viewed': 'border-l-purple-500',
  'export.completed': 'border-l-cyan-500',
  'ai.completed': 'border-l-violet-500',
  'incident.created': 'border-l-amber-500',
  'letter.failed': 'border-l-red-500',
};

interface EventBadgeProps {
  event: RealtimeEvent & { id: string };
}

function EventBadge({ event }: EventBadgeProps) {
  const icon = EVENT_ICONS[event.event_type] || '⚡';
  const color = EVENT_COLORS[event.event_type] || 'border-l-slate-500';
  const ts = new Date(event.ts).toLocaleTimeString();

  return (
    <motion.div
      initial={{ opacity: 0, x: 40, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: -40, scale: 0.95 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={`border-l-2 ${color} bg-panel rounded-lg px-3 py-2 flex items-start gap-3 text-sm`}
    >
      <span className="text-base mt-0.5">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-white font-medium truncate">{event.event_type}</span>
          <span className="text-slate-500 text-xs flex-shrink-0">{ts}</span>
        </div>
        {event.entity_type && (
          <div className="text-slate-400 text-xs truncate">
            {event.entity_type} • {event.entity_id?.slice(0, 8)}...
          </div>
        )}
      </div>
      <motion.div
        initial={{ scale: 1.5, opacity: 1 }}
        animate={{ scale: 1, opacity: 0 }}
        transition={{ duration: 1.5, delay: 0.2 }}
        className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0 mt-1.5"
      />
    </motion.div>
  );
}

interface LiveEventFeedProps {
  maxEvents?: number;
  className?: string;
  filterTypes?: string[];
}

export function LiveEventFeed({
  maxEvents = 20,
  className = '',
  filterTypes,
}: LiveEventFeedProps) {
  const [events, setEvents] = useState<(RealtimeEvent & { id: string })[]>([]);
  const [connected, setConnected] = useState(false);
  const unsubRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    const client = getWSClient();
    if (!client) return;

    setConnected(client.isConnected());

    // Poll connection state every 3s to keep indicator accurate
    const connInterval = setInterval(() => {
      const c = getWSClient();
      setConnected(c ? c.isConnected() : false);
    }, 3000);

    unsubRef.current = client.addHandler((event) => {
      if (filterTypes && !filterTypes.includes(event.event_type)) return;
      setEvents((prev) => {
        const newEvent = { ...event, id: `${Date.now()}-${Math.random()}` };
        return [newEvent, ...prev].slice(0, maxEvents);
      });
    });

    return () => {
      clearInterval(connInterval);
      unsubRef.current?.();
    };
  }, [maxEvents, filterTypes]);

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <div className="flex items-center gap-2 mb-1">
        <motion.div
          animate={{ scale: connected ? [1, 1.3, 1] : 1 }}
          transition={{ repeat: connected ? Infinity : 0, duration: 2 }}
          className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}
        />
        <span className="text-xs text-slate-400">
          {connected ? 'Live' : 'Reconnecting...'}
        </span>
        <span className="text-xs text-slate-600 ml-auto">{events.length} events</span>
      </div>

      <div className="flex flex-col gap-1.5 overflow-y-auto max-h-96">
        <AnimatePresence mode="popLayout" initial={false}>
          {events.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-slate-600 text-xs text-center py-8"
            >
              Waiting for events...
            </motion.div>
          ) : (
            events.map((event) => <EventBadge key={event.id} event={event} />)
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
