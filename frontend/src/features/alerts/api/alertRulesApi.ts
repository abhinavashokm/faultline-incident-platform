import {
  NotificationChannel,
  CreateAlertRulePayload,
} from "../types";

/**
 * Flags to easily simulate edge cases / tests:
 * - MOCK_EMPTY_CHANNELS: set to true to test the empty state ("Add a notification channel first").
 * - SIMULATE_SUBMIT_FAILURE: set to true to test the submission failure error state.
 */
export const MOCK_CONFIG = {
  MOCK_EMPTY_CHANNELS: false,
  SIMULATE_SUBMIT_FAILURE: false,
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

/**
 * List notification channels.
 * Filters for channels where enabled = true.
 */
export async function listChannels(): Promise<NotificationChannel[]> {
  await new Promise((resolve) => setTimeout(resolve, 300));

  if (MOCK_CONFIG.MOCK_EMPTY_CHANNELS) {
    return [];
  }

  return INITIAL_MOCK_CHANNELS.filter((channel) => channel.enabled);
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

  return { id: generatedId };
}
