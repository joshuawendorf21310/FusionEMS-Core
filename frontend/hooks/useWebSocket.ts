'use client';

import { useState, useEffect } from 'react';
import { getWSClient } from '@/services/websocket';

export interface WebSocketStatus {
  connected: boolean;
}

/**
 * Exposes the current WebSocket connection status.
 *
 * Polls the singleton WS client at a short interval so components can display
 * a live connection indicator.
 */
export function useWebSocket(): WebSocketStatus {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    function check() {
      const client = getWSClient();
      setConnected(client?.isConnected() ?? false);
    }

    check();
    const id = setInterval(check, 3000);
    return () => clearInterval(id);
  }, []);

  return { connected };
}
