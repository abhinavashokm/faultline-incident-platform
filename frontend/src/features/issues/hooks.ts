import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
} from "@tanstack/react-query";
import {
  listIssuesApi,
  getIssueDetailApi,
  listIssueEventsApi,
  getEventDetailApi,
  updateIssueStatusApi,
  bulkUpdateIssueStatusApi,
} from "./api";
import { IssueFilterParams, IssueStatus, EventListResponse, EventDetail } from "./types";

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

export function useIssueEventsList(
  projectId?: string,
  issueId?: string,
  limit: number = 25
) {
  return useInfiniteQuery<EventListResponse>({
    queryKey: ["issue-events", projectId, issueId, limit],
    queryFn: ({ pageParam }) =>
      listIssueEventsApi(projectId!, issueId!, {
        limit,
        cursor: pageParam as string | undefined,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.meta.hasMore && lastPage.meta.nextCursor
        ? lastPage.meta.nextCursor
        : undefined,
    enabled: Boolean(projectId && issueId),
  });
}

export function useEventDetail(
  projectId?: string,
  issueId?: string,
  eventId?: string | null
) {
  return useQuery<EventDetail>({
    queryKey: ["event-detail", projectId, issueId, eventId],
    queryFn: () => getEventDetailApi(projectId!, issueId!, eventId!),
    enabled: Boolean(projectId && issueId && eventId),
    staleTime: 5 * 60 * 1000,
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

