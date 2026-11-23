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

export type CreateWebhookChannelMockPayload = {
  name: string;
  channel_type: "webhook";
  destination: string;
  enabled: boolean;
  auth:
    | null
    | { type: "bearer"; value: string }
    | { type: "header"; name: string; value: string };
};

export type MockWebhookChannel = Omit<CreateWebhookChannelMockPayload, "auth"> & {
  id: string;
  has_auth: boolean;
};

// TODO: Replace this mock with the real create call when webhook channels are supported.
export async function createWebhookChannelMock(payload: CreateWebhookChannelMockPayload) {
  const { auth, ...channel } = payload;
  const request = {
    ...channel,
    auth: auth && { ...auth, value: "[redacted]" },
  };
  console.log("Mock webhook channel request", request);

  await new Promise<void>((resolve) => setTimeout(resolve, 600));

  const response: MockWebhookChannel & { signing_secret: string } = {
    ...channel,
    id: crypto.randomUUID(),
    has_auth: auth !== null,
    signing_secret: "whsec_" + Array.from(
      crypto.getRandomValues(new Uint8Array(16)),
      (byte) => byte.toString(16).padStart(2, "0"),
    ).join(""),
  };
  return { request, response };
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
