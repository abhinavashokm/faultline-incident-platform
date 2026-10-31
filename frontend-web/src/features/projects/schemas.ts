import { z } from "zod";

export const createProjectSchema = z.object({
  name: z
    .string()
    .min(2, "Project name must be at least 2 characters")
    .max(50, "Project name must be under 50 characters"),
  slug: z
    .string()
    .min(2, "Slug must be at least 2 characters")
    .regex(/^[a-z0-9-]+$/, "Slug must only contain lowercase letters, numbers, and hyphens"),
  platform: z.enum(["python", "javascript", "node", "java", "go", "other"], {
    required_error: "Please select a platform",
  }),
  environment: z.string().optional().default("production"),
});

export type CreateProjectFormData = z.infer<typeof createProjectSchema>;

