"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  AlertCircle,
  RefreshCw,
  Inbox,
  AlertTriangle,
} from "lucide-react";
import { EndpointMetricItem, PerformanceEndpointsResponse } from "../types";

interface EndpointsTableSectionProps {
  data?: PerformanceEndpointsResponse;
  isLoading: boolean;
  error?: Error | null;
  onRetry?: () => void;
  workspaceSlug: string;
  projectSlug: string;
  filterQueryParams?: {
    from?: string;
    to?: string;
    environment?: string;
    release?: string;
    range?: string;
  };
}

type SortColumn = "route" | "method" | "requests" | "error_rate" | "p50_ms" | "p95_ms" | "p99_ms";
type SortDirection = "asc" | "desc";

function getMethodBadgeStyle(method: string) {
  switch (method.toUpperCase()) {
    case "GET":
      return "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300";
    case "POST":
      return "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300";
    case "PUT":
      return "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300";
    case "DELETE":
      return "bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300";
    case "PATCH":
      return "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950 dark:text-purple-300";
    default:
      return "bg-gray-100 text-gray-700 border-gray-200";
  }
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

export function EndpointsTableSection({
  data,
  isLoading,
  error,
  onRetry,
  workspaceSlug,
  projectSlug,
  filterQueryParams,
}: EndpointsTableSectionProps) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [sortCol, setSortCol] = useState<SortColumn>("p95_ms");
  const [sortDir, setSortDir] = useState<SortDirection>("desc");
  const [pageSize, setPageSize] = useState<number>(25);
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Sorting handler
  const handleSort = (col: SortColumn) => {
    if (sortCol === col) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("desc");
    }
    setCurrentPage(1);
  };

  // Filtered & sorted items
  const filteredAndSortedItems = useMemo(() => {
    if (!data?.items) return [];

    let items = [...data.items];

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      items = items.filter(
        (it) => it.route.toLowerCase().includes(q) || it.method.toLowerCase().includes(q)
      );
    }

    items.sort((a, b) => {
      let aVal = a[sortCol];
      let bVal = b[sortCol];

      if (typeof aVal === "string") {
        return sortDir === "asc"
          ? (aVal as string).localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal as string);
      }

      return sortDir === "asc" ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
    });

    return items;
  }, [data?.items, search, sortCol, sortDir]);

  // Pagination slicing
  const totalPages = Math.max(1, Math.ceil(filteredAndSortedItems.length / pageSize));
  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAndSortedItems.slice(start, start + pageSize);
  }, [filteredAndSortedItems, currentPage, pageSize]);

  if (isLoading) {
    return (
      <div className="bg-card rounded-2xl border border-border p-5 shadow-xs animate-pulse space-y-4">
        <div className="flex justify-between items-center">
          <div className="h-8 w-64 bg-surface-container rounded-lg" />
          <div className="h-4 w-32 bg-surface-container rounded" />
        </div>
        <div className="space-y-2 pt-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-10 bg-surface-container-low rounded-lg w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card rounded-2xl border border-error/30 p-8 text-center space-y-3 shadow-xs">
        <div className="w-12 h-12 mx-auto rounded-full bg-error-container/40 flex items-center justify-center text-error">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-semibold text-text-primary">Failed to load endpoints list</h3>
        <p className="text-xs text-text-secondary max-w-sm mx-auto">
          {(error as any)?.detail || error.message || "An error occurred while loading endpoints."}
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

  const items = data?.items || [];
  if (items.length === 0) {
    return (
      <div className="bg-card rounded-2xl border border-border p-10 text-center space-y-3 shadow-xs">
        <div className="w-12 h-12 mx-auto rounded-full bg-surface-container flex items-center justify-center text-text-secondary">
          <Inbox className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-semibold text-text-primary">No endpoints found</h3>
        <p className="text-xs text-text-secondary max-w-sm mx-auto">
          No endpoint telemetry has been captured for this project within the selected range.
        </p>
      </div>
    );
  }

  const renderSortIcon = (col: SortColumn) => {
    if (sortCol !== col) {
      return <ArrowUpDown className="w-3.5 h-3.5 opacity-40 ml-1 inline" />;
    }
    return sortDir === "asc" ? (
      <ArrowUp className="w-3.5 h-3.5 text-primary ml-1 inline" />
    ) : (
      <ArrowDown className="w-3.5 h-3.5 text-primary ml-1 inline" />
    );
  };

  return (
    <div className="bg-card rounded-2xl border border-border shadow-xs overflow-hidden flex flex-col">
      {/* Truncation notice banner if total > 500 */}
      {data?.truncated && (
        <div className="bg-amber-50 dark:bg-amber-950/40 border-b border-amber-200 dark:border-amber-900/60 px-4 py-2.5 flex items-center gap-2 text-xs text-amber-800 dark:text-amber-300">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>
            Showing top 500 of {data.total} endpoints (sorted by p95 latency descending)
          </span>
        </div>
      )}

      {/* Table Header: Search & Info */}
      <div className="p-4 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-text-secondary" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Filter by route or method..."
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-surface-container-low text-text-primary text-xs font-mono border border-border placeholder:font-sans placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <div className="text-xs text-text-secondary font-medium">
          Showing {filteredAndSortedItems.length} of {data?.total || items.length} endpoints
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="bg-surface-container-low/60 text-xs font-semibold text-text-secondary border-b border-border select-none">
            <tr>
              <th
                onClick={() => handleSort("route")}
                className="py-3 px-4 cursor-pointer hover:text-text-primary"
              >
                Route {renderSortIcon("route")}
              </th>
              <th
                onClick={() => handleSort("method")}
                className="py-3 px-4 cursor-pointer hover:text-text-primary"
              >
                Method {renderSortIcon("method")}
              </th>
              <th
                onClick={() => handleSort("requests")}
                className="py-3 px-4 text-right cursor-pointer hover:text-text-primary"
              >
                Requests {renderSortIcon("requests")}
              </th>
              <th
                onClick={() => handleSort("error_rate")}
                className="py-3 px-4 text-right cursor-pointer hover:text-text-primary"
              >
                Error rate {renderSortIcon("error_rate")}
              </th>
              <th
                onClick={() => handleSort("p50_ms")}
                className="py-3 px-4 text-right cursor-pointer hover:text-text-primary"
              >
                p50 {renderSortIcon("p50_ms")}
              </th>
              <th
                onClick={() => handleSort("p95_ms")}
                className={`py-3 px-4 text-right cursor-pointer ${
                  sortCol === "p95_ms" ? "text-primary font-bold bg-primary/5" : "hover:text-text-primary"
                }`}
              >
                p95 {renderSortIcon("p95_ms")}
              </th>
              <th
                onClick={() => handleSort("p99_ms")}
                className="py-3 px-4 text-right cursor-pointer hover:text-text-primary"
              >
                p99 {renderSortIcon("p99_ms")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60 text-xs font-mono">
            {paginatedItems.map((item, index) => {
              // Target URL with route and method as query params, carrying over time & filters
              const searchParamsObj = new URLSearchParams();
              searchParamsObj.set("route", item.route);
              searchParamsObj.set("method", item.method);

              if (filterQueryParams?.from) searchParamsObj.set("from", filterQueryParams.from);
              if (filterQueryParams?.to) searchParamsObj.set("to", filterQueryParams.to);
              if (filterQueryParams?.range) searchParamsObj.set("range", filterQueryParams.range);
              if (filterQueryParams?.environment) searchParamsObj.set("environment", filterQueryParams.environment);
              if (filterQueryParams?.release) searchParamsObj.set("release", filterQueryParams.release);

              const targetUrl = `/${workspaceSlug}/${projectSlug}/performance/endpoint?${searchParamsObj.toString()}`;

              return (
                <tr
                  key={`${item.route}-${item.method}-${index}`}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      router.push(targetUrl);
                    }
                  }}
                  className="hover:bg-surface-container-low/70 transition-colors group cursor-pointer focus:outline-none focus:bg-primary/5"
                >
                  <td className="py-3 px-4 font-medium text-primary">
                    <Link
                      href={targetUrl}
                      className="hover:underline flex items-center gap-1.5 focus:outline-none"
                    >
                      {item.route}
                    </Link>
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getMethodBadgeStyle(
                        item.method
                      )}`}
                    >
                      {item.method}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right text-text-primary tabular-nums">
                    {formatNumber(item.requests)}
                  </td>
                  <td
                    className={`py-3 px-4 text-right tabular-nums ${
                      item.error_rate > 1 ? "text-error font-medium" : "text-text-primary"
                    }`}
                  >
                    {item.error_rate.toFixed(2)}%
                  </td>
                  <td className="py-3 px-4 text-right text-text-secondary tabular-nums">
                    {formatLatency(item.p50_ms)}
                  </td>
                  <td
                    className={`py-3 px-4 text-right font-semibold tabular-nums ${
                      sortCol === "p95_ms" ? "bg-primary/5 text-primary" : "text-text-primary"
                    }`}
                  >
                    {formatLatency(item.p95_ms)}
                  </td>
                  <td className="py-3 px-4 text-right text-text-secondary tabular-nums">
                    {formatLatency(item.p99_ms)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-3 border-t border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-text-secondary">
        <div>
          Showing {paginatedItems.length === 0 ? 0 : (currentPage - 1) * pageSize + 1} -{" "}
          {Math.min(currentPage * pageSize, filteredAndSortedItems.length)} of{" "}
          {filteredAndSortedItems.length}
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span>Show:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="bg-surface-container-low border border-border rounded-md py-1 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
            </select>
          </div>

          <div className="inline-flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="px-2.5 py-1 rounded-md border border-border bg-surface-container-low text-text-secondary hover:text-text-primary hover:bg-surface-container transition-colors disabled:opacity-40"
            >
              Previous
            </button>
            <span className="px-2 font-mono text-text-primary">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="px-2.5 py-1 rounded-md border border-border bg-surface-container-low text-text-secondary hover:text-text-primary hover:bg-surface-container transition-colors disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
