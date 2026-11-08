"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useListProjects } from "@/features/projects/hooks";

export default function WorkspaceRootRedirect() {
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = (params.workspaceSlug as string) || "";
  const { data: projects, isLoading } = useListProjects();

  useEffect(() => {
    if (isLoading) return;

    if (projects && projects.length > 0) {
      router.replace(`/${workspaceSlug}/${projects[0].slug}/overview`);
    } else {
      router.replace(`/${workspaceSlug}/projects/new`);
    }
  }, [projects, isLoading, workspaceSlug, router]);

  return (
    <div className="min-h-[50vh] flex items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}
