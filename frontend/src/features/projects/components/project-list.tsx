"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { ArrowRight, FolderOpen, Plus, Trash2, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/use-toast";
import { useAuth } from "@/features/auth/auth-context";
import { ProjectEditDialog } from "./project-edit-dialog";
import { useDeleteProject, useListProjects } from "../hooks";
import { PLATFORM_REGISTRY } from "../platform-registry";
import type { Project } from "../types";
import { useCurrentUser } from "@/features/auth/hooks";

export function ProjectList({ workspaceSlug }: { workspaceSlug: string }) {
  const { isReady, isAuthenticated } = useAuth();
  const { data: currentUser } = useCurrentUser();
  const { data: projects, isPending, isError, isFetching, refetch } = useListProjects();
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const deleteProject = useDeleteProject();
  const workspacePath = `/${workspaceSlug}`;
  const role = currentUser?.memberships?.find(
    (membership) => membership.workspace_id === currentUser.workspace?.id
  )?.role;
  const canManageProjects = role === "owner" || role === "admin";

  return (
    <section aria-labelledby="projects-heading">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-border pb-5">
        <h1 id="projects-heading" ref={headingRef} tabIndex={-1} className="text-headline-md font-semibold tracking-tight">Projects</h1>
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
            <Skeleton key={index} aria-hidden="true" className="h-44 rounded-lg" />
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
        <Card className="border-dashed p-10 text-center">
          <FolderOpen aria-hidden="true" className="mx-auto mb-3 h-6 w-6 text-text-muted" />
          <h2 className="text-headline-sm font-semibold">No projects yet</h2>
        </Card>
      ) : (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <li key={project.id} className="min-w-0">
              <Card className="flex h-full flex-col transition-colors focus-within:border-border-hover hover:border-border-hover">
                <div className="flex-1 p-5">
                  <div className="flex items-start gap-3">
                    <div className="shrink-0 rounded-md bg-primary-tint p-2 text-primary">
                      <FolderOpen aria-hidden="true" className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h2 className="break-words text-body-md font-semibold">{project.name}</h2>
                      <p className="mt-0.5 break-words font-mono text-label-sm text-text-muted">
                        {project.slug}
                      </p>
                    </div>
                    {canManageProjects && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="-mr-2 ml-auto shrink-0 hover:bg-error-container hover:text-error"
                        aria-label={`Delete ${project.name}`}
                        title="Delete project"
                        onClick={() => {
                          deleteProject.reset();
                          setProjectToDelete(project);
                        }}
                      >
                        <Trash2 aria-hidden="true" className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                  {project.description && (
                    <p className="mt-4 break-words text-body-sm text-text-secondary">{project.description}</p>
                  )}
                  {project.platform && (
                    <Badge
                      variant={project.platform === "fastapi" ? "success" : "default"}
                      showDot={false}
                      className="mt-3 max-w-full break-all font-sans normal-case tracking-normal"
                    >
                      <span className="flex items-center gap-1.5">
                        {project.platform === "fastapi" && (
                          <Zap aria-hidden="true" className="h-3 w-3 shrink-0" />
                        )}
                        {PLATFORM_REGISTRY[project.platform]?.label ?? project.platform}
                      </span>
                    </Badge>
                  )}
                </div>
                <div className="flex items-center justify-between gap-2 border-t border-border px-5 py-2">
                  <Button asChild variant="ghost" size="sm" className="-ml-2 gap-1.5">
                    <Link href={`${workspacePath}/${project.slug}/overview`} aria-label={`Open ${project.name}`}>
                      Open project
                      <ArrowRight aria-hidden="true" className="h-4 w-4" />
                    </Link>
                  </Button>
                  {canManageProjects && <ProjectEditDialog project={project} />}
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
      {isAuthenticated && canManageProjects && projectToDelete && (
        <ConfirmationDialog
          title="Delete project?"
          confirmLabel={deleteProject.isPending ? "Deleting…" : "Delete project"}
          pending={deleteProject.isPending}
          onCancel={() => setProjectToDelete(null)}
          onConfirm={() => {
            if (deleteProject.isPending) return;
            deleteProject.mutate(projectToDelete.id, {
              onSuccess: () => {
                setProjectToDelete(null);
                toast({ title: "Project deleted", variant: "success" });
                requestAnimationFrame(() => headingRef.current?.focus());
              },
            });
          }}
        >
          <p className="break-words">
            <strong>{projectToDelete.name}</strong> will be archived and removed from the project list.
            You can’t restore it from the app or reuse its slug.
          </p>
          {deleteProject.isError && (
            <p role="alert" className="mt-3 text-error">{deleteProject.error.message}</p>
          )}
        </ConfirmationDialog>
      )}
    </section>
  );
}
