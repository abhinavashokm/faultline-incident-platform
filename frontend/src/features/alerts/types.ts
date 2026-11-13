import { z } from "zod";

export type AlertSeverity = "info" | "warning" | "critical";

export type RuleType = "new_issue";

export interface NotificationChannel {
  id: string; // uuid
  name: string;
  channel_type: "email";
  destination: string;
  enabled: boolean;
}

export interface CreateAlertRulePayload {
  name: string;
  rule_type: "new_issue";
  conditions: Record<string, never>;
  environment: string | null;
  severity: AlertSeverity;
  channel_ids: string[];
}

export const createAlertRuleSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Name is required")
    .max(150, "Name must not exceed 150 characters"),
  rule_type: z.literal("new_issue").default("new_issue"),
  channel_ids: z
    .array(z.string().uuid("Invalid channel identifier"))
    .min(1, "At least one notification channel must be selected"),
  environment: z
    .string()
    .trim()
    .regex(/^[a-z0-9_-]+$/, "Environment must be lowercase and contain only letters, numbers, underscores, or hyphens")
    .or(z.literal(""))
    .optional(),
  severity: z.enum(["info", "warning", "critical"] as const),
});

export type CreateAlertRuleFormData = z.infer<typeof createAlertRuleSchema>;
