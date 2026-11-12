import { apiClient, ApiError } from "@/lib/api-client";
import {
  PerformanceFilterOptions,
  PerformanceSummary,
  PerformanceTimeseries,
  PerformanceEndpointsResponse,
  PerformanceQueryParams,
  EndpointDetailResponse,
} from "./types";

// Helper to calculate interval seconds from from/to difference in milliseconds
export function getRecommendedIntervalSeconds(fromIso: string, toIso: string): number {
  const fromMs = new Date(fromIso).getTime();
  const toMs = new Date(toIso).getTime();
  const diffHours = Math.max(0, (toMs - fromMs) / (1000 * 60 * 60));

  if (diffHours <= 2) return 60; // <= 2h -> 60s
  if (diffHours <= 12) return 300; // <= 12h -> 300s (5m)
  if (diffHours <= 48) return 900; // <= 2d -> 900s (15m)
  return 3600; // > 2d -> 3600s (1h)
}

/**
 * 1) GET /filters -> filter dropdowns (environment, release, services)
 */
export async function getFilters(projectId: string): Promise<PerformanceFilterOptions> {
  return apiClient.get<PerformanceFilterOptions>(
    `/api/v1/projects/${projectId}/performance/filters`,
    { transformCase: false }
  );
}

/**
 * 2) GET /summary?from&to&environment&release -> KPI cards
 * Note: If project has no recorded telemetry in the workspace, processing service returns 404.
 * We catch 404 and return zeroed/empty summary with is_empty_telemetry flag so the UI can render
 * an empty warning state rather than a network error.
 */
export async function getSummary(
  projectId: string,
  params: PerformanceQueryParams
): Promise<PerformanceSummary> {
  const queryParams: Record<string, string | undefined> = {
    from: params.from,
    to: params.to,
    environment: params.environment || undefined,
    release: params.release || undefined,
  };

  try {
    return await apiClient.get<PerformanceSummary>(
      `/api/v1/projects/${projectId}/performance/summary`,
      { params: queryParams, transformCase: false }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return {
        request_count: 0,
        error_count: 0,
        error_rate: 0,
        p50_ms: 0,
        p95_ms: 0,
        p99_ms: 0,
        is_empty_telemetry: true,
      };
    }
    throw err;
  }
}

/**
 * 3) GET /timeseries?from&to&environment&release&route&method -> 3 charts from the same response
 * Returns empty points array if project has no telemetry in workspace (404).
 */
export async function getTimeseries(
  projectId: string,
  params: PerformanceQueryParams
): Promise<PerformanceTimeseries> {
  const queryParams: Record<string, string | undefined> = {
    from: params.from,
    to: params.to,
    environment: params.environment || undefined,
    release: params.release || undefined,
    route: params.route || undefined,
    method: params.method || undefined,
  };

  try {
    return await apiClient.get<PerformanceTimeseries>(
      `/api/v1/projects/${projectId}/performance/timeseries`,
      { params: queryParams, transformCase: false }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return {
        interval_seconds: getRecommendedIntervalSeconds(params.from, params.to),
        points: [],
      };
    }
    throw err;
  }
}

/**
 * 4) GET /endpoints?from&to&environment&release -> endpoints table
 * Returns empty items list if project has no telemetry in workspace (404).
 */
export async function getEndpoints(
  projectId: string,
  params: PerformanceQueryParams
): Promise<PerformanceEndpointsResponse> {
  const queryParams: Record<string, string | undefined> = {
    from: params.from,
    to: params.to,
    environment: params.environment || undefined,
    release: params.release || undefined,
  };

  try {
    return await apiClient.get<PerformanceEndpointsResponse>(
      `/api/v1/projects/${projectId}/performance/endpoints`,
      { params: queryParams, transformCase: false }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return {
        items: [],
        total: 0,
        truncated: false,
      };
    }
    throw err;
  }
}

/**
 * 5) GET /endpoint-detail?route=...&method=...&from=...&to=...&environment=...&release=... -> endpoint detail
 */
export async function getEndpointDetail(
  projectId: string,
  params: PerformanceQueryParams
): Promise<EndpointDetailResponse> {
  const queryParams: Record<string, string | undefined> = {
    route: params.route,
    method: params.method,
    from: params.from,
    to: params.to,
    environment: params.environment || undefined,
    release: params.release || undefined,
  };

  return apiClient.get<EndpointDetailResponse>(
    `/api/v1/projects/${projectId}/performance/endpoint-detail`,
    { params: queryParams, transformCase: false }
  );
}
