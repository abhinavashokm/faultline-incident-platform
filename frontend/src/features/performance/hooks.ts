"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getFilters,
  getSummary,
  getTimeseries,
  getEndpoints,
} from "./api";
import { PerformanceQueryParams } from "./types";

export const performanceQueryKeys = {
  all: ["performance"] as const,
  filters: (projectId: string) => [...performanceQueryKeys.all, "filters", projectId] as const,
  summary: (projectId: string, params: PerformanceQueryParams) =>
    [...performanceQueryKeys.all, "summary", projectId, params] as const,
  timeseries: (projectId: string, params: PerformanceQueryParams) =>
    [...performanceQueryKeys.all, "timeseries", projectId, params] as const,
  endpoints: (projectId: string, params: PerformanceQueryParams) =>
    [...performanceQueryKeys.all, "endpoints", projectId, params] as const,
};

export function usePerformanceFilters(projectId: string) {
  return useQuery({
    queryKey: performanceQueryKeys.filters(projectId),
    queryFn: () => getFilters(projectId),
    enabled: Boolean(projectId),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePerformanceSummary(
  projectId: string,
  params: PerformanceQueryParams,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: performanceQueryKeys.summary(projectId, params),
    queryFn: () => getSummary(projectId, params),
    enabled: Boolean(projectId) && enabled,
    staleTime: 30 * 1000,
  });
}

export function usePerformanceTimeseries(
  projectId: string,
  params: PerformanceQueryParams,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: performanceQueryKeys.timeseries(projectId, params),
    queryFn: () => getTimeseries(projectId, params),
    enabled: Boolean(projectId) && enabled,
    staleTime: 30 * 1000,
  });
}

export function usePerformanceEndpoints(
  projectId: string,
  params: PerformanceQueryParams,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: performanceQueryKeys.endpoints(projectId, params),
    queryFn: () => getEndpoints(projectId, params),
    enabled: Boolean(projectId) && enabled,
    staleTime: 30 * 1000,
  });
}
