import { apiClient } from "@/lib/api-client";
import {
  NotificationChannel,
  CreateNotificationChannelPayload,
  AlertRule,
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

/**
 * List alert rules for a project.
 */
export async function listAlertRules(
  projectId: string
): Promise<AlertRule[]> {
  return apiClient.get<AlertRule[]>(
    `/api/v1/projects/${projectId}/alert-rules`
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
