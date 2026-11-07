import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listIssuesApi,
  getIssueDetailApi,
  updateIssueStatusApi,
  bulkUpdateIssueStatusApi,
} from "./api";
import { IssueFilterParams, IssueStatus } from "./types";

export function useIssuesList(
  workspaceSlug: string,
  filters: IssueFilterParams = {}
) {
  return useQuery({
    queryKey: ["issues-list", workspaceSlug, filters],
    queryFn: () => listIssuesApi(workspaceSlug, filters),
  });
}

export function useIssueDetail(workspaceSlug: string, issueId: string) {
  return useQuery({
    queryKey: ["issue-detail", workspaceSlug, issueId],
    queryFn: () => getIssueDetailApi(workspaceSlug, issueId),
    enabled: Boolean(issueId),
  });
}

export function useUpdateIssueStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      issueId,
      status,
    }: {
      issueId: string;
      status: IssueStatus;
    }) => updateIssueStatusApi(issueId, status),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["issues-list"] });
      queryClient.invalidateQueries({
        queryKey: ["issue-detail", variables.issueId],
      });
    },
  });
}

export function useBulkUpdateIssueStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      issueIds,
      status,
    }: {
      issueIds: string[];
      status: IssueStatus;
    }) => bulkUpdateIssueStatusApi(issueIds, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["issues-list"] });
    },
  });
}

