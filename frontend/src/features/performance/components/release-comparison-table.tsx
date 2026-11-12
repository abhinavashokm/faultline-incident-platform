"use client";

import React from "react";
import { AlertCircle, TrendingUp, Info } from "lucide-react";
import { ReleasePerformance } from "../types";

interface ReleaseComparisonTableProps {
  releases?: ReleasePerformance[];
  isLoading: boolean;
  error?: Error | null;
  activeReleaseFilter?: string;
}

function formatLatency(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${ms}ms`;
}

function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return num.toLocaleString();
}

export function ReleaseComparisonTable({
  releases,
  isLoading,
  error,
  activeReleaseFilter,
}: ReleaseComparisonTableProps) {
  if (isLoading) {
    return (
      <div className="bg-card p-5 rounded-2xl border border-border shadow-xs animate-pulse space-y-4">
        <div className="h-5 w-48 bg-surface-container rounded" />
        <div className="h-4 w-72 bg-surface-container-low rounded" />
        <div className="space-y-2 pt-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 bg-surface-container-low rounded-lg w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card p-6 rounded-2xl border border-error/30 text-center space-y-2">
        <AlertCircle className="w-6 h-6 text-error mx-auto" />
        <h3 className="text-xs font-semibold text-text-primary">Failed to load release comparisons</h3>
        <p className="text-[11px] text-text-secondary">{error.message}</p>
      </div>
    );
  }

  const items = releases || [];

  // Identify worst p95 and worst error rate to highlight regressions
  const worstP95 = items.length > 0 ? Math.max(...items.map((r) => r.p95_ms)) : 0;
  const worstErr = items.length > 0 ? Math.max(...items.map((r) => r.error_rate)) : 0;

  return (
    <div className="bg-card p-5 rounded-2xl border border-border shadow-xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
        <div>
          <h2 className="text-sm font-semibold text-text-primary">Performance by Release</h2>
          <div className="flex items-center gap-1.5 text-xs text-text-secondary mt-0.5">
            <Info className="w-3.5 h-3.5 text-primary" />
            <span>
              Always shows all releases active in this time window (ignores release filter).
            </span>
          </div>
        </div>
        <div className="font-mono text-xs text-text-secondary">
          {items.length} releases active
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-surface-container-low/60 text-text-secondary uppercase text-[11px] font-semibold tracking-wider border-b border-border select-none">
            <tr>
              <th className="py-2.5 px-4 rounded-l-lg">Release</th>
              <th className="py-2.5 px-4 text-right">Requests</th>
              <th className="py-2.5 px-4 text-right">Error Rate</th>
              <th className="py-2.5 px-4 text-right rounded-r-lg">p95 Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40 font-mono">
            {items.map((item) => {
              const isSelectedRelease =
                activeReleaseFilter && activeReleaseFilter === item.release;
              const isWorstP95 = items.length > 1 && item.p95_ms === worstP95;
              const isWorstErr = items.length > 1 && item.error_rate === worstErr && worstErr > 1;

              return (
                <tr
                  key={item.release}
                  className={`hover:bg-surface-container-low/70 transition-colors ${
                    isSelectedRelease ? "bg-primary/5" : ""
                  }`}
                >
                  <td className="py-3 px-4 font-semibold text-text-primary">
                    <div className="flex items-center gap-2">
                      <span className={isSelectedRelease ? "text-primary font-bold" : ""}>
                        {item.release}
                      </span>
                      {isSelectedRelease && (
                        <span className="px-2 py-0.5 rounded-full bg-primary text-white text-[10px] font-medium font-sans">
                          Filter match
                        </span>
                      )}
                    </div>
                  </td>

                  <td className="py-3 px-4 text-right tabular-nums text-text-primary">
                    {formatNumber(item.requests)}
                  </td>

                  <td className="py-3 px-4 text-right tabular-nums">
                    <div className="inline-flex items-center justify-end gap-1.5">
                      <span
                        className={`font-semibold ${
                          isWorstErr ? "text-error" : item.error_rate > 1 ? "text-error/80" : "text-text-primary"
                        }`}
                      >
                        {item.error_rate.toFixed(2)}%
                      </span>
                      {isWorstErr && (
                        <span
                          className="w-1.5 h-1.5 rounded-full bg-error"
                          title="Highest error rate across releases"
                        />
                      )}
                    </div>
                  </td>

                  <td className="py-3 px-4 text-right tabular-nums">
                    <div className="inline-flex items-center justify-end gap-1.5">
                      <span
                        className={`font-semibold ${
                          isWorstP95 ? "text-error font-bold" : "text-text-primary"
                        }`}
                      >
                        {formatLatency(item.p95_ms)}
                      </span>
                      {isWorstP95 && (
                        <span title="Highest p95 latency (regression indicator)" className="inline-flex items-center">
                          <TrendingUp className="w-3.5 h-3.5 text-error" />
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
