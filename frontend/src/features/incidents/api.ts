import { apiClient } from "@/lib/api-client";

export type IncidentSeverity = "low" | "medium" | "high" | "critical";

type CreateIncidentPayload = {
  title: string;
  severity: IncidentSeverity;
  description?: string;
  relatedIssueIds?: string[];
};

type CreatedIncident = {
  id: string;
  title: string;
  severity: string;
  status: string;
};

type IncidentListItem = CreatedIncident & {
  assigneeId: string | null;
  startedAt: string;
};

export function incidentsQueryKey(projectId: string | undefined) {
  return ["incidents", projectId] as const;
}

export function listIncidents(projectId: string) {
  return apiClient.get<IncidentListItem[]>(`/api/v1/projects/${projectId}/incidents`);
}

export function createIncident(projectId: string, payload: CreateIncidentPayload) {
  return apiClient.post<CreatedIncident>(`/api/v1/projects/${projectId}/incidents`, payload);
}

type IncidentDetail = IncidentListItem & {
  description: string | null;
  relatedIssues: {
    issueId: string;
    issueTitle: string | null;
    errorType: string | null;
    occurrenceCount: number | null;
  }[];
  timeline: {
    id: string;
    eventType: string;
    message: string;
    createdAt: string;
  }[];
};

export function getIncident(projectId: string, incidentId: string, signal: AbortSignal) {
  return apiClient.get<IncidentDetail>(
    `/api/v1/projects/${projectId}/incidents/${encodeURIComponent(incidentId)}`,
    { signal },
  );
}
