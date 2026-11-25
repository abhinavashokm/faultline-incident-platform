import type { Metadata } from "next";
import { ProjectList } from "@/features/projects/components/project-list";

export const metadata: Metadata = { title: "Projects | Faultline" };

export default function ProjectsPage({ params }: { params: { workspaceSlug: string } }) {
  return <ProjectList workspaceSlug={params.workspaceSlug} />;
}
