'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/components/api';

/** State returned by the useApi hook. */
export interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Generic data-fetching hook that uses the centralised API client.
 *
 * Automatically fetches on mount and exposes a manual `refetch` callback.
 * Handles loading, error, and data states.
 */
export function useApi<T>(
  path: string,
  options?: RequestInit,
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Keep a stable reference to options so the caller doesn't need to memoise.
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api<T>(path, optionsRef.current);
      setData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}
