import type { Metadata } from "next";
import { ProjectSdkSetup } from "@/features/projects/components/project-sdk-setup";

export const metadata: Metadata = { title: "SDK setup | Faultline" };

export default function ProjectSdkSetupPage({
  params,
}: {
  params: { workspaceSlug: string; slug: string };
}) {
  return <ProjectSdkSetup workspaceSlug={params.workspaceSlug} slug={params.slug} />;
}
