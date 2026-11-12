"use client";

import React, { useState, useMemo, useCallback, useEffect, Suspense } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { useListProjects } from "@/features/projects/hooks";
import {
  usePerformanceFilters,
  usePerformanceTimeseries,
  usePerformanceEndpointDetail,
} from "@/features/performance/hooks";
import { PerformanceQueryParams } from "@/features/performance/types";
import { PerformanceFilterBar, PresetRange } from "@/features/performance/components/performance-filter-bar";
import { EndpointHeader } from "@/features/performance/components/endpoint-header";
import { KpiCardsSection } from "@/features/performance/components/kpi-cards-section";
import { TimeseriesChartsSection } from "@/features/performance/components/timeseries-charts-section";
import { LatencyHistogram } from "@/features/performance/components/latency-histogram";
import { StatusBreakdown } from "@/features/performance/components/status-breakdown";
import { ReleaseComparisonTable } from "@/features/performance/components/release-comparison-table";

function computePresetTimes(preset: PresetRange): { from: string; to: string } {
  const now = new Date();
  const to = now.toISOString();

  let diffHours = 24;
  if (preset === "1h") diffHours = 1;
  else if (preset === "6h") diffHours = 6;
  else if (preset === "24h") diffHours = 24;
  else if (preset === "7d") diffHours = 24 * 7;

  const fromDate = new Date(now.getTime() - diffHours * 60 * 60 * 1000);
  return { from: fromDate.toISOString(), to };
}

function EndpointDetailContent() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();

  const workspaceSlug = (params?.workspaceSlug as string) || "";
  const routeProjectSlug = (params?.projectSlug as string) || "";

  // Query parameters: route and method are REQUIRED
  const routeParam = searchParams?.get("route");
  const methodParam = searchParams?.get("method");

  // Read URL filters & carry-over state
  const initialPreset = (searchParams?.get("range") as PresetRange) || "24h";
  const initialEnv = searchParams?.get("environment") || "";
  const initialRel = searchParams?.get("release") || "";

  const [activePreset, setActivePreset] = useState<PresetRange>(initialPreset);
  const [environment, setEnvironment] = useState<string>(initialEnv);
  const [release, setRelease] = useState<string>(initialRel);

  // Pinned from/to timestamps
  const [pinnedTimes, setPinnedTimes] = useState<{ from: string; to: string }>(() => {
    const fromParam = searchParams?.get("from");
    const toParam = searchParams?.get("to");
    if (fromParam && toParam) {
      return { from: fromParam, to: toParam };
    }
    return computePresetTimes(initialPreset);
  });

  const [customFrom, setCustomFrom] = useState(pinnedTimes.from.slice(0, 16));
  const [customTo, setCustomTo] = useState(pinnedTimes.to.slice(0, 16));

  // Date range validation
  const rangeValidationError = useMemo(() => {
    const fromMs = new Date(customFrom).getTime();
    const toMs = new Date(customTo).getTime();

    if (isNaN(fromMs) || isNaN(toMs)) return "Invalid date format";
    if (fromMs >= toMs) return "Start time must be before end time";
    const diffDays = (toMs - fromMs) / (1000 * 60 * 60 * 24);
    if (diffDays > 7) return "Time range must not exceed 7 days";
    return null;
  }, [customFrom, customTo]);

  // Resolve project
  const { data: projects, isLoading: isProjectsLoading } = useListProjects();
  const currentProject = useMemo(() => {
    if (!projects || projects.length === 0) return null;
    if (routeProjectSlug) {
      return projects.find((p) => p.slug === routeProjectSlug) || null;
    }
    return projects[0];
  }, [projects, routeProjectSlug]);

  const projectId = currentProject?.id || "";

  // Back link URL preserving from/to/environment/release
  const overviewBackUrl = useMemo(() => {
    const p = new URLSearchParams();
    p.set("range", activePreset);
    p.set("from", pinnedTimes.from);
    p.set("to", pinnedTimes.to);
    if (environment) p.set("environment", environment);
    if (release) p.set("release", release);
    return `/${workspaceSlug}/${routeProjectSlug || currentProject?.slug || ""}/performance?${p.toString()}`;
  }, [workspaceSlug, routeProjectSlug, currentProject?.slug, activePreset, pinnedTimes, environment, release]);

  // Update URL search params
  const updateUrlParams = useCallback(
    (newParams: {
      range?: string;
      from?: string;
      to?: string;
      environment?: string;
      release?: string;
    }) => {
      const current = new URLSearchParams(searchParams?.toString() || "");
      if (newParams.range) current.set("range", newParams.range);
      if (newParams.from) current.set("from", newParams.from);
      if (newParams.to) current.set("to", newParams.to);

      if (newParams.environment) current.set("environment", newParams.environment);
      else if (newParams.environment === "") current.delete("environment");

      if (newParams.release) current.set("release", newParams.release);
      else if (newParams.release === "") current.delete("release");

      router.replace(`?${current.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleSelectPreset = (preset: PresetRange) => {
    setActivePreset(preset);
    if (preset !== "custom") {
      const times = computePresetTimes(preset);
      setPinnedTimes(times);
      setCustomFrom(times.from.slice(0, 16));
      setCustomTo(times.to.slice(0, 16));
      updateUrlParams({
        range: preset,
        from: times.from,
        to: times.to,
      });
    }
  };

  const handleApplyCustomRange = () => {
    if (rangeValidationError) return;
    const isoFrom = new Date(customFrom).toISOString();
    const isoTo = new Date(customTo).toISOString();
    setActivePreset("custom");
    setPinnedTimes({ from: isoFrom, to: isoTo });
    updateUrlParams({
      range: "custom",
      from: isoFrom,
      to: isoTo,
    });
  };

  const handleChangeEnvironment = (env: string) => {
    setEnvironment(env);
    updateUrlParams({ environment: env });
  };

  const handleChangeRelease = (rel: string) => {
    setRelease(rel);
    updateUrlParams({ release: rel });
  };

  // Build query params
  const queryParams: PerformanceQueryParams = useMemo(() => {
    return {
      from: pinnedTimes.from,
      to: pinnedTimes.to,
      environment: environment || undefined,
      release: release || undefined,
      route: routeParam || undefined,
      method: methodParam || undefined,
    };
  }, [pinnedTimes, environment, release, routeParam, methodParam]);

  // 1) Parallel Call: Filters
  const { data: filtersData } = usePerformanceFilters(projectId);

  // 2) Parallel Call: Timeseries scoped to route & method
  const {
    data: timeseriesData,
    isLoading: isTimeseriesLoading,
    error: timeseriesError,
    refetch: refetchTimeseries,
    isRefetching: isTimeseriesRefetching,
  } = usePerformanceTimeseries(projectId, queryParams, Boolean(projectId && routeParam && methodParam));

  // 3) Parallel Call: Endpoint Detail (summary, distribution, status_counts, releases)
  const {
    data: detailData,
    isLoading: isDetailLoading,
    error: detailError,
    refetch: refetchDetail,
    isRefetching: isDetailRefetching,
  } = usePerformanceEndpointDetail(projectId, queryParams, Boolean(projectId && routeParam && methodParam));

  // Redirect to endpoint list / overview page if no data exists for this endpoint
  const hasNoData =
    Boolean(detailError && (detailError as any)?.status === 404) ||
    (!isDetailLoading && detailData && detailData.summary.request_count === 0);

  useEffect(() => {
    if (hasNoData) {
      router.replace(overviewBackUrl);
    }
  }, [hasNoData, overviewBackUrl, router]);

  const handleRefresh = () => {
    refetchTimeseries();
    refetchDetail();
  };

  const isRefreshing = isTimeseriesRefetching || isDetailRefetching;

  if (hasNoData) {
    return (
      <div className="p-8 max-w-4xl mx-auto text-center space-y-4 animate-pulse">
        <div className="h-8 w-48 bg-surface-container rounded mx-auto" />
        <div className="h-4 w-72 bg-surface-container rounded mx-auto" />
      </div>
    );
  }

  // Validation: Missing route or method query parameter (real API would return 422)
  if (!routeParam || !methodParam) {
    return (
      <div className="p-8 max-w-2xl mx-auto my-12 bg-card rounded-2xl border border-error/40 text-center space-y-4 shadow-sm">
        <div className="w-12 h-12 mx-auto rounded-full bg-error-container/40 flex items-center justify-center text-error">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-text-primary">Missing Required Parameters (422)</h2>
        <p className="text-xs text-text-secondary max-w-md mx-auto">
          Both <code>route</code> and <code>method</code> must be provided as query parameters to view endpoint performance details.
        </p>
        <div className="pt-2">
          <Link
            href={overviewBackUrl}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-white text-xs font-semibold hover:bg-primary/90 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Performance Overview
          </Link>
        </div>
      </div>
    );
  }

  // 404 Project Not Found State
  if (!isProjectsLoading && !currentProject) {
    return (
      <div className="p-8 max-w-4xl mx-auto text-center space-y-4">
        <h2 className="text-xl font-bold text-text-primary">Project Not Found</h2>
        <p className="text-sm text-text-secondary">
          The requested project could not be found in this workspace.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-background">
      <div className="max-w-[1440px] mx-auto px-6 py-6 space-y-6">
        {/* Header with method badge, route, and back link */}
        <EndpointHeader
          method={methodParam}
          route={routeParam}
          overviewBackUrl={overviewBackUrl}
        />

        {/* Reused FilterBar */}
        <PerformanceFilterBar
          filters={filtersData}
          activePreset={activePreset}
          onSelectPreset={handleSelectPreset}
          environment={environment}
          onChangeEnvironment={handleChangeEnvironment}
          release={release}
          onChangeRelease={handleChangeRelease}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
          customFrom={customFrom}
          customTo={customTo}
          onChangeCustomFrom={setCustomFrom}
          onChangeCustomTo={setCustomTo}
          onApplyCustomRange={handleApplyCustomRange}
          rangeValidationError={rangeValidationError}
        />

        {/* 1. KPI Cards (Requests, Error rate, p50, p95, p99) */}
        <KpiCardsSection
          data={detailData?.summary}
          isLoading={isDetailLoading}
          error={detailError as Error}
          onRetry={refetchDetail}
          hideErrorsCount={true}
        />

        {/* 2. Synchronized Timeseries Charts (Scoped to route & method) */}
        <TimeseriesChartsSection
          data={timeseriesData}
          isLoading={isTimeseriesLoading}
          error={timeseriesError as Error}
          onRetry={refetchTimeseries}
        />

        {/* 3. Latency Distribution & Status Code Breakdown (2-Column Grid) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <LatencyHistogram
            distribution={detailData?.latency_distribution}
            isLoading={isDetailLoading}
            error={detailError as Error}
            totalSamples={detailData?.summary?.request_count}
          />

          <StatusBreakdown
            statusCounts={detailData?.status_counts}
            isLoading={isDetailLoading}
            error={detailError as Error}
          />
        </div>

        {/* 4. Release Comparison Table */}
        <ReleaseComparisonTable
          releases={detailData?.releases}
          isLoading={isDetailLoading}
          error={detailError as Error}
          activeReleaseFilter={release}
        />
      </div>
    </div>
  );
}

export default function EndpointDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 max-w-4xl mx-auto space-y-4 animate-pulse">
          <div className="h-4 w-40 bg-surface-container rounded" />
          <div className="h-8 w-64 bg-surface-container rounded" />
          <div className="h-14 w-full bg-surface-container rounded-xl" />
        </div>
      }
    >
      <EndpointDetailContent />
    </Suspense>
  );
}
