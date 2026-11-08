import { apiClient, delay } from "@/lib/api-client";
import { CreateProjectFormData } from "./schemas";
import { Project, SdkConfig, LiveStatusEvent } from "./types";
import { DEFAULT_SDK } from "./sdk-config";

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

export async function getSdkConfigApi(): Promise<SdkConfig> {
  return {
    name: DEFAULT_SDK.name,
    installCommand: DEFAULT_SDK.installCommand,
    initSnippet: DEFAULT_SDK.initSnippet,
    envSnippet: DEFAULT_SDK.envSnippet,
    dsn: "https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    apiKey: "fl_sec_9a82f1b4892cfa7eb40",
  };
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
