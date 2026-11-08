export const RESERVED_PROJECT_SLUGS = [
  "overview",
  "issues",
  "projects",
  "settings",
  "alerts",
  "incidents",
  "investigations",
  "performance",
  "members",
  "billing",
  "api",
  "auth",
  "new",
] as const;

export type ReservedProjectSlug = (typeof RESERVED_PROJECT_SLUGS)[number];

export function isReservedProjectSlug(slug: string): boolean {
  return RESERVED_PROJECT_SLUGS.includes(
    slug.toLowerCase() as ReservedProjectSlug
  );
}
