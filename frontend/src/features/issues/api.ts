import { apiClient } from "@/lib/api-client";
import {
  EventDetail,
  EventListResponse,
  IssueDetail,
  IssueListResponse,
  IssueFilterParams,
  IssueStatus,
} from "./types";

export async function listIssuesApi(
  projectId: string,
  filters: IssueFilterParams = {}
): Promise<IssueListResponse> {
  const params: Record<string, string | number | undefined> = {};

  if (filters.status) {
    params.status = filters.status;
  }
  if (filters.limit) {
    params.limit = filters.limit;
  }
  if (filters.cursor) {
    params.cursor = filters.cursor;
  }

  return apiClient.get<IssueListResponse>(`/api/v1/projects/${projectId}/issues`, {
    params,
  });
}

export async function getIssueDetailApi(
  projectId: string,
  issueId: string
): Promise<IssueDetail> {
  return apiClient.get<IssueDetail>(`/api/v1/projects/${projectId}/issues/${issueId}`);
}

export async function listIssueEventsApi(
  projectId: string,
  issueId: string,
  options: { limit?: number; cursor?: string } = {}
): Promise<EventListResponse> {
  const params: Record<string, string | number | undefined> = {};
  if (options.limit) {
    params.limit = options.limit;
  }
  if (options.cursor) {
    params.cursor = options.cursor;
  }

  return apiClient.get<EventListResponse>(
    `/api/v1/projects/${projectId}/issues/${issueId}/events`,
    { params }
  );
}

export async function getEventDetailApi(
  projectId: string,
  issueId: string,
  eventId: string
): Promise<EventDetail> {
  return apiClient.get<EventDetail>(
    `/api/v1/projects/${projectId}/issues/${issueId}/events/${eventId}`
  );
}

export async function updateIssueStatusApi(
  projectId: string,
  issueId: string,
  status: IssueStatus
): Promise<IssueDetail> {
  return apiClient.patch<IssueDetail>(
    `/api/v1/projects/${projectId}/issues/${issueId}`,
    { status }
  );
}

export async function bulkUpdateIssueStatusApi(
  projectId: string,
  issueIds: string[],
  status: IssueStatus
): Promise<{ success: boolean; updatedCount: number }> {
  await Promise.all(
    issueIds.map((id) =>
      apiClient.patch(`/api/v1/projects/${projectId}/issues/${id}`, { status })
    )
  );

  return { success: true, updatedCount: issueIds.length };
}
