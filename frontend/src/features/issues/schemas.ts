import { z } from "zod";

export const issueFilterSchema = z.object({
  status: z.enum(["unresolved", "resolved", "ignored"]).default("unresolved"),
  environment: z.string().default("all"),
  timeRange: z.enum(["1h", "24h", "7d", "14d", "30d"]).default("24h"),
  search: z.string().optional(),
  cursor: z.string().optional(),
  limit: z.number().int().min(1).max(100).default(25),
});

export type IssueFilterInput = z.infer<typeof issueFilterSchema>;

export const updateIssueStatusSchema = z.object({
  status: z.enum(["unresolved", "resolved", "ignored"]),
});

export type UpdateIssueStatusInput = z.infer<typeof updateIssueStatusSchema>;

export const bulkUpdateIssueStatusSchema = z.object({
  issueIds: z.array(z.string()).min(1, "Select at least one issue"),
  status: z.enum(["unresolved", "resolved", "ignored"]),
});

export type BulkUpdateIssueStatusInput = z.infer<typeof bulkUpdateIssueStatusSchema>;

