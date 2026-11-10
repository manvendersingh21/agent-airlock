'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, type Health } from './api';
import type { Metrics, Run, Scenario } from './types';

export function useConsoleData() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    try {
      const [nextHealth, nextScenarios, nextMetrics, nextRuns] = await Promise.all([
        api.health(), api.scenarios(), api.metrics(), api.runs(),
      ]);
      setHealth(nextHealth); setScenarios(nextScenarios); setMetrics(nextMetrics); setRuns(nextRuns); setError(null);
    } catch (cause) {
      setHealth(null);
      setError(cause instanceof Error && cause.message !== 'Failed to fetch' ? cause.message : 'Unable to connect to the gateway. Check that the backend is running, then reconnect.');
    } finally { setLoading(false); }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => { void refresh(); }, 20000);
    return () => clearInterval(timer);
  }, [refresh]);
  return { scenarios, metrics, runs, health, loading, error, refresh };
}
