"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, Radio } from "lucide-react";

interface EndpointHeaderProps {
  method: string;
  route: string;
  overviewBackUrl: string;
}

function getMethodBadgeClass(method: string) {
  switch (method.toUpperCase()) {
    case "GET":
      return "bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800 dark:text-slate-200";
    case "POST":
      return "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-950 dark:text-blue-200";
    case "PUT":
      return "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950 dark:text-amber-200";
    case "DELETE":
      return "bg-red-100 text-red-800 border-red-200 dark:bg-red-950 dark:text-red-200";
    case "PATCH":
      return "bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-950 dark:text-purple-200";
    default:
      return "bg-gray-100 text-gray-800 border-gray-200";
  }
}

export function EndpointHeader({
  method,
  route,
  overviewBackUrl,
}: EndpointHeaderProps) {
  return (
    <div className="space-y-4">
      {/* Navigation Breadcrumb */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <nav className="flex items-center gap-2 text-xs text-text-secondary">
          <Link
            href={overviewBackUrl}
            className="inline-flex items-center gap-1.5 text-primary hover:text-primary/80 font-medium transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Performance Overview</span>
          </Link>
          <span className="text-border">/</span>
          <span>Endpoints</span>
          <span className="text-border">/</span>
          <span className="font-mono font-semibold text-text-primary">
            {method} {route}
          </span>
        </nav>

        <div className="flex items-center gap-2 font-mono text-[11px] text-text-secondary bg-surface-container-low px-2.5 py-1 rounded-full border border-border/40">
          <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
          <span>Telemetry Stream Active</span>
        </div>
      </div>

      {/* Main Title Row */}
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          <span
            className={`px-2.5 py-0.5 rounded-lg font-mono text-xs font-bold tracking-wide border ${getMethodBadgeClass(
              method
            )}`}
          >
            {method.toUpperCase()}
          </span>
          <h1 className="font-mono text-2xl font-bold tracking-tight text-text-primary">
            {route}
          </h1>
        </div>
        <p className="text-xs text-text-secondary">
          Endpoint metrics, latency distribution, and release performance for {method.toUpperCase()} {route}
        </p>
      </div>
    </div>
  );
}
