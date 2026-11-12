"use client";

import React from "react";
import { AlertCircle } from "lucide-react";

interface StatusBreakdownProps {
  statusCounts?: Record<string, number>;
  isLoading: boolean;
  error?: Error | null;
}

function getStatusDetails(code: string): { label: string; description: string; color: string; badge: string; bg: string } {
  const c = parseInt(code, 10);
  if (c >= 200 && c < 300) {
    return {
      label: `${code} OK`,
      description: "Successful requests",
      color: "#16a34a", // emerald-600
      badge: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
      bg: "bg-emerald-600",
    };
  }
  if (c >= 300 && c < 400) {
    return {
      label: `${code} Redirection`,
      description: "Redirect responses",
      color: "#2563eb", // blue-600
      badge: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
      bg: "bg-blue-600",
    };
  }
  if (c >= 400 && c < 500) {
    return {
      label: code === "404" ? "404 Not Found" : code === "422" ? "422 Unprocessable" : `${code} Bad Request`,
      description: "Client error responses",
      color: "#f59e0b", // amber-500
      badge: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
      bg: "bg-amber-500",
    };
  }
  return {
    label: code === "500" ? "500 Internal Error" : code === "504" ? "504 Gateway Timeout" : `${code} Server Error`,
    description: "Server/runtime errors",
    color: "#ba1a1a", // red-600 / error
    badge: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
    bg: "bg-[#ba1a1a]",
  };
}

export function StatusBreakdown({
  statusCounts,
  isLoading,
  error,
}: StatusBreakdownProps) {
  if (isLoading) {
    return (
      <div className="bg-card p-5 rounded-2xl border border-border shadow-xs animate-pulse space-y-4">
        <div className="h-5 w-48 bg-surface-container rounded" />
        <div className="h-4 w-64 bg-surface-container-low rounded" />
        <div className="h-4 w-full bg-surface-container rounded-full mt-4" />
        <div className="space-y-2 mt-4">
          {[1, 2, 3].map((i) => (
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
        <h3 className="text-xs font-semibold text-text-primary">Failed to load status counts</h3>
        <p className="text-[11px] text-text-secondary">{error.message}</p>
      </div>
    );
  }

  const counts = statusCounts || {};
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((acc, [, cnt]) => acc + cnt, 0);

  // Group by category for top proportional bar
  const categories = {
    "2xx": 0,
    "3xx": 0,
    "4xx": 0,
    "5xx": 0,
  };

  entries.forEach(([code, cnt]) => {
    const num = parseInt(code, 10);
    if (num >= 200 && num < 300) categories["2xx"] += cnt;
    else if (num >= 300 && num < 400) categories["3xx"] += cnt;
    else if (num >= 400 && num < 500) categories["4xx"] += cnt;
    else if (num >= 500) categories["5xx"] += cnt;
  });

  const pct = (val: number) => (total > 0 ? (val / total) * 100 : 0);

  return (
    <div className="bg-card p-5 rounded-2xl border border-border shadow-xs flex flex-col justify-between">
      <div>
        <div className="space-y-0.5">
          <h2 className="text-sm font-semibold text-text-primary">Status Code Breakdown</h2>
          <p className="text-xs text-text-secondary">
            Proportional request volume by HTTP response status code
          </p>
        </div>

        {/* Proportional Segment Bar */}
        <div className="mt-5 space-y-1.5">
          <div className="h-3 w-full rounded-full bg-surface-container flex overflow-hidden">
            {categories["2xx"] > 0 && (
              <div
                className="bg-emerald-600 h-full transition-all"
                style={{ width: `${pct(categories["2xx"])}%` }}
                title={`2xx: ${pct(categories["2xx"]).toFixed(1)}%`}
              />
            )}
            {categories["3xx"] > 0 && (
              <div
                className="bg-blue-600 h-full transition-all"
                style={{ width: `${pct(categories["3xx"])}%` }}
                title={`3xx: ${pct(categories["3xx"]).toFixed(1)}%`}
              />
            )}
            {categories["4xx"] > 0 && (
              <div
                className="bg-amber-500 h-full transition-all"
                style={{ width: `${pct(categories["4xx"])}%` }}
                title={`4xx: ${pct(categories["4xx"]).toFixed(1)}%`}
              />
            )}
            {categories["5xx"] > 0 && (
              <div
                className="bg-[#ba1a1a] h-full transition-all"
                style={{ width: `${pct(categories["5xx"])}%` }}
                title={`5xx: ${pct(categories["5xx"]).toFixed(1)}%`}
              />
            )}
          </div>

          <div className="flex justify-between text-[11px] font-mono text-text-secondary pt-0.5">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-600" />
              2xx ({pct(categories["2xx"]).toFixed(1)}%)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              4xx ({pct(categories["4xx"]).toFixed(1)}%)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#ba1a1a]" />
              5xx ({pct(categories["5xx"]).toFixed(1)}%)
            </span>
          </div>
        </div>

        {/* List of individual status codes */}
        <div className="mt-5 space-y-2">
          {entries.length === 0 ? (
            <p className="text-xs text-text-secondary">No status codes reported.</p>
          ) : (
            entries.map(([code, count]) => {
              const meta = getStatusDetails(code);
              const percentage = pct(count).toFixed(2);

              return (
                <div
                  key={code}
                  className="flex items-center justify-between p-2 rounded-lg bg-surface-container-low border border-border/40 text-xs"
                >
                  <div className="flex items-center gap-2.5">
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: meta.color }}
                    />
                    <span className="font-mono font-semibold text-text-primary">
                      {code}
                    </span>
                    <span className="text-[11px] text-text-secondary hidden sm:inline">
                      {meta.description}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 font-mono">
                    <span className="text-text-primary tabular-nums">
                      {count.toLocaleString()}
                    </span>
                    <span className={`font-semibold px-1.5 py-0.5 rounded text-[11px] ${meta.badge}`}>
                      {percentage}%
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="mt-4 pt-3 flex items-center justify-between text-xs text-text-secondary bg-surface-container-low p-2.5 rounded-lg border border-border/40">
        <span>Non-2xx failures:</span>
        <span className="font-mono font-semibold text-error tabular-nums">
          {(total - categories["2xx"]).toLocaleString()} requests
        </span>
      </div>
    </div>
  );
}
