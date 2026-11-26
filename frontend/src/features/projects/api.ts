import { apiClient, delay } from "@/lib/api-client";
import { CreateProjectFormData } from "./schemas";
import { Project, ProjectApiKeyResponse, LiveStatusEvent, ProjectUpdate } from "./types";

export async function listProjectsApi(): Promise<Project[]> {
  return apiClient.get<Project[]>("/api/v1/projects");
}

export async function createProjectApi(data: CreateProjectFormData): Promise<Project> {
  const payload: {
    name: string;
    slug: string;
    platform?: string;
    description?: string;
  } = {
    name: data.name,
    slug: data.slug,
    platform: data.platform || "fastapi",
  };

  if (data.description && data.description.trim()) {
    payload.description = data.description.trim();
  }

  return apiClient.post<Project>("/api/v1/projects", payload);
}

export async function updateProjectApi(projectId: string, data: ProjectUpdate): Promise<Project> {
  return apiClient.patch<Project>(`/api/v1/projects/${projectId}`, data);
}

export async function deleteProjectApi(projectId: string): Promise<void> {
  await apiClient.delete(`/api/v1/projects/${projectId}`);
}

export async function getProjectApiKeyApi(projectId: string): Promise<ProjectApiKeyResponse> {
  return apiClient.get<ProjectApiKeyResponse>(`/api/v1/projects/${projectId}/api-key`);
}

export async function rotateProjectApiKeyApi(projectId: string): Promise<ProjectApiKeyResponse> {
  return apiClient.post<ProjectApiKeyResponse>(`/api/v1/projects/${projectId}/api-key/rotate`);
}

export async function checkFirstEventStatusApi(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _projectId?: string
): Promise<LiveStatusEvent> {
  await delay(400);

  return {
    status: "waiting",
  };
}

export async function createReleaseKeyApi(projectId: string): Promise<{ token: string }> {
  return apiClient.post<{ token: string }>(`/api/v1/projects/${projectId}/release-keys`);
}
