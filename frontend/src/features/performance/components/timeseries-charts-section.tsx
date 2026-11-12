"use client";

import React from "react";
import { AlertCircle, RefreshCw, BarChart2 } from "lucide-react";
import { TimeseriesChart } from "./timeseries-chart";
import { PerformanceTimeseries } from "../types";

interface TimeseriesChartsSectionProps {
  data?: PerformanceTimeseries;
  isLoading: boolean;
  error?: Error | null;
  onRetry?: () => void;
}

export function TimeseriesChartsSection({
  data,
  isLoading,
  error,
  onRetry,
}: TimeseriesChartsSectionProps) {
  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        {[1, 2, 3].map((idx) => (
          <div key={idx} className="bg-card rounded-2xl border border-border p-5 h-44 flex flex-col justify-between">
            <div className="flex justify-between items-center">
              <div className="h-4 w-36 bg-surface-container rounded" />
              <div className="h-3 w-20 bg-surface-container rounded" />
            </div>
            <div className="h-28 w-full bg-surface-container-low rounded-lg" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card rounded-2xl border border-error/30 p-8 text-center space-y-3 shadow-xs">
        <div className="w-12 h-12 mx-auto rounded-full bg-error-container/40 flex items-center justify-center text-error">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-semibold text-text-primary">Failed to load performance timeseries</h3>
        <p className="text-xs text-text-secondary max-w-sm mx-auto">
          {(error as any)?.detail || error.message || "An unexpected error occurred while loading charts."}
        </p>
        {onRetry && (
          <div className="pt-2">
            <button
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-xs font-semibold text-text-primary border border-border transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Retry
            </button>
          </div>
        )}
      </div>
    );
  }

  const points = data?.points || [];
  const isEmpty = points.length === 0;

  if (isEmpty) {
    return (
      <div className="bg-card rounded-2xl border border-border p-10 text-center space-y-3 shadow-xs">
        <div className="w-12 h-12 mx-auto rounded-full bg-surface-container flex items-center justify-center text-text-secondary">
          <BarChart2 className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-semibold text-text-primary">No timeseries data in range</h3>
        <p className="text-xs text-text-secondary max-w-sm mx-auto">
          There are no recorded metric intervals for the selected time range and filters.
        </p>
      </div>
    );
  }

  const intervalSeconds = data?.interval_seconds || 60;

  // Calculate summaries for header labels
  const totalRequests = points.reduce((acc, p) => acc + (p.requests || 0), 0);
  const validErrors = points.filter((p) => p.error_rate !== null).map((p) => p.error_rate as number);
  const avgErrorRate =
    validErrors.length > 0 ? (validErrors.reduce((a, b) => a + b, 0) / validErrors.length).toFixed(2) : "0.00";
  const validP95 = points.filter((p) => p.p95_ms !== null).map((p) => p.p95_ms as number);
  const maxP95 = validP95.length > 0 ? Math.max(...validP95) : 0;

  return (
    <div className="space-y-4">
      {/* 1. Requests over time */}
      <TimeseriesChart
        title="Requests over time"
        subtitle={`Total: ${totalRequests.toLocaleString()}`}
        data={points}
        dataKey="requests"
        type="bar"
        intervalSeconds={intervalSeconds}
        fillColor="#0058be"
        formatter={(val) => `${val.toLocaleString()} req`}
      />

      {/* 2. Error rate over time */}
      <TimeseriesChart
        title="Error rate over time"
        subtitle={`Avg: ${avgErrorRate}%`}
        data={points}
        dataKey="error_rate"
        type="line"
        intervalSeconds={intervalSeconds}
        strokeColor="#ba1a1a"
        formatter={(val) => `${val.toFixed(2)}%`}
      />

      {/* 3. p95 latency over time */}
      <TimeseriesChart
        title="p95 latency over time"
        subtitle={`Peak: ${maxP95 >= 1000 ? `${(maxP95 / 1000).toFixed(2)}s` : `${maxP95}ms`}`}
        data={points}
        dataKey="p95_ms"
        type="line"
        intervalSeconds={intervalSeconds}
        strokeColor="#0058be"
        formatter={(val) => (val >= 1000 ? `${(val / 1000).toFixed(2)}s` : `${val}ms`)}
      />
    </div>
  );
}
