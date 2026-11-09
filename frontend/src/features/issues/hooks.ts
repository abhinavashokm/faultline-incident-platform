import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listIssuesApi,
  getIssueDetailApi,
  updateIssueStatusApi,
  bulkUpdateIssueStatusApi,
} from "./api";
import { IssueFilterParams, IssueStatus } from "./types";

export function useIssuesList(
  projectId?: string,
  filters: IssueFilterParams = {}
) {
  return useQuery({
    queryKey: ["issues-list", projectId, filters],
    queryFn: () => listIssuesApi(projectId!, filters),
    enabled: Boolean(projectId),
  });
}

export function useIssueDetail(projectId?: string, issueId?: string) {
  return useQuery({
    queryKey: ["issue-detail", projectId, issueId],
    queryFn: () => getIssueDetailApi(projectId!, issueId!),
    enabled: Boolean(projectId && issueId),
  });
}

export function useUpdateIssueStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      issueId,
      status,
    }: {
      projectId: string;
      issueId: string;
      status: IssueStatus;
    }) => updateIssueStatusApi(projectId, issueId, status),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["issues-list", variables.projectId],
      });
      queryClient.invalidateQueries({
        queryKey: ["issue-detail", variables.projectId, variables.issueId],
      });
    },
  });
}

export function useBulkUpdateIssueStatus(projectId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      issueIds,
      status,
    }: {
      issueIds: string[];
      status: IssueStatus;
    }) => bulkUpdateIssueStatusApi(projectId!, issueIds, status),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["issues-list", projectId],
      });
    },
  });
}

