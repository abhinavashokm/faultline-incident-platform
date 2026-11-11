# Performance Feature Documentation & Switching to Real API

This module implements the **Performance Overview** screen according to the Stitch design prototype and the Faultline API contracts.

## Architecture

- **`types.ts`**: TypeScript definitions corresponding strictly to the backend contract shapes:
  - `PerformanceFilterOptions` (`GET /filters`)
  - `PerformanceSummary` (`GET /summary`)
  - `PerformanceTimeseries` (`GET /timeseries`)
  - `PerformanceEndpointsResponse` (`GET /endpoints`)
- **`api.ts`**: The single API module encapsulating the 4 API functions:
  - `getFilters(projectId)`
  - `getSummary(projectId, params)`
  - `getTimeseries(projectId, params)`
  - `getEndpoints(projectId, params)`
- **`hooks.ts`**: React Query hooks supporting parallel independent data loading and refetching.
- **`components/timeseries-chart.tsx`**: Reusable Recharts wrapper configured with `connectNulls={false}` for gap rendering, exact value tooltips, Stitch design tokens, and accessibility.
- **`components/kpi-cards-section.tsx`**: Renders the 6 key performance indicator cards (Requests, Errors, Error rate, p50, p95, p99).
- **`components/endpoints-table-section.tsx`**: Searchable, client-side sortable, paginated table with route navigation to `/performance/endpoint?route={route}&method={method}`.

## Switching from Mocks to Real API

In [`frontend/src/features/performance/api.ts`](./api.ts):

Change line 17:
```typescript
export const USE_MOCKS = true;
```
to:
```typescript
export const USE_MOCKS = false;
```

All 4 functions will then dispatch real network requests using `apiClient` with proper `Authorization: Bearer <token>` headers to:
- `GET /api/v1/projects/{project_id}/performance/filters`
- `GET /api/v1/projects/{project_id}/performance/summary`
- `GET /api/v1/projects/{project_id}/performance/timeseries`
- `GET /api/v1/projects/{project_id}/performance/endpoints`
