"use client";

import React from "react";
import { AlertCircle, AlertTriangle, RefreshCw } from "lucide-react";
import { PerformanceSummary } from "../types";

interface KpiData {
  request_count: number;
  error_count?: number;
  error_rate: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  is_empty_telemetry?: boolean;
}

interface KpiCardsSectionProps {
  data?: KpiData;
  isLoading: boolean;
  error?: Error | null;
  onRetry?: () => void;
  hideErrorsCount?: boolean;
}

function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return num.toLocaleString();
}

function formatLatency(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${ms}ms`;
}

export function KpiCardsSection({
  data,
  isLoading,
  error,
  onRetry,
  hideErrorsCount = false,
}: KpiCardsSectionProps) {
  const cardCount = hideErrorsCount ? 5 : 6;

  if (isLoading) {
    return (
      <div className={`grid grid-cols-2 sm:grid-cols-3 ${hideErrorsCount ? "lg:grid-cols-5" : "lg:grid-cols-6"} gap-3.5`}>
        {Array.from({ length: cardCount }).map((_, i) => (
          <div
            key={i}
            className="bg-card p-4 rounded-2xl border border-border shadow-xs animate-pulse space-y-2"
          >
            <div className="h-3 w-16 bg-surface-container rounded" />
            <div className="h-7 w-20 bg-surface-container rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card rounded-2xl border border-error/30 p-5 flex items-center justify-between gap-4 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-error-container/40 flex items-center justify-center text-error flex-shrink-0">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-text-primary">Failed to load performance metrics</h4>
            <p className="text-[11px] text-text-secondary">
              {(error as any)?.detail || error.message || "Summary calculation unavailable"}
            </p>
          </div>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-xs font-semibold text-text-primary border border-border transition-colors flex-shrink-0"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry
          </button>
        )}
      </div>
    );
  }

  const items = [
    { label: "Requests", value: formatNumber(data?.request_count ?? 0) },
    ...(hideErrorsCount
      ? []
      : [{ label: "Errors", value: formatNumber(data?.error_count ?? 0) }]),
    {
      label: "Error rate",
      value: `${(data?.error_rate ?? 0).toFixed(2)}%`,
      highlight: (data?.error_rate ?? 0) > 1 ? "text-error" : undefined,
    },
    { label: "p50", value: formatLatency(data?.p50_ms ?? 0) },
    { label: "p95", value: formatLatency(data?.p95_ms ?? 0) },
    { label: "p99", value: formatLatency(data?.p99_ms ?? 0) },
  ];

  const isNoTelemetry = data?.is_empty_telemetry;

  return (
    <div className="space-y-3">
      {isNoTelemetry && (
        <div className="bg-amber-500/10 border border-amber-500/25 rounded-2xl p-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center text-amber-500 flex-shrink-0">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-text-primary">No telemetry found for this project</h4>
            <p className="text-[11px] text-text-secondary">
              No performance data has been received yet. Check if something is wrong with your SDK setup or ingestion configuration.
            </p>
          </div>
        </div>
      )}

      <div className={`grid grid-cols-2 sm:grid-cols-3 ${hideErrorsCount ? "lg:grid-cols-5" : "lg:grid-cols-6"} gap-3.5`}>
        {items.map((item) => (
          <div
            key={item.label}
            className="bg-card p-4 rounded-2xl border border-border shadow-xs flex flex-col justify-between"
          >
            <div className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
              {item.label}
            </div>
            <div
              className={`mt-2 text-2xl font-bold font-mono tracking-tight tabular-nums ${
                item.highlight || "text-text-primary"
              }`}
            >
              {item.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
