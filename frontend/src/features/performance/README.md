# Performance Feature Documentation & Switching to Real API

This module implements the **Performance Overview** screen according to the Stitch design prototype and the Faultline API contracts.

## Architecture

- **`types.ts`**: TypeScript definitions corresponding strictly to the backend contract shapes:
  - `PerformanceFilterOptions` (`GET /filters`)
  - `PerformanceSummary` (`GET /summary`)
  - `PerformanceTimeseries` (`GET /timeseries`)
  - `PerformanceEndpointsResponse` (`GET /endpoints`)
  - `EndpointDetailResponse` (`GET /endpoint?route=...&method=...`)
- **`api.ts`**: The single API module encapsulating the 5 API functions:
  - `getFilters(projectId)`
  - `getSummary(projectId, params)`
  - `getTimeseries(projectId, params)`
  - `getEndpoints(projectId, params)`
  - `getEndpointDetail(projectId, params)`
- **`hooks.ts`**: React Query hooks supporting parallel independent data loading and refetching.
- **`components/timeseries-chart.tsx`**: Reusable Recharts wrapper configured with `connectNulls={false}` for gap rendering, exact value tooltips, Stitch design tokens, and accessibility.
- **`components/kpi-cards-section.tsx`**: Renders KPI cards (Requests, Errors, Error rate, p50, p95, p99; supports `hideErrorsCount` for endpoint detail).
- **`components/endpoints-table-section.tsx`**: Searchable, client-side sortable, paginated table with route navigation to `/performance/endpoint?route={route}&method={method}` carrying over pinned time and filters.
- **`components/latency-histogram.tsx`**: Latency distribution histogram rendering cumulative boundaries and properly labeling the `le_ms: null` bucket as `>{last boundary}ms`.
- **`components/status-breakdown.tsx`**: Visualizes HTTP response codes by class (2xx, 3xx, 4xx, 5xx) with proportional segment bar and detailed list.
- **`components/release-comparison-table.tsx`**: Release comparison highlighting regressions (highest p95 and error rates) and explicitly noting that the release filter is bypassed.

## Backend API Integration

All 5 functions dispatch real network requests using `apiClient` with proper `Authorization: Bearer <token>` headers to:
- `GET /api/v1/projects/{project_id}/performance/filters`
- `GET /api/v1/projects/{project_id}/performance/summary`
- `GET /api/v1/projects/{project_id}/performance/timeseries`
- `GET /api/v1/projects/{project_id}/performance/endpoints`
- `GET /api/v1/projects/{project_id}/performance/endpoint-detail?route=...&method=...`
