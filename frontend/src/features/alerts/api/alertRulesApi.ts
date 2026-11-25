import { apiClient } from "@/lib/api-client";
import {
  NotificationChannel,
  CreateNotificationChannelPayload,
  AlertRule,
  AlertRuleListResponse,
  CreateAlertRulePayload,
} from "../types";

/**
 * List notification channels for a project.
 */
export async function listChannels(
  projectId: string
): Promise<NotificationChannel[]> {
  return apiClient.get<NotificationChannel[]>(
    `/api/v1/projects/${projectId}/notification-channels`
  );
}

export async function testChannel(projectId: string, channelId: string): Promise<void> {
  return apiClient.post<void>(
    `/api/v1/projects/${projectId}/notification-channels/${channelId}/test`
  );
}

/**
 * Create a new notification channel for a project.
 */
export async function createChannel(
  projectId: string,
  payload: CreateNotificationChannelPayload
): Promise<NotificationChannel> {
  return apiClient.post<NotificationChannel>(
    `/api/v1/projects/${projectId}/notification-channels`,
    payload
  );
}

export type CreateWebhookChannelPayload = {
  name: string;
  channel_type: "webhook";
  destination: string;
  enabled: boolean;
  auth:
    | null
    | { type: "bearer"; value: string }
    | { type: "header"; name: string; value: string };
};

export async function createWebhookChannel(
  projectId: string,
  payload: CreateWebhookChannelPayload
): Promise<NotificationChannel & { signingSecret: string }> {
  return apiClient.post<NotificationChannel & { signingSecret: string }>(
    `/api/v1/projects/${projectId}/notification-channels`,
    payload
  );
}

export type UpdateWebhookChannelPayload = Omit<CreateWebhookChannelPayload, "auth"> & {
  auth?: CreateWebhookChannelPayload["auth"];
};

export function updateChannel(
  projectId: string,
  channelId: string,
  payload: CreateNotificationChannelPayload | UpdateWebhookChannelPayload,
): Promise<NotificationChannel> {
  return apiClient.patch(
    `/api/v1/projects/${projectId}/notification-channels/${channelId}`,
    payload,
  );
}

export function deleteChannel(projectId: string, channelId: string): Promise<void> {
  return apiClient.delete(`/api/v1/projects/${projectId}/notification-channels/${channelId}`);
}

/**
 * List alert rules for a project.
 */
export async function listAlertRules(
  projectId: string,
  cursor?: string
): Promise<AlertRuleListResponse> {
  const query = cursor ? `?${new URLSearchParams({ cursor })}` : "";
  return apiClient.get<AlertRuleListResponse>(
    `/api/v1/projects/${projectId}/alert-rules${query}`
  );
}

/**
 * Create an alert rule for a project.
 */
export async function createAlertRule(
  projectId: string,
  payload: CreateAlertRulePayload
): Promise<AlertRule> {
  return apiClient.post<AlertRule>(
    `/api/v1/projects/${projectId}/alert-rules`,
    payload
  );
}

/**
 * Toggle an alert rule's enabled status.
 */
export async function toggleAlertRule(
  projectId: string,
  id: string,
  enabled: boolean
): Promise<AlertRule> {
  return apiClient.patch<AlertRule>(
    `/api/v1/projects/${projectId}/alert-rules/${id}`,
    { enabled }
  );
}

/**
 * Delete an alert rule by id.
 */
export async function deleteAlertRule(
  projectId: string,
  id: string
): Promise<void> {
  return apiClient.delete<void>(
    `/api/v1/projects/${projectId}/alert-rules/${id}`
  );
}
