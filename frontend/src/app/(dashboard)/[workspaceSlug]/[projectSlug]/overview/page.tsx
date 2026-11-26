import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function OverviewPage({
  params,
}: {
  params: { workspaceSlug: string; projectSlug: string };
}) {
  const { workspaceSlug, projectSlug } = params;
  const projectPath = `/${workspaceSlug}/${projectSlug}`;

  return (
    <div className="space-y-6">
      <h1 className="text-headline-md font-semibold tracking-tight text-text-primary">
        Overview
      </h1>

      <div className="rounded-lg border border-border bg-card p-8 shadow-level-1">
        <p className="text-body-sm text-text-secondary">
          View project data in Issues and Performance, or open SDK setup to start
          sending telemetry.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button asChild size="sm" variant="secondary">
            <Link href={`${projectPath}/issues`}>View issues</Link>
          </Button>
          <Button asChild size="sm" variant="secondary">
            <Link href={`${projectPath}/performance`}>View performance</Link>
          </Button>
          <Button asChild size="sm" variant="secondary">
            <Link href={`/${workspaceSlug}/projects/${projectSlug}/sdk-setup`}>
              SDK setup
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
