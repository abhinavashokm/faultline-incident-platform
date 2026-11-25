"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
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
      <ProjectSetupContent
        project={project}
        actions={
          <div className="flex items-center gap-2">
            <Button asChild variant="secondary">
              <Link href={`/${workspaceSlug}/overview`}>Skip for now</Link>
            </Button>
            <Button asChild className="gap-2">
              <Link href={`/${workspaceSlug}/overview`}>
                Go to dashboard
                <ArrowRight aria-hidden="true" className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        }
        footerActions={
          <Button asChild className="gap-2">
            <Link href={`/${workspaceSlug}/overview`}>
              Go to Overview Dashboard
              <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </Link>
          </Button>
        }
      />
    </div>
  );
}
