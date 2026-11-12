import { apiClient, delay, ApiError } from "@/lib/api-client";
import {
  PerformanceFilterOptions,
  PerformanceSummary,
  PerformanceTimeseries,
  PerformanceEndpointsResponse,
  PerformanceQueryParams,
  EndpointMetricItem,
  TimeseriesPoint,
  EndpointDetailResponse,
} from "./types";

/**
 * Flag to control mock vs real API calls for unimplemented endpoints.
 * Currently keeps endpoint detail mocked until real backend wiring is added.
 */
export const USE_MOCKS = true;

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

// ---------------------------------------------------------------------------
// Mock Generators
// ---------------------------------------------------------------------------

function checkMockErrorState(params?: PerformanceQueryParams) {
  if (params?.mockState === "error") {
    const error: any = new Error("Failed to load endpoint telemetry from cluster");
    error.status = 500;
    error.detail = "Failed to load endpoint telemetry from cluster: connection timeout";
    throw error;
  }
}

function generateMockSummary(params: PerformanceQueryParams): PerformanceSummary {
  if (params.mockState === "empty") {
    return {
      request_count: 0,
      error_count: 0,
      error_rate: 0,
      p50_ms: 0,
      p95_ms: 0,
      p99_ms: 0,
    };
  }

  // Vary values predictably based on filters
  let multiplier = 1.0;
  if (params.environment === "staging") multiplier *= 0.2;
  if (params.release === "v1.7.2") multiplier *= 0.8;

  const totalReq = Math.round(58240 * multiplier);
  const errorCount = Math.round(145 * multiplier);
  const errorRate = totalReq > 0 ? Number(((errorCount / totalReq) * 100).toFixed(2)) : 0;

  return {
    request_count: totalReq,
    error_count: errorCount,
    error_rate: errorRate,
    p50_ms: Math.round(42 * (params.environment === "staging" ? 1.2 : 1)),
    p95_ms: Math.round(315 * (params.environment === "staging" ? 1.4 : 1)),
    p99_ms: Math.round(820 * (params.environment === "staging" ? 1.6 : 1)),
  };
}

function generateMockTimeseries(params: PerformanceQueryParams): PerformanceTimeseries {
  if (params.mockState === "empty") {
    return {
      interval_seconds: getRecommendedIntervalSeconds(params.from, params.to),
      points: [],
    };
  }

  const intervalSeconds = getRecommendedIntervalSeconds(params.from, params.to);
  const fromMs = new Date(params.from).getTime();
  const toMs = new Date(params.to).getTime();
  const stepMs = intervalSeconds * 1000;

  const points: TimeseriesPoint[] = [];
  let currentMs = fromMs;
  let index = 0;

  // Max ~150 points for clean rendering if interval calculation is coarse
  while (currentMs < toMs) {
    const isoString = new Date(currentMs).toISOString();

    // Inject deliberate gaps (no traffic) every 14th interval
    const isGap = index > 0 && index % 14 === 0;

    if (isGap) {
      points.push({
        t: isoString,
        requests: 0,
        error_rate: null,
        p95_ms: null,
      });
    } else {
      const baseReq = 350 + Math.sin(index / 3) * 180 + (index % 5) * 30;
      const envFactor = params.environment === "staging" ? 0.3 : 1;
      const requests = Math.max(10, Math.round(baseReq * envFactor));

      const errorRate = Number((0.8 + Math.cos(index / 2) * 0.7 + (index % 7 === 0 ? 1.5 : 0)).toFixed(2));
      const p95 = Math.round(260 + Math.sin(index / 4) * 80 + (index % 6 === 0 ? 120 : 0));

      points.push({
        t: isoString,
        requests,
        error_rate: Math.max(0, errorRate),
        p95_ms: Math.max(50, p95),
      });
    }

    currentMs += stepMs;
    index++;
  }

  return {
    interval_seconds: intervalSeconds,
    points,
  };
}

const SAMPLE_ROUTES = [
  { route: "/api/v1/payments/charge", method: "POST", baseReq: 18400, baseErr: 3.82, p50: 62, p95: 412, p99: 1120 },
  { route: "/api/v1/checkout/session", method: "POST", baseReq: 12100, baseErr: 1.15, p50: 45, p95: 310, p99: 780 },
  { route: "/api/v1/tokens/verify", method: "POST", baseReq: 5600, baseErr: 0.42, p50: 24, p95: 180, p99: 420 },
  { route: "/api/v1/customers/{id}", method: "GET", baseReq: 3900, baseErr: 0.08, p50: 18, p95: 145, p99: 320 },
  { route: "/api/v1/webhooks/stripe", method: "POST", baseReq: 1800, baseErr: 0.12, p50: 32, p95: 135, p99: 290 },
  { route: "/api/v1/invoices/generate", method: "PUT", baseReq: 980, baseErr: 1.04, p50: 88, p95: 120, p99: 450 },
  { route: "/api/v1/projects/{id}/summary", method: "GET", baseReq: 4200, baseErr: 0.18, p50: 35, p95: 110, p99: 240 },
  { route: "/api/v1/auth/refresh", method: "POST", baseReq: 8500, baseErr: 0.05, p50: 22, p95: 95, p99: 210 },
  { route: "/api/v1/users/profile", method: "GET", baseReq: 6100, baseErr: 0.02, p50: 15, p95: 85, p99: 170 },
  { route: "/api/v1/subscriptions/{id}", method: "DELETE", baseReq: 420, baseErr: 2.14, p50: 55, p95: 230, p99: 610 },
  { route: "/api/v1/transfers/batch", method: "POST", baseReq: 310, baseErr: 4.52, p50: 140, p95: 890, p99: 2400 },
  { route: "/api/v1/reports/export", method: "GET", baseReq: 150, baseErr: 1.25, p50: 210, p95: 1200, p99: 3400 },
];

function generateMockEndpoints(params: PerformanceQueryParams): PerformanceEndpointsResponse {
  if (params.mockState === "empty") {
    return {
      items: [],
      total: 0,
      truncated: false,
    };
  }

  const isTruncatedTest = params.mockState === "truncated";
  const count = isTruncatedTest ? 620 : 137;
  const items: EndpointMetricItem[] = [];

  const multiplier = params.environment === "staging" ? 0.35 : 1;

  for (let i = 0; i < count; i++) {
    const base = SAMPLE_ROUTES[i % SAMPLE_ROUTES.length];
    const suffix = i >= SAMPLE_ROUTES.length ? `/${Math.floor(i / SAMPLE_ROUTES.length)}` : "";
    const route = `${base.route}${suffix}`;

    items.push({
      route,
      method: base.method,
      requests: Math.max(10, Math.round((base.baseReq + (i * 17) % 500) * multiplier)),
      error_rate: Number((base.baseErr + ((i % 10) * 0.1)).toFixed(2)),
      p50_ms: Math.round(base.p50 + (i % 7) * 2),
      p95_ms: Math.round(base.p95 + (i % 11) * 8),
      p99_ms: Math.round(base.p99 + (i % 13) * 20),
    });
  }

  // Server contract: Already sorted by p95 desc and capped at 500
  items.sort((a, b) => b.p95_ms - a.p95_ms);

  const cappedItems = items.slice(0, 500);

  return {
    items: cappedItems,
    total: count,
    truncated: count > 500,
  };
}

// ---------------------------------------------------------------------------
// 4 Exposed API Functions
// ---------------------------------------------------------------------------

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
 * We catch 404 and return zeroed/empty summary with isNoTelemetry flag so the UI can render
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

function generateMockEndpointDetail(params: PerformanceQueryParams): EndpointDetailResponse {
  if (params.mockState === "empty") {
    return {
      summary: {
        request_count: 0,
        error_rate: 0,
        p50_ms: 0,
        p95_ms: 0,
        p99_ms: 0,
      },
      latency_distribution: [
        { le_ms: 50, count: 0 },
        { le_ms: 100, count: 0 },
        { le_ms: 250, count: 0 },
        { le_ms: 500, count: 0 },
        { le_ms: 1000, count: 0 },
        { le_ms: null, count: 0 },
      ],
      status_counts: {},
      releases: [],
    };
  }

  let multiplier = 1.0;
  if (params.environment === "staging") multiplier *= 0.3;
  if (params.release === "v1.7.2") multiplier *= 0.7;

  const totalReq = Math.round(14200 * multiplier);
  const errorRate = params.release === "v1.8.0" ? 4.82 : 1.84;
  const p50 = Math.round(62 * (params.environment === "staging" ? 1.1 : 1));
  const p95 = Math.round((params.release === "v1.8.0" ? 510 : 380) * (params.environment === "staging" ? 1.2 : 1));
  const p99 = Math.round(p95 * 2.4);

  // Status counts based on errorRate
  const errorCount = Math.round(totalReq * (errorRate / 100));
  const successCount = totalReq - errorCount;
  const c500 = Math.round(errorCount * 0.7);
  const c400 = Math.round(errorCount * 0.2);
  const c422 = errorCount - c500 - c400;

  return {
    summary: {
      request_count: totalReq,
      error_rate: errorRate,
      p50_ms: p50,
      p95_ms: p95,
      p99_ms: p99,
    },
    latency_distribution: [
      { le_ms: 50, count: Math.round(totalReq * 0.408) },
      { le_ms: 100, count: Math.round(totalReq * 0.324) },
      { le_ms: 250, count: Math.round(totalReq * 0.148) },
      { le_ms: 500, count: Math.round(totalReq * 0.077) },
      { le_ms: 1000, count: Math.round(totalReq * 0.030) },
      { le_ms: null, count: Math.round(totalReq * 0.013) },
    ],
    status_counts: {
      "200": successCount,
      "500": c500,
      "400": c400,
      "422": Math.max(0, c422),
    },
    // The "releases" list IGNORES the release filter
    releases: [
      { release: "v1.8.0", requests: 6800000, error_rate: 4.82, p95_ms: 510 },
      { release: "v1.7.2", requests: 5400000, error_rate: 1.84, p95_ms: 290 },
      { release: "v1.7.1", requests: 1600000, error_rate: 1.72, p95_ms: 280 },
      { release: "v1.7.0", requests: 400000, error_rate: 1.65, p95_ms: 275 },
    ],
  };
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
 * 5) GET /endpoint?route=/payments&method=POST&from&to&environment&release -> endpoint detail
 */
export async function getEndpointDetail(
  projectId: string,
  params: PerformanceQueryParams
): Promise<EndpointDetailResponse> {
  if (USE_MOCKS) {
    await delay(400);
    checkMockErrorState(params);
    return generateMockEndpointDetail(params);
  }

  const queryParams: Record<string, string | undefined> = {
    route: params.route,
    method: params.method,
    from: params.from,
    to: params.to,
    environment: params.environment,
    release: params.release,
  };

  return apiClient.get<EndpointDetailResponse>(
    `/api/v1/projects/${projectId}/performance/endpoint`,
    { params: queryParams, transformCase: false }
  );
}
