"use client";

import React from "react";
import { useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useProjectBySlug } from "@/features/projects/hooks";
import { ProjectSetupContent } from "@/features/projects/components/project-setup-content";
import { ProjectNotFound } from "@/features/projects/components/project-not-found";

export default function ProjectSetupPage() {
  const params = useParams();
  const workspaceSlug = (params.workspaceSlug as string) || "";
  const projectSlug = (params.slug as string) || "";

  const { project, isLoading, isNotFound, isArchived } = useProjectBySlug(projectSlug);

  if (isLoading || (!project && !isNotFound)) {
    return (
      <div className="py-20 flex flex-col items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
        <span className="text-body-sm text-text-secondary">Loading project telemetry setup...</span>
      </div>
    );
  }

  if (isNotFound || !project) {
    return (
      <ProjectNotFound
        slug={projectSlug}
        workspaceSlug={workspaceSlug}
        isArchived={isArchived}
      />
    );
  }

  return (
    <div className="max-w-4xl w-full mx-auto py-2 sm:py-6">
      <ProjectSetupContent project={project} workspaceSlug={workspaceSlug} />
    </div>
  );
}
