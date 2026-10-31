import { useMutation, useQuery } from "@tanstack/react-query";
import {
  createProjectApi,
  getSdkConfigApi,
  checkFirstEventStatusApi,
} from "./api";
import { CreateProjectFormData } from "./schemas";
import { PlatformId } from "./types";

export function useCreateProject() {
  return useMutation({
    mutationFn: (data: CreateProjectFormData) => createProjectApi(data),
  });
}

export function useSdkConfig(platform: PlatformId) {
  return useQuery({
    queryKey: ["sdk-config", platform],
    queryFn: () => getSdkConfigApi(platform),
  });
}

export function useLiveEventStatus(projectId?: string) {
  return useQuery({
    queryKey: ["live-event-status", projectId],
    queryFn: () => checkFirstEventStatusApi(projectId),
    refetchInterval: 3000,
  });
}

