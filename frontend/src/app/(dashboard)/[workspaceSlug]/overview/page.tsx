"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  TrendingUp,
  AlertTriangle,
  Flame,
  Activity,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  ExternalLink,
  ChevronRight,
  Filter,
  CheckCircle2,
  Terminal,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useOverviewDashboard } from "@/features/overview/hooks";
import { IssueItem } from "@/features/overview/types";

// SVG Sparkline component (48px high per DESIGN.md spec)
function Sparkline({ data, color = "#3B82F6" }: { data: number[]; color?: string }) {
  if (!data || data.length === 0) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const width = 140;
  const height = 36;

  const points = data.map((val, idx) => {
    const x = (idx / (data.length - 1)) * width;
    const y = height - ((val - min) / range) * (height - 8) - 4;
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(" L ")}`;
  const areaD = `${pathD} L ${width},${height} L 0,${height} Z`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible"
    >
      <path d={areaD} fill={color} fillOpacity="0.08" />
      <path
        d={pathD}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function OverviewPage() {
  const params = useParams();
  const workspaceSlug = (params.workspaceSlug as string) || "acme-cloud";

  const [selectedIssueIds, setSelectedIssueIds] = useState<string[]>([
    "iss_42b56e9a",
  ]);
  const [simulationMode, setSimulationMode] = useState<"normal" | "empty" | "error">("normal");

  const { data, isLoading, isError, error, refetch, isFetching } = useOverviewDashboard(
    workspaceSlug,
    {
      isEmpty: simulationMode === "empty",
      shouldFail: simulationMode === "error",
    }
  );

  const toggleSelectIssue = (id: string) => {
    setSelectedIssueIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = (issues: IssueItem[]) => {
    if (selectedIssueIds.length === issues.length) {
      setSelectedIssueIds([]);
    } else {
      setSelectedIssueIds(issues.map((i) => i.id));
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-headline-md font-semibold text-text-primary tracking-tight">
              Overview
            </h1>
            <Badge variant="success" showDot>
              Live Telemetry
            </Badge>
          </div>
          <p className="text-body-sm text-text-secondary mt-0.5">
            Real-time error trends, latency regressions, and service health across clusters.
          </p>
        </div>

        {/* Demo state simulation pills & Refresh */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-md border border-border bg-card p-0.5 shadow-level-1 text-label-sm">
            <button
              type="button"
              onClick={() => setSimulationMode("normal")}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${
                simulationMode === "normal"
                  ? "bg-primary-tint text-primary font-semibold"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              Normal
            </button>
            <button
              type="button"
              onClick={() => setSimulationMode("empty")}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${
                simulationMode === "empty"
                  ? "bg-primary-tint text-primary font-semibold"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              Empty
            </button>
            <button
              type="button"
              onClick={() => setSimulationMode("error")}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${
                simulationMode === "error"
                  ? "bg-error-container text-error font-semibold"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              Error
            </button>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
            <span>Sync</span>
          </Button>

          <Button asChild size="sm" className="gap-1.5">
            <Link href="/onboarding/install-sdk">
              <Terminal className="h-3.5 w-3.5" />
              <span>Connect SDK</span>
            </Link>
          </Button>
        </div>
      </div>

      {/* ERROR STATE */}
      {isError && (
        <Alert variant="destructive" className="shadow-level-2">
          <AlertCircle className="h-5 w-5" />
          <AlertTitle className="text-body-md font-semibold">
            Telemetry Stream Unavailable
          </AlertTitle>
          <AlertDescription className="mt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span>
              {(error as any)?.message ||
                "Failed to load telemetry overview metrics. The ingestion worker timed out."}
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setSimulationMode("normal");
                refetch();
              }}
              className="bg-card shrink-0"
            >
              Retry Connection
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* SKELETON LOADING STATE */}
      {isLoading && (
        <div className="space-y-6">
          {/* 4 Metric Card Skeletons */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="rounded-lg border border-border bg-card p-4 space-y-3 shadow-level-1"
              >
                <div className="flex items-center justify-between">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-5 w-14 rounded-full" />
                </div>
                <div className="flex items-baseline justify-between pt-1">
                  <Skeleton className="h-8 w-28" />
                  <Skeleton className="h-9 w-24" />
                </div>
              </div>
            ))}
          </div>

          {/* Chart Skeleton */}
          <div className="rounded-lg border border-border bg-card p-6 space-y-4 shadow-level-1">
            <Skeleton className="h-5 w-44" />
            <Skeleton className="h-44 w-full" />
          </div>

          {/* Table Skeleton */}
          <div className="rounded-lg border border-border bg-card p-6 space-y-4 shadow-level-1">
            <Skeleton className="h-5 w-32" />
            <div className="space-y-2">
              {[1, 2, 3, 4].map((j) => (
                <Skeleton key={j} className="h-11 w-full" />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* LOADED CONTENT */}
      {!isLoading && !isError && data && (
        <>
          {/* EMPTY STATE */}
          {data.recentIssues.length === 0 && data.metrics[0].rawNumber === 0 ? (
            <div className="rounded-lg border border-border bg-card p-12 text-center shadow-level-1">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary-tint border border-primary-subdued text-primary mb-4">
                <Terminal className="h-7 w-7" />
              </div>
              <h3 className="text-headline-sm font-semibold text-text-primary">
                No events received yet
              </h3>
              <p className="text-body-sm text-text-secondary max-w-md mx-auto mt-1 mb-6">
                Your workspace is ready. Instrument your application with the Faultline SDK to start capturing stack traces and operational anomalies in real time.
              </p>
              <div className="flex items-center justify-center gap-3">
                <Button asChild className="gap-2">
                  <Link href="/onboarding/install-sdk">
                    <span>Install SDK</span>
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setSimulationMode("normal")}
                >
                  Load Sample Data
                </Button>
              </div>
            </div>
          ) : (
            <>
              {/* 1. Four Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {data.metrics.map((metric) => (
                  <div
                    key={metric.id}
                    className="rounded-lg border border-border bg-card p-4 shadow-level-1 flex flex-col justify-between hover:border-border-hover transition-colors"
                  >
                    <div className="flex items-center justify-between text-label-md text-text-secondary">
                      <span className="font-medium">{metric.label}</span>
                      <Badge
                        variant={metric.statusVariant}
                        showDot={metric.statusVariant !== "default"}
                      >
                        {metric.change}
                      </Badge>
                    </div>

                    <div className="flex items-end justify-between mt-3">
                      <div>
                        <span className="text-[26px] font-semibold text-text-primary leading-none tracking-tight font-sans">
                          {metric.value}
                        </span>
                      </div>
                      <div className="shrink-0 h-9 flex items-center">
                        <Sparkline
                          data={metric.sparkline}
                          color={
                            metric.statusVariant === "error"
                              ? "#EF4444"
                              : metric.statusVariant === "warning"
                              ? "#F59E0B"
                              : metric.statusVariant === "success"
                              ? "#10B981"
                              : "#3B82F6"
                          }
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* 2. Events Over Time Visualizer */}
              <div className="rounded-lg border border-border bg-card p-5 shadow-level-1">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
                  <div>
                    <h2 className="text-title-md font-semibold text-text-primary">
                      Event Volume &amp; Ingestion Throughput
                    </h2>
                    <p className="text-[12px] text-text-secondary">
                      Total events processed over the last 24 hours (2-hour buckets)
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-label-sm font-mono">
                    <div className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-sm bg-primary" />
                      <span className="text-text-secondary">Normal Traffic</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-sm bg-error" />
                      <span className="text-text-secondary">Exceptions</span>
                    </div>
                  </div>
                </div>

                {/* Bar/Graph Visualization */}
                <div className="pt-2 pb-1">
                  <div className="flex items-end justify-between gap-1.5 sm:gap-3 h-36 px-1 border-b border-border">
                    {data.timeSeries.map((point) => {
                      const maxEvents = 140000;
                      const heightPercent = Math.max(
                        (point.events / maxEvents) * 100,
                        12
                      );
                      const hasError = point.errors > 50;

                      return (
                        <div
                          key={point.time}
                          className="flex-1 flex flex-col items-center gap-1.5 group relative"
                        >
                          {/* Tooltip on hover */}
                          <div className="absolute -top-10 hidden group-hover:flex flex-col items-center z-20 pointer-events-none">
                            <div className="rounded bg-text-primary text-canvas px-2 py-1 text-[10px] font-mono shadow-level-2 whitespace-nowrap">
                              {point.time}: {point.events.toLocaleString()} events ({point.errors} errs)
                            </div>
                          </div>

                          {/* Bar */}
                          <div className="w-full flex flex-col justify-end h-28">
                            <div
                              style={{ height: `${heightPercent}%` }}
                              className={`w-full rounded-t-sm transition-all duration-150 ${
                                hasError
                                  ? "bg-error/85 group-hover:bg-error"
                                  : "bg-primary/80 group-hover:bg-primary"
                              }`}
                            />
                          </div>

                          <span className="font-mono text-[10px] text-text-muted">
                            {point.time}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* 3. Recent Issues Table (Styled per DESIGN.md spec: 44px rows, mono columns, selected row style) */}
              <div className="rounded-lg border border-border bg-card shadow-level-1 overflow-hidden">
                <div className="p-4 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h2 className="text-title-md font-semibold text-text-primary">
                      Recent Unresolved Issues
                    </h2>
                    <p className="text-[12px] text-text-secondary">
                      Ranked by event frequency and user blast radius in active window.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-label-sm text-text-muted">
                      {selectedIssueIds.length} selected
                    </span>
                    <Button variant="secondary" size="sm" className="h-7 text-label-sm gap-1">
                      <Filter className="h-3 w-3" />
                      <span>Filter</span>
                    </Button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-canvas border-b border-border text-label-sm uppercase text-text-secondary h-9">
                        <th className="py-2 px-3.5 w-10 text-center">
                          <input
                            type="checkbox"
                            checked={
                              selectedIssueIds.length === data.recentIssues.length &&
                              data.recentIssues.length > 0
                            }
                            onChange={() => toggleSelectAll(data.recentIssues)}
                            className="h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary focus:ring-offset-0 cursor-pointer"
                          />
                        </th>
                        <th className="py-2 px-3 font-medium">Issue &amp; Root Cause Culprit</th>
                        <th className="py-2 px-3 font-medium">Environment</th>
                        <th className="py-2 px-3 font-medium text-right">Events</th>
                        <th className="py-2 px-3 font-medium text-right">Users</th>
                        <th className="py-2 px-3 font-medium">Commit SHA</th>
                        <th className="py-2 px-3 font-medium text-right">Last Seen</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {data.recentIssues.map((issue) => {
                        const isSelected = selectedIssueIds.includes(issue.id);

                        return (
                          <tr
                            key={issue.id}
                            onClick={() => toggleSelectIssue(issue.id)}
                            className={`h-11 transition-colors cursor-pointer text-body-sm select-none ${
                              isSelected
                                ? "bg-primary-tint border-l-2 border-primary"
                                : "bg-card hover:bg-canvas"
                            }`}
                          >
                            {/* Checkbox */}
                            <td
                              className="py-2 px-3.5 text-center"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleSelectIssue(issue.id)}
                                className="h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary focus:ring-offset-0 cursor-pointer"
                              />
                            </td>

                            {/* Title & Culprit */}
                            <td className="py-2 px-3">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-text-primary truncate max-w-md">
                                  {issue.title}
                                </span>
                              </div>
                              <div className="font-mono text-[11px] text-text-muted truncate max-w-lg mt-0.5">
                                {issue.culprit}
                              </div>
                            </td>

                            {/* Environment */}
                            <td className="py-2 px-3">
                              <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-canvas border border-border text-text-secondary">
                                {issue.environment}
                              </span>
                            </td>

                            {/* Events Count (Mono tabular) */}
                            <td className="py-2 px-3 text-right font-mono text-[12px] tabular-nums font-semibold text-text-primary">
                              {issue.eventsCount.toLocaleString()}
                            </td>

                            {/* Users Affected (Mono tabular) */}
                            <td className="py-2 px-3 text-right font-mono text-[12px] tabular-nums text-text-secondary">
                              {issue.usersAffected.toLocaleString()}
                            </td>

                            {/* Commit SHA */}
                            <td className="py-2 px-3">
                              <span className="font-mono text-[11px] text-primary hover:underline">
                                {issue.commitSha}
                              </span>
                            </td>

                            {/* Last Seen */}
                            <td className="py-2 px-3 text-right font-mono text-[11px] text-text-muted">
                              {issue.lastSeen}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="p-3 border-t border-border bg-canvas flex items-center justify-between text-label-sm text-text-secondary">
                  <span>Showing {data.recentIssues.length} active issues</span>
                  <Link
                    href={`/${workspaceSlug}/issues`}
                    className="flex items-center gap-1 font-medium text-primary hover:underline"
                  >
                    <span>View all issues in triage</span>
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </div>
              </div>

              {/* 4. Project / Service Health List */}
              <div className="rounded-lg border border-border bg-card p-5 shadow-level-1">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h2 className="text-title-md font-semibold text-text-primary">
                      Monitored Services &amp; Cluster Health
                    </h2>
                    <p className="text-[12px] text-text-secondary">
                      Availability, error budget consumption, and p99 latency status.
                    </p>
                  </div>
                  <Button variant="secondary" size="sm" asChild>
                    <Link href="/onboarding/create-project">Add Service</Link>
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {data.services.map((svc) => (
                    <div
                      key={svc.id}
                      className="rounded-md border border-border bg-canvas p-3.5 flex items-center justify-between hover:border-border-hover transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`h-2.5 w-2.5 rounded-full ${
                            svc.status === "healthy" ? "bg-success" : "bg-warning"
                          }`}
                        />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-body-sm font-semibold text-text-primary">
                              {svc.name}
                            </span>
                            <span className="font-mono text-[10px] text-text-muted">
                              {svc.platform}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 font-mono text-[11px] text-text-secondary mt-0.5">
                            <span>Err: {svc.errorRate}</span>
                            <span>•</span>
                            <span>p99: {svc.p99Latency}</span>
                            <span>•</span>
                            <span>SLO: {svc.slo}</span>
                          </div>
                        </div>
                      </div>

                      <div>
                        {svc.activeIncidents > 0 ? (
                          <Badge variant="warning" showDot>
                            {svc.activeIncidents} Incident
                          </Badge>
                        ) : (
                          <Badge variant="success" showDot>
                            Optimal
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

