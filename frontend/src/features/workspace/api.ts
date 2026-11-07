import { apiClient } from "@/lib/api-client";
import { WorkspaceDetail } from "./types";

export async function fetchCurrentWorkspaceApi(): Promise<WorkspaceDetail> {
  return apiClient.get<WorkspaceDetail>("/api/v1/workspaces/current");
}
