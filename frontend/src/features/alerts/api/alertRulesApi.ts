import { apiClient } from "@/lib/api-client";
import {
  NotificationChannel,
  CreateNotificationChannelPayload,
  AlertRule,
  CreateAlertRulePayload,
} from "../types";

/**
 * Flags to easily simulate edge cases / tests:
 * - MOCK_EMPTY_CHANNELS: set to true to test the empty state ("Add a notification channel first").
 * - MOCK_EMPTY_RULES: set to true to test the empty state ("No alert rules yet").
 * - SIMULATE_SUBMIT_FAILURE: set to true to test the submission failure error state.
 * - SIMULATE_LOAD_RULES_FAILURE: set to true to test rule list load error state.
 */
export const MOCK_CONFIG = {
  MOCK_EMPTY_CHANNELS: false,
  MOCK_EMPTY_RULES: false,
  SIMULATE_SUBMIT_FAILURE: false,
  SIMULATE_LOAD_RULES_FAILURE: false,
};

const INITIAL_MOCK_CHANNELS: NotificationChannel[] = [
  {
    id: "a3b890f1-2856-4c92-b883-04981a8c3d11",
    name: "Engineering Alerts",
    channel_type: "email",
    destination: "dev-team@faultline.io",
    enabled: true,
  },
  {
    id: "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    name: "Incident Response Team",
    channel_type: "email",
    destination: "ops-oncall@faultline.io",
    enabled: true,
  },
  {
    id: "9c8b7a6d-5e4f-3a2b-1c0d-ef8a7b6c5d4e",
    name: "Disabled Legacy Team",
    channel_type: "email",
    destination: "legacy@faultline.io",
    enabled: false,
  },
];

let mockAlertRules: AlertRule[] = [
  {
    id: "1e4a3b8c-7f5d-419a-9e12-3a5b6c7d8e90",
    name: "Production New Issue Trigger",
    rule_type: "new_issue",
    environment: "production",
    severity: "critical",
    enabled: true,
    channels: [
      {
        id: "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        name: "Incident Response Team",
        channel_type: "email",
      },
      {
        id: "a3b890f1-2856-4c92-b883-04981a8c3d11",
        name: "Engineering Alerts",
        channel_type: "email",
      },
    ],
    created_at: "2026-11-10T14:32:00.000Z",
  },
  {
    id: "2d5b4c9e-8a6e-420b-af23-4b6c7d8e9f01",
    name: "Staging Unseen Error Alert",
    rule_type: "new_issue",
    environment: "staging",
    severity: "warning",
    enabled: true,
    channels: [
      {
        id: "a3b890f1-2856-4c92-b883-04981a8c3d11",
        name: "Engineering Alerts",
        channel_type: "email",
      },
    ],
    created_at: "2026-11-11T09:15:30.000Z",
  },
  {
    id: "3c6d5e0f-9b7f-431c-b034-5c7d8e9f0a12",
    name: "Global First-Seen Incident Detection",
    rule_type: "new_issue",
    environment: null, // "All environments"
    severity: "info",
    enabled: false,
    channels: [
      {
        id: "a3b890f1-2856-4c92-b883-04981a8c3d11",
        name: "Engineering Alerts",
        channel_type: "email",
      },
    ],
    created_at: "2026-11-12T18:45:10.000Z",
  },
];

/**
 * List notification channels for a project.
 * Uses real backend API call.
 */
export async function listChannels(
  projectId?: string
): Promise<NotificationChannel[]> {
  if (MOCK_CONFIG.MOCK_EMPTY_CHANNELS) {
    return [];
  }

  if (projectId) {
    return apiClient.get<NotificationChannel[]>(
      `/api/v1/projects/${projectId}/notification-channels`
    );
  }

  // Fallback for mock contexts where projectId is not passed
  await new Promise((resolve) => setTimeout(resolve, 300));
  return INITIAL_MOCK_CHANNELS.filter((channel) => channel.enabled);
}

/**
 * Create a new notification channel for a project.
 * Uses real backend API call.
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
 * List alert rules.
 */
export async function listAlertRules(): Promise<AlertRule[]> {
  await new Promise((resolve) => setTimeout(resolve, 350));

  if (MOCK_CONFIG.SIMULATE_LOAD_RULES_FAILURE) {
    throw new Error("Unable to load alert rules. Telemetry service unreachable.");
  }

  if (MOCK_CONFIG.MOCK_EMPTY_RULES) {
    return [];
  }

  return [...mockAlertRules];
}

/**
 * Delete an alert rule by id.
 */
export async function deleteAlertRule(id: string): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 400));
  mockAlertRules = mockAlertRules.filter((rule) => rule.id !== id);
}

/**
 * Toggle alert rule enabled status in mock store.
 */
export async function toggleAlertRule(id: string): Promise<AlertRule> {
  await new Promise((resolve) => setTimeout(resolve, 200));
  const rule = mockAlertRules.find((r) => r.id === id);
  if (!rule) {
    throw new Error("Alert rule not found");
  }
  rule.enabled = !rule.enabled;
  return { ...rule };
}

/**
 * Create an alert rule using mock delayed execution.
 */
export async function createAlertRule(
  payload: CreateAlertRulePayload
): Promise<{ id: string }> {
  await new Promise((resolve) => setTimeout(resolve, 600));

  if (MOCK_CONFIG.SIMULATE_SUBMIT_FAILURE) {
    throw new Error("Failed to create alert rule. Network timeout or service unavailable.");
  }

  const generatedId =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : "b7e45a29-4180-4cf7-8d0f-90e82c16a4b1";

  // Also append to in-memory mockAlertRules list for consistency
  const activeChannels = INITIAL_MOCK_CHANNELS.filter((c) =>
    payload.channel_ids.includes(c.id)
  ).map((c) => ({
    id: c.id,
    name: c.name,
    channel_type: c.channel_type,
  }));

  const newRule: AlertRule = {
    id: generatedId,
    name: payload.name,
    rule_type: payload.rule_type,
    environment: payload.environment,
    severity: payload.severity,
    enabled: true,
    channels: activeChannels,
    created_at: new Date().toISOString(),
  };

  mockAlertRules.unshift(newRule);

  return { id: generatedId };
}
