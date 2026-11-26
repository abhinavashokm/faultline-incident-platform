"use client";

import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useProjectBySlug } from "@/features/projects/hooks";
import { apiClient } from "@/lib/api-client";

type Deployment = {
  id: string;
  environment: string;
  kind: string;
  status: string;
  externalRunId: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
};

type Release = {
  id: string;
  version: string;
  commitSha: string | null;
  artifactRef: string | null;
  createdAt: string;
  deployments: Deployment[];
};

const dateFormat = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

function Timestamp({ value }: { value: string | null }) {
  return value ? <time dateTime={value}>{dateFormat.format(new Date(value))}</time> : "—";
}

export default function ReleasesPage({ params }: { params: { projectSlug: string } }) {
  const { project, isLoading, isError, isNotFound, isArchived } = useProjectBySlug(params.projectSlug);
  const projectId = project?.id;
  const releases = useQuery({
    queryKey: ["project-releases", projectId],
    queryFn: ({ signal }) => apiClient.get<Release[]>(`/api/v1/projects/${projectId}/releases`, { signal }),
    enabled: Boolean(projectId && !isArchived),
  });

  return (
    <section className="space-y-5" aria-labelledby="releases-heading">
      <h1 id="releases-heading" className="text-headline-md font-semibold tracking-tight">Releases</h1>
      {isLoading ? (
        <p role="status" className="text-body-sm text-text-secondary">Loading project…</p>
      ) : isError ? (
        <p role="alert" className="text-body-sm text-error">Couldn’t load the project.</p>
      ) : isNotFound || isArchived || !project ? (
        <p className="text-body-sm text-text-secondary">Project not found.</p>
      ) : releases.isPending ? (
        <p role="status" className="text-body-sm text-text-secondary">Loading releases…</p>
      ) : releases.isError ? (
        <Card className="flex flex-wrap items-center gap-3 p-5">
          <p role="alert" className="text-body-sm text-error">Couldn’t load releases.</p>
          <Button size="sm" variant="secondary" onClick={() => void releases.refetch()}>Try again</Button>
        </Card>
      ) : releases.data.length === 0 ? (
        <Card className="p-6">
          <p className="text-body-sm text-text-secondary">No releases registered yet.</p>
        </Card>
      ) : (
        <ul className="space-y-3">
          {releases.data.map((release) => (
            <li key={release.id}>
              <Card className="p-5">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h2 className="min-w-0 break-all font-mono text-headline-sm font-semibold">{release.version}</h2>
                  <p className="text-body-sm text-text-secondary">Registered <Timestamp value={release.createdAt} /></p>
                </div>
                <dl className="mt-3 grid gap-3 text-body-sm sm:grid-cols-2">
                  <div className="min-w-0">
                    <dt className="font-medium text-text-secondary">Commit SHA</dt>
                    <dd className="break-all font-mono">{release.commitSha ?? "—"}</dd>
                  </div>
                  <div className="min-w-0">
                    <dt className="font-medium text-text-secondary">Artifact</dt>
                    <dd className="break-all font-mono">{release.artifactRef ?? "—"}</dd>
                  </div>
                </dl>
                <details className="mt-4 border-t border-border pt-3">
                  <summary className="cursor-pointer text-body-sm font-semibold">
                    Deployment history ({release.deployments.length})
                  </summary>
                  {release.deployments.length === 0 ? (
                    <p className="mt-3 text-body-sm text-text-secondary">No deployment attempts recorded.</p>
                  ) : (
                    <div className="mt-3 overflow-x-auto">
                      <table className="w-full text-left text-body-sm">
                        <thead className="text-text-secondary">
                          <tr>
                            {["Environment", "Status", "Registered", "Started", "Finished", "CI run"].map((label) => (
                              <th key={label} scope="col" className="whitespace-nowrap px-2 py-1 font-medium">{label}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {release.deployments.map((deployment) => (
                            <tr key={deployment.id} className="border-t border-border">
                              <td className="px-2 py-2">
                                {deployment.environment}
                                {deployment.kind === "rollback" && <span className="ml-2 text-text-secondary">(rollback)</span>}
                              </td>
                              <td className="whitespace-nowrap px-2 py-2 capitalize">{deployment.status.replaceAll("_", " ")}</td>
                              <td className="whitespace-nowrap px-2 py-2"><Timestamp value={deployment.createdAt} /></td>
                              <td className="whitespace-nowrap px-2 py-2"><Timestamp value={deployment.startedAt} /></td>
                              <td className="whitespace-nowrap px-2 py-2"><Timestamp value={deployment.finishedAt} /></td>
                              <td className="px-2 py-2 font-mono">{deployment.externalRunId ?? "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </details>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
