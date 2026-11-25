import type { Metadata } from "next";
import { ProjectDetail } from "@/features/projects/components/project-detail";

export const metadata: Metadata = { title: "Project details | Faultline" };

export default function ProjectDetailPage({
  params,
}: {
  params: { workspaceSlug: string; slug: string };
}) {
  return <ProjectDetail workspaceSlug={params.workspaceSlug} slug={params.slug} />;
}
