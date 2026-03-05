/**
 * Analytics module types.
 */

export interface TimeSeriesPoint {
  date: string;
  value: number;
}

export interface KPIMetric {
  key: string;
  label: string;
  value: number;
  previousValue: number | null;
  unit: string;
  trend: 'up' | 'down' | 'flat';
}

export interface SystemHealthMetric {
  service: string;
  status: 'healthy' | 'degraded' | 'down';
  latencyMs: number;
  uptime: number;
  lastCheck: string;
}
