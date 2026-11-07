import { useMutation, useQuery } from "@tanstack/react-query";
import {
  listProjectsApi,
  createProjectApi,
  getSdkConfigApi,
  checkFirstEventStatusApi,
} from "./api";
import { CreateProjectFormData } from "./schemas";
import { useAuth } from "@/features/auth/auth-context";

export function useListProjects() {
  const { isAuthenticated, isReady } = useAuth();

  return useQuery({
    queryKey: ["projects"],
    queryFn: listProjectsApi,
    enabled: isReady && isAuthenticated,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useCreateProject() {
  return useMutation({
    mutationFn: (data: CreateProjectFormData) => createProjectApi(data),
  });
}

export function useSdkConfig() {
  return useQuery({
    queryKey: ["sdk-config"],
    queryFn: () => getSdkConfigApi(),
  });
}

export function useLiveEventStatus(projectId?: string) {
  return useQuery({
    queryKey: ["live-event-status", projectId],
    queryFn: () => checkFirstEventStatusApi(projectId),
    refetchInterval: 3000,
  });
}
