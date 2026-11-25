import { apiClient } from "@/lib/api-client";

export type IncidentSeverity = "low" | "medium" | "high" | "critical";

type CreateIncidentPayload = {
  title: string;
  severity: IncidentSeverity;
  description?: string;
};

type CreatedIncident = {
  id: string;
  title: string;
  severity: string;
  status: string;
};

export function createIncident(projectId: string, payload: CreateIncidentPayload) {
  return apiClient.post<CreatedIncident>(`/api/v1/projects/${projectId}/incidents`, payload);
}
