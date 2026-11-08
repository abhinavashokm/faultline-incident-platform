import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listProjectsApi,
  createProjectApi,
  getProjectApiKeyApi,
  checkFirstEventStatusApi,
} from "./api";
import { CreateProjectFormData } from "./schemas";
import { Project, ProjectApiKeyResponse } from "./types";
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

export function useProjectBySlug(slug: string) {
  const { isReady, isAuthenticated } = useAuth();
  const { data: projects, isLoading: isQueryLoading, isFetched, isError, error } = useListProjects();

  const project = useMemo(() => {
    if (!projects) return undefined;
    return projects.find((p) => p.slug === slug);
  }, [projects, slug]);

  // Loading is true while auth bootstrap is pending OR when projects are actively loading
  // OR when authenticated and the projects query hasn't finished fetching yet.
  const isLoading = !isReady || isQueryLoading || (isAuthenticated && !isFetched);

  // Strictly only not found if auth is settled, authenticated, projects query has fetched, and matching completed
  const isNotFound = isReady && isAuthenticated && isFetched && !isLoading && !project;

  return {
    project,
    isLoading,
    isNotFound,
    isArchived: project?.status === "archived",
    isError,
    error,
  };
}

export function useProjectApiKey(projectId?: string) {
  return useQuery({
    queryKey: ["project-api-key", projectId],
    queryFn: () => getProjectApiKeyApi(projectId!),
    enabled: Boolean(projectId),
    staleTime: 1000 * 60 * 5,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateProjectFormData) => createProjectApi(data),
    onSuccess: (newProject: Project) => {
      // 1. Seed ["projects"] query cache with the new project
      queryClient.setQueryData<Project[]>(["projects"], (old = []) => {
        const exists = old.some((p) => p.id === newProject.id || p.slug === newProject.slug);
        if (exists) {
          return old.map((p) => (p.id === newProject.id || p.slug === newProject.slug ? newProject : p));
        }
        return [...old, newProject];
      });

      // 2. If the response contains the dsn, pre-seed ["project-api-key", newProject.id]
      if (newProject.dsn && newProject.id) {
        queryClient.setQueryData<ProjectApiKeyResponse>(["project-api-key", newProject.id], {
          id: newProject.id,
          key_type: "ingest",
          dsn: newProject.dsn,
          last_used_at: null,
          created_at: newProject.created_at || newProject.createdAt || new Date().toISOString(),
        });
      }
    },
  });
}

export function useLiveEventStatus(projectId?: string) {
  return useQuery({
    queryKey: ["live-event-status", projectId],
    queryFn: () => checkFirstEventStatusApi(projectId),
    refetchInterval: 3000,
  });
}
