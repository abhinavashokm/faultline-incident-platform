"use client";

import React from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { LatencyBucket } from "../types";
import { AlertCircle, Clock } from "lucide-react";

interface LatencyHistogramProps {
  distribution?: LatencyBucket[];
  isLoading: boolean;
  error?: Error | null;
  totalSamples?: number;
}

export function LatencyHistogram({
  distribution,
  isLoading,
  error,
  totalSamples,
}: LatencyHistogramProps) {
  if (isLoading) {
    return (
      <div className="bg-card p-5 rounded-2xl border border-border shadow-xs animate-pulse space-y-4">
        <div className="h-5 w-48 bg-surface-container rounded" />
        <div className="h-4 w-64 bg-surface-container-low rounded" />
        <div className="h-48 w-full bg-surface-container-low rounded-xl mt-4" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card p-6 rounded-2xl border border-error/30 text-center space-y-2">
        <AlertCircle className="w-6 h-6 text-error mx-auto" />
        <h3 className="text-xs font-semibold text-text-primary">Failed to load latency distribution</h3>
        <p className="text-[11px] text-text-secondary">{error.message}</p>
      </div>
    );
  }

  const buckets = distribution || [];
  const totalCount =
    totalSamples ?? buckets.reduce((acc, b) => acc + (b.count || 0), 0);

  // Find last non-null boundary
  const boundaries = buckets.filter((b) => b.le_ms !== null).map((b) => b.le_ms as number);
  const lastBoundary = boundaries.length > 0 ? boundaries[boundaries.length - 1] : 1000;

  const chartData = buckets.map((bucket) => {
    let label = "";
    if (bucket.le_ms === null) {
      label = `>${lastBoundary >= 1000 ? `${lastBoundary / 1000}s` : `${lastBoundary}ms`}`;
    } else if (bucket.le_ms >= 1000) {
      label = `≤${bucket.le_ms / 1000}s`;
    } else {
      label = `≤${bucket.le_ms}ms`;
    }

    const pct = totalCount > 0 ? (bucket.count / totalCount) * 100 : 0;

    return {
      bucketLabel: label,
      count: bucket.count,
      percentage: Number(pct.toFixed(1)),
      isOverflow: bucket.le_ms === null,
    };
  });

  return (
    <div className="bg-card p-5 rounded-2xl border border-border shadow-xs flex flex-col justify-between">
      <div>
        <div className="space-y-0.5">
          <h2 className="text-sm font-semibold text-text-primary">Latency Distribution</h2>
          <p className="text-xs text-text-secondary">
            Request latency bucketed by cumulative response thresholds
          </p>
        </div>

        <div className="mt-6 h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 12, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e4ee" vertical={false} opacity={0.6} />
              <XAxis
                dataKey="bucketLabel"
                tick={{ fontSize: 11, fill: "#424754", fontFamily: "JetBrains Mono, monospace" }}
                axisLine={{ stroke: "#e2e4ee" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#424754", fontFamily: "JetBrains Mono, monospace" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v)}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="rounded-lg bg-[#131b2e] px-3 py-2 text-white shadow-xl border border-[#283044] text-xs font-mono select-none pointer-events-none z-50">
                        <div className="text-[#a0aec0] text-[11px] mb-0.5">{data.bucketLabel}</div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white">
                            {data.count.toLocaleString()} req ({data.percentage}%)
                          </span>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
                cursor={{ fill: "rgba(0, 88, 190, 0.05)" }}
              />
              <Bar
                dataKey="count"
                fill="#0058be"
                radius={[4, 4, 0, 0]}
                maxBarSize={48}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="mt-4 pt-3 flex items-center justify-between text-xs text-text-secondary bg-surface-container-low p-2.5 rounded-lg border border-border/40">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-primary" />
          <span>Cumulative distribution buckets</span>
        </div>
        <span className="font-mono text-text-primary font-semibold tabular-nums">
          {totalCount.toLocaleString()} total samples
        </span>
      </div>
    </div>
  );
}
