import React from "react";
import Link from "next/link";
import { FolderX, ArrowLeft, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ProjectNotFoundProps {
  slug: string;
  workspaceSlug: string;
  isArchived?: boolean;
}

export function ProjectNotFound({ slug, workspaceSlug, isArchived }: ProjectNotFoundProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-12 text-center shadow-level-1 max-w-xl mx-auto my-8">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-warning-tint border border-warning-subdued text-warning mb-4">
        <FolderX className="h-7 w-7" />
      </div>
      <h3 className="text-headline-sm font-semibold text-text-primary">
        {isArchived ? "Project is Archived" : "Project Not Found"}
      </h3>
      <p className="text-body-sm text-text-secondary max-w-md mx-auto mt-2 mb-6">
        {isArchived ? (
          <>
            The project <code className="font-mono text-text-primary px-1 py-0.5 bg-canvas rounded">{slug}</code> is archived. SDK ingestion and keys cannot be configured for archived projects.
          </>
        ) : (
          <>
            No project matching <code className="font-mono text-text-primary px-1 py-0.5 bg-canvas rounded">{slug}</code> exists in this workspace.
          </>
        )}
      </p>

      <div className="flex items-center justify-center gap-3">
        <Button variant="secondary" asChild className="gap-2">
          <Link href={`/${workspaceSlug}/overview`}>
            <ArrowLeft className="h-4 w-4" />
            <span>Go to Overview</span>
          </Link>
        </Button>
        <Button asChild className="gap-2">
          <Link href={`/${workspaceSlug}/projects/new`}>
            <Plus className="h-4 w-4" />
            <span>Create Project</span>
          </Link>
        </Button>
      </div>
    </div>
  );
}
