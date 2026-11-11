"use client";

import React, { useState, useMemo, useCallback, Suspense } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useListProjects } from "@/features/projects/hooks";
import {
  usePerformanceFilters,
  usePerformanceSummary,
  usePerformanceTimeseries,
  usePerformanceEndpoints,
} from "@/features/performance/hooks";
import { PerformanceQueryParams } from "@/features/performance/types";
import { PerformanceFilterBar, PresetRange } from "@/features/performance/components/performance-filter-bar";
import { KpiCardsSection } from "@/features/performance/components/kpi-cards-section";
import { TimeseriesChartsSection } from "@/features/performance/components/timeseries-charts-section";
import { EndpointsTableSection } from "@/features/performance/components/endpoints-table-section";

// Helper to compute pinned ISO 8601 UTC times for presets
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

function PerformanceOverviewContent() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();

  const workspaceSlug = (params?.workspaceSlug as string) || "";
  const routeProjectSlug = (params?.projectSlug as string) || "";

  // Resolve active project ID from list
  const { data: projects, isLoading: isProjectsLoading } = useListProjects();
  const currentProject = useMemo(() => {
    if (!projects || projects.length === 0) return null;
    if (routeProjectSlug) {
      return projects.find((p) => p.slug === routeProjectSlug) || null;
    }
    return projects[0];
  }, [projects, routeProjectSlug]);

  const projectId = currentProject?.id || "";

  // Read URL search params
  const initialPreset = (searchParams?.get("range") as PresetRange) || "24h";
  const initialEnv = searchParams?.get("environment") || "";
  const initialRel = searchParams?.get("release") || "";
  const initialMockState = (searchParams?.get("mockState") as any) || "normal";

  const [activePreset, setActivePreset] = useState<PresetRange>(initialPreset);
  const [environment, setEnvironment] = useState<string>(initialEnv);
  const [release, setRelease] = useState<string>(initialRel);
  const [mockState, setMockState] = useState<"normal" | "empty" | "error" | "truncated">(initialMockState);

  // Pinned from/to timestamps (computed once on user selection)
  const [pinnedTimes, setPinnedTimes] = useState<{ from: string; to: string }>(() => {
    const fromParam = searchParams?.get("from");
    const toParam = searchParams?.get("to");
    if (fromParam && toParam) {
      return { from: fromParam, to: toParam };
    }
    return computePresetTimes(initialPreset);
  });

  // Custom range input fields
  const [customFrom, setCustomFrom] = useState(
    pinnedTimes.from.slice(0, 16)
  );
  const [customTo, setCustomTo] = useState(
    pinnedTimes.to.slice(0, 16)
  );

  // Validate custom date range (from < to, max 7 days)
  const rangeValidationError = useMemo(() => {
    const fromMs = new Date(customFrom).getTime();
    const toMs = new Date(customTo).getTime();

    if (isNaN(fromMs) || isNaN(toMs)) return "Invalid date format";
    if (fromMs >= toMs) return "Start time must be before end time";
    const diffDays = (toMs - fromMs) / (1000 * 60 * 60 * 24);
    if (diffDays > 7) return "Time range must not exceed 7 days";
    return null;
  }, [customFrom, customTo]);

  // Update query params in URL
  const updateUrlParams = useCallback(
    (newParams: {
      range?: string;
      from?: string;
      to?: string;
      environment?: string;
      release?: string;
      mockState?: string;
    }) => {
      const current = new URLSearchParams(searchParams?.toString() || "");
      if (newParams.range) current.set("range", newParams.range);
      if (newParams.from) current.set("from", newParams.from);
      if (newParams.to) current.set("to", newParams.to);

      if (newParams.environment) current.set("environment", newParams.environment);
      else if (newParams.environment === "") current.delete("environment");

      if (newParams.release) current.set("release", newParams.release);
      else if (newParams.release === "") current.delete("release");

      if (newParams.mockState && newParams.mockState !== "normal") {
        current.set("mockState", newParams.mockState);
      } else {
        current.delete("mockState");
      }

      router.replace(`?${current.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  // Handle Preset selection
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

  // Handle Custom Range application
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

  const handleChangeMockState = (state: "normal" | "empty" | "error" | "truncated") => {
    setMockState(state);
    updateUrlParams({ mockState: state });
  };

  // Common query params for parallel calls
  const queryParams: PerformanceQueryParams = useMemo(() => {
    return {
      from: pinnedTimes.from,
      to: pinnedTimes.to,
      environment: environment || undefined,
      release: release || undefined,
      mockState: mockState,
    };
  }, [pinnedTimes, environment, release, mockState]);

  // 1) Parallel independent call: Filters
  const { data: filtersData } = usePerformanceFilters(projectId);

  // 2) Parallel independent call: Summary
  const {
    data: summaryData,
    isLoading: isSummaryLoading,
    error: summaryError,
    refetch: refetchSummary,
    isRefetching: isSummaryRefetching,
  } = usePerformanceSummary(projectId, queryParams, Boolean(projectId));

  // 3) Parallel independent call: Timeseries
  const {
    data: timeseriesData,
    isLoading: isTimeseriesLoading,
    error: timeseriesError,
    refetch: refetchTimeseries,
    isRefetching: isTimeseriesRefetching,
  } = usePerformanceTimeseries(projectId, queryParams, Boolean(projectId));

  // 4) Parallel independent call: Endpoints
  const {
    data: endpointsData,
    isLoading: isEndpointsLoading,
    error: endpointsError,
    refetch: refetchEndpoints,
    isRefetching: isEndpointsRefetching,
  } = usePerformanceEndpoints(projectId, queryParams, Boolean(projectId));

  // Refresh all parallel queries
  const handleRefresh = () => {
    refetchSummary();
    refetchTimeseries();
    refetchEndpoints();
  };

  const isRefreshing =
    isSummaryRefetching || isTimeseriesRefetching || isEndpointsRefetching;

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
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Performance
          </h1>
          <p className="text-sm text-text-secondary">
            Endpoint latency and error rates for {currentProject?.name || "your project"}
          </p>
        </div>

        {/* Global Filter Bar */}
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
          mockState={mockState}
          onChangeMockState={handleChangeMockState}
          customFrom={customFrom}
          customTo={customTo}
          onChangeCustomFrom={setCustomFrom}
          onChangeCustomTo={setCustomTo}
          onApplyCustomRange={handleApplyCustomRange}
          rangeValidationError={rangeValidationError}
        />

        {/* Section 1: KPI Summary Cards */}
        <KpiCardsSection
          data={summaryData}
          isLoading={isSummaryLoading}
          error={summaryError as Error}
          onRetry={refetchSummary}
        />

        {/* Section 2: Timeseries Charts */}
        <TimeseriesChartsSection
          data={timeseriesData}
          isLoading={isTimeseriesLoading}
          error={timeseriesError as Error}
          onRetry={refetchTimeseries}
        />

        {/* Section 3: Endpoints Table */}
        <EndpointsTableSection
          data={endpointsData}
          isLoading={isEndpointsLoading}
          error={endpointsError as Error}
          onRetry={refetchEndpoints}
          workspaceSlug={workspaceSlug}
          projectSlug={routeProjectSlug || currentProject?.slug || ""}
        />
      </div>
    </div>
  );
}

export default function PerformanceOverviewPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 max-w-4xl mx-auto space-y-4 animate-pulse">
          <div className="h-8 w-48 bg-surface-container rounded" />
          <div className="h-4 w-72 bg-surface-container rounded" />
          <div className="h-16 w-full bg-surface-container rounded-xl" />
        </div>
      }
    >
      <PerformanceOverviewContent />
    </Suspense>
  );
}
