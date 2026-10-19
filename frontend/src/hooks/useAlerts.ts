import { useState, useCallback } from 'react';
import type { AlertEvent } from './useWebSocket';

export interface AlertsState {
  events: AlertEvent[];
  unreadCount: number;
  bySource: {
    database: AlertEvent[];
    server: AlertEvent[];
    security: AlertEvent[];
    system: AlertEvent[];
  };
  addEvent: (event: AlertEvent) => void;
  markRead: (id: string) => void;
  acknowledge: (id: string) => Promise<void>;
  resolve: (id: string, note?: string) => Promise<void>;
  markAllRead: () => void;
}

function getToken(): string | null {
  return localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
}

function groupBySource(events: AlertEvent[]) {
  return {
    database: events.filter((e) => e.source === 'database'),
    server: events.filter((e) => e.source === 'server'),
    security: events.filter((e) => e.source === 'security'),
    system: events.filter((e) => e.source === 'system'),
  };
}

export function useAlerts(initialEvents: AlertEvent[] = []): AlertsState {
  const [events, setEvents] = useState<AlertEvent[]>(initialEvents);

  const addEvent = useCallback((event: AlertEvent) => {
    setEvents((prev) => {
      // Deduplicate by id
      if (prev.some((e) => e.id === event.id)) return prev;
      return [event, ...prev];
    });
  }, []);

  const markRead = useCallback((id: string) => {
    setEvents((prev) =>
      prev.map((e) => (e.id === id && e.status === 'new' ? { ...e, status: 'acknowledged' } : e))
    );
  }, []);

  const markAllRead = useCallback(() => {
    setEvents((prev) =>
      prev.map((e) => (e.status === 'new' ? { ...e, status: 'acknowledged' } : e))
    );
  }, []);

  const acknowledge = useCallback(async (id: string) => {
    const token = getToken();
    try {
      await fetch(`/api/v1/monitoring/notifications/${id}/acknowledge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
    } catch {
      // optimistic update regardless
    }
    setEvents((prev) =>
      prev.map((e) => (e.id === id ? { ...e, status: 'acknowledged' } : e))
    );
  }, []);

  const resolve = useCallback(async (id: string, note?: string) => {
    const token = getToken();
    try {
      await fetch(`/api/v1/monitoring/notifications/${id}/resolve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ note }),
      });
    } catch {
      // optimistic update regardless
    }
    setEvents((prev) =>
      prev.map((e) => (e.id === id ? { ...e, status: 'resolved' } : e))
    );
  }, []);

  const unreadCount = events.filter((e) => e.status === 'new').length;
  const bySource = groupBySource(events);

  return { events, unreadCount, bySource, addEvent, markRead, acknowledge, resolve, markAllRead };
}
