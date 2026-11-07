import { delay } from "@/lib/api-client";
import { CreateProjectFormData } from "./schemas";
import { Project, SdkConfig, LiveStatusEvent } from "./types";
import { DEFAULT_SDK } from "./sdk-config";

export async function createProjectApi(data: CreateProjectFormData): Promise<Project> {
  await delay(600);

  return {
    id: "proj_" + Math.random().toString(36).substring(2, 10),
    name: data.name,
    slug: data.slug,
    environment: data.environment || "production",
    dsn: "https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    apiKey: "fl_sec_9a82f1b4892cfa7eb40",
    createdAt: new Date().toISOString(),
    eventCount: 0,
  };
}

export async function getSdkConfigApi(): Promise<SdkConfig> {
  await delay(200);

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
