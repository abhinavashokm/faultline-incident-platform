"use client";

import Link from "next/link";
import { ArrowUpRight, FolderOpen, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/auth-context";
import { ProjectEditDialog } from "./project-edit-dialog";
import { useListProjects } from "../hooks";
import { PLATFORM_REGISTRY } from "../platform-registry";
import { useCurrentUser } from "@/features/auth/hooks";

export function ProjectList({ workspaceSlug }: { workspaceSlug: string }) {
  const { isReady, isAuthenticated } = useAuth();
  const { data: currentUser } = useCurrentUser();
  const { data: projects, isPending, isError, isFetching, refetch } = useListProjects();
  const workspacePath = `/${workspaceSlug}`;
  const role = currentUser?.memberships?.find(
    (membership) => membership.workspace_id === currentUser.workspace?.id
  )?.role;
  const canManageProjects = role === "owner" || role === "admin";

  return (
    <section aria-labelledby="projects-heading">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h1 id="projects-heading" className="text-headline-md font-semibold">Projects</h1>
        {isAuthenticated && canManageProjects && (
          <Button asChild>
            <Link href={`${workspacePath}/projects/new`}>
              <Plus aria-hidden="true" className="mr-2 h-4 w-4" />
              New project
            </Link>
          </Button>
        )}
      </div>

      {!isReady || (isAuthenticated && isPending) ? (
        <div role="status" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <span className="sr-only">Loading projects…</span>
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} aria-hidden="true" className="h-44" />
          ))}
        </div>
      ) : !isAuthenticated ? (
        <Card className="p-8 text-center">
          <Button asChild><Link href="/login">Sign in to view projects</Link></Button>
        </Card>
      ) : isError ? (
        <Card className="space-y-3 p-8 text-center">
          <p role="alert" className="text-body-sm text-text-secondary">Couldn’t load projects.</p>
          <Button variant="secondary" disabled={isFetching} onClick={() => void refetch()}>
            Try again
          </Button>
        </Card>
      ) : !projects?.length ? (
        <Card className="p-10 text-center">
          <FolderOpen aria-hidden="true" className="mx-auto mb-3 h-6 w-6 text-text-muted" />
          <h2 className="text-headline-sm font-semibold">No projects yet</h2>
        </Card>
      ) : (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <li key={project.id} className="min-w-0">
              <Card className="flex h-full flex-col">
                <div className="flex-1 p-5">
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <div className="rounded-md border border-border bg-canvas p-2 text-primary">
                      <FolderOpen aria-hidden="true" className="h-5 w-5" />
                    </div>
                    {project.platform && (
                      <span className="text-label-sm text-text-secondary">
                        {PLATFORM_REGISTRY[project.platform]?.label ?? project.platform}
                      </span>
                    )}
                  </div>
                  <h2 className="break-words text-headline-sm font-semibold">{project.name}</h2>
                  <p className="mt-1 break-words font-mono text-label-sm text-text-muted">{project.slug}</p>
                  {project.description && (
                    <p className="mt-3 break-words text-body-sm text-text-secondary">{project.description}</p>
                  )}
                </div>
                <div className="flex items-center justify-between gap-2 border-t border-border px-5 py-3">
                  <Button asChild variant="link">
                    <Link href={`${workspacePath}/${project.slug}/overview`} aria-label={`Open ${project.name}`}>
                      Open project
                      <ArrowUpRight aria-hidden="true" className="ml-1 h-4 w-4" />
                    </Link>
                  </Button>
                  {canManageProjects && <ProjectEditDialog project={project} />}
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
