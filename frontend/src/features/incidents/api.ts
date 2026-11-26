import type { IncidentStatus } from "@/features/incidents/status";
import { apiClient } from "@/lib/api-client";

type CreateIncidentPayload = {
  title: string;
  severity: string;
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
  resolvedAt: string | null;
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

export function deleteIncident(projectId: string, incidentId: string) {
  return apiClient.delete(`/api/v1/projects/${projectId}/incidents/${encodeURIComponent(incidentId)}`);
}

type UpdateIncidentDetailsPayload = {
  title: string;
  severity: string;
  description: string | null;
  relatedIssueIds: string[];
};

export function updateIncidentDetails(
  projectId: string,
  incidentId: string,
  payload: UpdateIncidentDetailsPayload,
) {
  return apiClient.patch<CreatedIncident>(
    `/api/v1/projects/${projectId}/incidents/${encodeURIComponent(incidentId)}/details`,
    payload,
  );
}

export function updateIncidentStatus(incidentId: string, status: IncidentStatus, note?: string) {
  return apiClient.post<{ id: string; status: IncidentStatus; resolvedAt: string | null }>(
    `/api/v1/incidents/${encodeURIComponent(incidentId)}/status`,
    { status, note },
  );
}
