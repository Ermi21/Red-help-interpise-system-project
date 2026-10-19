import { useEffect, useRef, useState, useCallback } from 'react';

export type WsStatus = 'connected' | 'reconnecting' | 'polling' | 'disconnected';

export interface AlertEvent {
  id: string;
  source: 'database' | 'server' | 'security' | 'system';
  type: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string;
  metadata?: Record<string, unknown>;
  user_id?: string;
  created_at: string;
  status: 'new' | 'acknowledged' | 'resolved';
}

const BACKOFF_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000];
const PING_INTERVAL = 25000;
const POLL_INTERVAL = 10000;

export function useWebSocket(onEvent: (event: AlertEvent) => void) {
  const [status, setStatus] = useState<WsStatus>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastEventIdRef = useRef<string | null>(null);
  const onEventRef = useRef(onEvent);
  const mountedRef = useRef(true);

  // Keep callback ref up to date without triggering reconnect
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  const getToken = useCallback((): string | null => {
    return localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
  }, []);

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current);
      pingTimerRef.current = null;
    }
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    if (!mountedRef.current) return;
    setStatus('polling');

    const poll = async () => {
      const token = getToken();
      if (!token) return;
      try {
        // Use the paginated notifications endpoint (correct schema)
        const params = new URLSearchParams({ page_size: '20', page: '1' });
        const res = await fetch(`/api/v1/notifications?${params}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json() as {
            items?: Array<{
              id: string;
              source?: string;
              event_type?: string;
              severity?: string;
              title?: string;
              message?: string;
              metadata_json?: Record<string, unknown>;
              user_id?: string;
              status?: string;
              created_at?: string;
            }>;
          };
          const rawItems = data.items ?? [];
          rawItems.forEach((raw) => {
            // Skip events we've already processed
            if (lastEventIdRef.current === raw.id) return;
            const sev = raw.severity === 'low' || raw.severity === 'medium' ? 'info' : (raw.severity ?? 'info');
            const ev: AlertEvent = {
              id: raw.id,
              source: (raw.source ?? 'system') as AlertEvent['source'],
              type: raw.event_type ?? 'event',
              severity: sev as AlertEvent['severity'],
              title: raw.title ?? '',
              message: raw.message ?? '',
              metadata: raw.metadata_json,
              user_id: raw.user_id,
              created_at: raw.created_at ?? new Date().toISOString(),
              status: raw.status === 'acknowledged' ? 'acknowledged' : raw.status === 'resolved' ? 'resolved' : 'new',
            };
            lastEventIdRef.current = ev.id;
            onEventRef.current(ev);
          });
        }
      } catch {
        // silently ignore poll errors
      }
    };

    poll();
    pollTimerRef.current = setInterval(poll, POLL_INTERVAL);
  }, [getToken]);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    const token = getToken();
    if (!token) {
      setStatus('disconnected');
      return;
    }

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    if (reconnectAttemptRef.current > 0) {
      setStatus('reconnecting');
    }

    let ws: WebSocket;
    try {
      const wsUrl = `ws://${window.location.host}/api/v1/ws/notifications?token=${token}`;
      ws = new WebSocket(wsUrl);
    } catch {
      startPolling();
      return;
    }

    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setStatus('connected');
      reconnectAttemptRef.current = 0;

      // Stop polling if it was running
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }

      // Setup keepalive ping
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = (ev) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(ev.data as string) as Record<string, unknown>;
        // Skip keepalive messages
        if (msg.type === 'ping' || msg.type === 'pong' || msg.type === 'connected') return;
        // Backend sends: { type: "event", data: { id, source, event_type, severity, title, message, ... } }
        const rawEvent = (msg.type === 'event' ? msg.data : msg) as Record<string, unknown>;
        if (!rawEvent || !rawEvent.id) return;

        const sev = rawEvent.severity === 'low' || rawEvent.severity === 'medium' ? 'info' : (rawEvent.severity ?? 'info');
        const event: AlertEvent = {
          id: rawEvent.id as string,
          source: (rawEvent.source ?? 'system') as AlertEvent['source'],
          type: (rawEvent.event_type ?? rawEvent.type ?? 'event') as string,
          severity: sev as AlertEvent['severity'],
          title: (rawEvent.title ?? '') as string,
          message: (rawEvent.message ?? '') as string,
          metadata: rawEvent.metadata_json as Record<string, unknown> | undefined ?? rawEvent.metadata as Record<string, unknown> | undefined,
          user_id: rawEvent.user_id as string | undefined,
          created_at: (rawEvent.created_at ?? rawEvent.occurred_at ?? new Date().toISOString()) as string,
          status: rawEvent.status === 'acknowledged' ? 'acknowledged' : rawEvent.status === 'resolved' ? 'resolved' : 'new',
        };
        lastEventIdRef.current = event.id;
        onEventRef.current(event);
      } catch {
        // ignore non-JSON messages
      }
    };

    ws.onerror = () => {
      // onclose will fire after onerror
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      if (pingTimerRef.current) {
        clearInterval(pingTimerRef.current);
        pingTimerRef.current = null;
      }

      const attempt = reconnectAttemptRef.current;
      const maxAttempt = BACKOFF_DELAYS.length - 1;

      if (attempt >= BACKOFF_DELAYS.length * 2) {
        // Too many reconnect attempts — fall back to polling
        startPolling();
        return;
      }

      const delay = BACKOFF_DELAYS[Math.min(attempt, maxAttempt)];
      reconnectAttemptRef.current += 1;
      setStatus('reconnecting');

      reconnectTimerRef.current = setTimeout(() => {
        if (mountedRef.current) connect();
      }, delay);
    };
  }, [getToken, startPolling]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      clearTimers();
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect, clearTimers]);

  return { status };
}
