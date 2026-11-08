import { apiClient, delay } from "@/lib/api-client";
import { CreateProjectFormData } from "./schemas";
import { Project, ProjectApiKeyResponse, LiveStatusEvent } from "./types";

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

export async function getProjectApiKeyApi(projectId: string): Promise<ProjectApiKeyResponse> {
  return apiClient.get<ProjectApiKeyResponse>(`/api/v1/projects/${projectId}/api-key`);
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
