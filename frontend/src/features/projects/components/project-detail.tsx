"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/auth-context";
import { useListProjects } from "../hooks";
import { PLATFORM_REGISTRY } from "../platform-registry";

export function ProjectDetail({ workspaceSlug, slug }: { workspaceSlug: string; slug: string }) {
  const { isReady, isAuthenticated } = useAuth();
  const { data: projects, isPending, isError, isFetching, refetch } = useListProjects();
  const project = projects?.find((item) => item.slug === slug);
  const projectsPath = `/${workspaceSlug}/projects`;

  return (
    <div className="mx-auto max-w-3xl">
      <nav aria-label="Breadcrumb" className="mb-4 text-body-sm">
        <ol className="flex items-baseline gap-2">
          <li>
            <Link href={projectsPath} className="rounded-sm text-text-secondary hover:underline focus-visible:outline-primary">
              Projects
            </Link>
          </li>
          <li aria-hidden="true" className="text-text-muted">/</li>
          <li aria-current="page" className="min-w-0 break-words font-mono text-text-primary">
            {slug}
          </li>
        </ol>
      </nav>

      {!isReady || (isAuthenticated && isPending) ? (
        <div role="status">
          <span className="sr-only">Loading project…</span>
          <Skeleton aria-hidden="true" className="h-56 rounded-lg" />
        </div>
      ) : !isAuthenticated ? (
        <Card className="p-8 text-center">
          <Button asChild><Link href="/login">Sign in to view project details</Link></Button>
        </Card>
      ) : isError ? (
        <Card className="space-y-3 p-8 text-center">
          <p role="alert" className="text-body-sm text-text-secondary">Couldn’t load the project.</p>
          <Button variant="secondary" disabled={isFetching} onClick={() => void refetch()}>
            Try again
          </Button>
        </Card>
      ) : !project ? (
        <Card className="p-8 text-center">
          <h1 className="text-headline-sm font-semibold">Project not found</h1>
        </Card>
      ) : (
        <Card>
          <header className="border-b border-border p-6">
            <h1 className="break-words text-headline-md font-semibold tracking-tight">{project.name}</h1>
            <p className="mt-1 break-words font-mono text-label-sm text-text-muted">{project.slug}</p>
          </header>
          <dl className="grid gap-5 p-6 sm:grid-cols-2">
            <div>
              <dt className="text-label-md font-semibold">Platform</dt>
              <dd className="mt-1 break-words text-body-sm text-text-secondary">
                {project.platform ? PLATFORM_REGISTRY[project.platform]?.label ?? project.platform : "Unspecified"}
              </dd>
            </div>
            <div>
              <dt className="text-label-md font-semibold">Status</dt>
              <dd className="mt-1 text-body-sm capitalize text-text-secondary">{project.status}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-label-md font-semibold">Description</dt>
              <dd className="mt-1 whitespace-pre-wrap break-words text-body-sm text-text-secondary">
                {project.description || "No description provided."}
              </dd>
            </div>
          </dl>
          <div className="flex flex-wrap gap-2 border-t border-border px-6 py-4">
            <Button asChild>
              <Link href={`/${workspaceSlug}/${project.slug}/overview`}>Open project</Link>
            </Button>
            <Button asChild variant="secondary">
              <Link href={`${projectsPath}/${project.slug}/sdk-setup`}>SDK setup</Link>
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
