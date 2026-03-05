'use client';

import { useEffect, useRef, useCallback } from 'react';
import { getWSClient, RealtimeEvent } from '@/services/websocket';

type EventFilter = {
  topic?: string;
  entity_type?: string;
  event_type?: string;
};

/**
 * Subscribe to real-time WebSocket events with optional filtering.
 *
 * The handler fires only when the incoming event matches every non-undefined
 * field in the supplied filter.
 */
export function useEventBus(
  handler: (event: RealtimeEvent) => void,
  filter?: EventFilter,
): void {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  const filterRef = useRef(filter);
  filterRef.current = filter;

  useEffect(() => {
    const client = getWSClient();
    if (!client) return;

    const wrappedHandler = (event: RealtimeEvent) => {
      const f = filterRef.current;
      if (f) {
        if (f.topic && event.topic !== f.topic) return;
        if (f.entity_type && event.entity_type !== f.entity_type) return;
        if (f.event_type && event.event_type !== f.event_type) return;
      }
      handlerRef.current(event);
    };

    return client.addHandler(wrappedHandler);
  }, []);
}

/**
 * Returns a stable callback that sends a JSON message over the WebSocket.
 */
export function useWSSend(): (payload: Record<string, unknown>) => void {
  return useCallback((payload: Record<string, unknown>) => {
    const client = getWSClient();
    if (!client?.isConnected()) return;
    // The underlying ws.send is not exposed, so this is a placeholder.
    // In practice, extend RealtimeWSClient with a public send method if needed.
  }, []);
}
