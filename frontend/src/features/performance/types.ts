export interface PerformanceFilterOptions {
  environments: string[];
  releases: string[];
  services: string[];
}

export interface PerformanceSummary {
  request_count: number;
  error_count: number;
  error_rate: number; // Percentage (e.g. 0.21 = 0.21%)
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
}

export interface TimeseriesPoint {
  t: string; // ISO 8601 UTC timestamp
  requests: number;
  error_rate: number | null; // null represents no-traffic intervals / gap
  p95_ms: number | null; // null represents no-traffic intervals / gap
}

export interface PerformanceTimeseries {
  interval_seconds: number;
  points: TimeseriesPoint[];
}

export interface EndpointMetricItem {
  route: string;
  method: string;
  requests: number;
  error_rate: number; // Percentage (e.g. 4.8 = 4.8%)
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
}

export interface PerformanceEndpointsResponse {
  items: EndpointMetricItem[];
  total: number;
  truncated: boolean;
}

export interface PerformanceQueryParams {
  from: string; // ISO 8601 UTC
  to: string; // ISO 8601 UTC
  environment?: string;
  release?: string;
  route?: string;
  method?: string;
  mockState?: "normal" | "empty" | "error" | "truncated";
}

export interface LatencyBucket {
  le_ms: number | null; // null represents the overflow bucket (> last boundary)
  count: number;
}

export interface ReleasePerformance {
  release: string;
  requests: number;
  error_rate: number;
  p95_ms: number;
}

export interface EndpointDetailResponse {
  summary: {
    request_count: number;
    error_rate: number;
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
  };
  latency_distribution: LatencyBucket[];
  status_counts: Record<string, number>;
  releases: ReleasePerformance[];
}
