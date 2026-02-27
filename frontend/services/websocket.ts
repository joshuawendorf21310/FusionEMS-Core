type EventHandler = (event: RealtimeEvent) => void;

export interface RealtimeEvent {
  topic: string;
  tenant_id: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  ts: string;
  correlation_id: string | null;
}

interface WSClientOptions {
  url: string;
  token: string;
  onEvent?: EventHandler;
  onConnect?: () => void;
  onDisconnect?: () => void;
  maxReconnectAttempts?: number;
  heartbeatIntervalMs?: number;
  missedEventBufferSize?: number;
}

export class RealtimeWSClient {
  private ws: WebSocket | null = null;
  private url: string;
  private token: string;
  private onEvent: EventHandler;
  private onConnect: () => void;
  private onDisconnect: () => void;
  private reconnectAttempts = 0;
  private maxReconnectAttempts: number;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private heartbeatIntervalMs: number;
  private lastHeartbeat: number = Date.now();
  private missedEventBuffer: RealtimeEvent[] = [];
  private missedEventBufferSize: number;
  private isDestroyed = false;
  private handlers: Set<EventHandler> = new Set();

  constructor(options: WSClientOptions) {
    this.url = options.url;
    this.token = options.token;
    this.onEvent = options.onEvent || (() => {});
    this.onConnect = options.onConnect || (() => {});
    this.onDisconnect = options.onDisconnect || (() => {});
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 20;
    this.heartbeatIntervalMs = options.heartbeatIntervalMs ?? 25000;
    this.missedEventBufferSize = options.missedEventBufferSize ?? 100;
  }

  connect(): void {
    if (this.isDestroyed) return;
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const wsUrl = `${this.url}?token=${encodeURIComponent(this.token)}`;

    try {
      this.ws = new WebSocket(wsUrl);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.lastHeartbeat = Date.now();
      this.startHeartbeat();
      this.onConnect();
      this.flushMissedEvents();
    };

    this.ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.event_type === 'heartbeat') {
          this.lastHeartbeat = Date.now();
          return;
        }
        const event = data as RealtimeEvent;
        this.handlers.forEach((h) => h(event));
        this.onEvent(event);
      } catch {
        // ignore parse errors
      }
    };

    this.ws.onclose = () => {
      this.stopHeartbeat();
      this.onDisconnect();
      if (!this.isDestroyed) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  private scheduleReconnect(): void {
    if (this.isDestroyed) return;
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;

    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      const now = Date.now();
      if (now - this.lastHeartbeat > this.heartbeatIntervalMs * 2) {
        this.ws?.close();
        return;
      }
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, this.heartbeatIntervalMs);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private flushMissedEvents(): void {
    const buffered = [...this.missedEventBuffer];
    this.missedEventBuffer = [];
    buffered.forEach((e) => {
      this.handlers.forEach((h) => h(e));
      this.onEvent(e);
    });
  }

  addHandler(handler: EventHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  destroy(): void {
    this.isDestroyed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.stopHeartbeat();
    this.ws?.close();
    this.ws = null;
  }
}

let globalClient: RealtimeWSClient | null = null;

export function getWSClient(): RealtimeWSClient | null {
  return globalClient;
}

export function initWSClient(options: WSClientOptions): RealtimeWSClient {
  globalClient?.destroy();
  globalClient = new RealtimeWSClient(options);
  globalClient.connect();
  return globalClient;
}
