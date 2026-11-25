"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/auth-context";
import { ProjectSetupContent } from "./project-setup-content";
import { useListProjects } from "../hooks";

export function ProjectSdkSetup({ workspaceSlug, slug }: { workspaceSlug: string; slug: string }) {
  const { isReady, isAuthenticated } = useAuth();
  const { data: projects, isPending, isError, isFetching, refetch } = useListProjects();
  const project = projects?.find((item) => item.slug === slug);
  const projectsPath = `/${workspaceSlug}/projects`;

  return (
    <div className="mx-auto w-full max-w-4xl">
      <nav aria-label="Breadcrumb" className="mb-4 text-body-sm">
        <ol className="flex items-baseline gap-2">
          <li>
            <Link href={projectsPath} className="rounded-sm text-text-secondary hover:underline focus-visible:outline-primary">
              Projects
            </Link>
          </li>
          <li aria-hidden="true" className="text-text-muted">/</li>
          <li className="min-w-0 break-words font-mono">
            <Link href={`${projectsPath}/${slug}`} className="rounded-sm text-text-secondary hover:underline focus-visible:outline-primary">
              {slug}
            </Link>
          </li>
          <li aria-hidden="true" className="text-text-muted">/</li>
          <li aria-current="page" className="text-text-primary">Setup</li>
        </ol>
      </nav>

      {!isReady || (isAuthenticated && isPending) ? (
        <div role="status">
          <span className="sr-only">Loading SDK setup…</span>
          <Skeleton aria-hidden="true" className="h-56 rounded-lg" />
        </div>
      ) : !isAuthenticated ? (
        <Card className="p-8 text-center">
          <Button asChild><Link href="/login">Sign in to view SDK setup</Link></Button>
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
        <ProjectSetupContent project={project} />
      )}
    </div>
  );
}
