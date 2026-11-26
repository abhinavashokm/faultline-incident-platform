"use client";

import { skipToken, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { incidentsQueryKey, listIncidents } from "@/features/incidents/api";
import { useProjectBySlug } from "@/features/projects/hooks";

const columns = ["Incident", "Severity", "Status", "Assignee", "Started"];
const startedDate = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

export default function IncidentsPage({
  params,
}: {
  params: { workspaceSlug: string; projectSlug: string };
}) {
  const incidentsHref = `/${params.workspaceSlug}/${params.projectSlug}/incidents`;
  const projectQuery = useProjectBySlug(params.projectSlug);
  const projectId = projectQuery.project?.id;
  const incidents = useQuery({
    queryKey: incidentsQueryKey(projectId),
    queryFn: projectId ? () => listIncidents(projectId) : skipToken,
  });

  const loading = projectQuery.isLoading || incidents.isLoading;
  const error = projectQuery.isError
    ? "Couldn’t load the project."
    : !projectId
      ? "Project not found."
      : incidents.isError
        ? incidents.error.message
        : null;

  return (
    <div className="flex-1 space-y-6 p-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Incidents
        </h1>
        <Button className="gap-2" asChild>
          <Link href={`${incidentsHref}/new`}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Create incident
          </Link>
        </Button>
      </header>

      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <caption className="sr-only">Project incidents</caption>
          <thead className="border-b bg-muted/40 text-muted-foreground">
            <tr>
              {columns.map((column) => (
                <th key={column} scope="col" className="px-4 py-3 font-medium">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading || error || !incidents.data?.length ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-16 text-center text-muted-foreground">
                  {loading ? (
                    <span role="status">Loading incidents…</span>
                  ) : error ? (
                    <div className="space-y-3">
                      <p role="alert">{error}</p>
                      {incidents.isError && (
                        <Button variant="outline" size="sm" onClick={() => void incidents.refetch()}>
                          Try again
                        </Button>
                      )}
                    </div>
                  ) : (
                    "No incidents yet."
                  )}
                </td>
              </tr>
            ) : (
              incidents.data.map((incident) => (
                <tr key={incident.id} className="border-b last:border-b-0">
                  <th scope="row" className="px-4 py-3 font-medium text-foreground">
                    <Link href={`${incidentsHref}/${incident.id}`} className="hover:text-primary hover:underline focus-visible:underline">
                      {incident.title}
                    </Link>
                  </th>
                  <td className="px-4 py-3 capitalize">{incident.severity}</td>
                  <td className="px-4 py-3 capitalize">{incident.status.replaceAll("_", " ")}</td>
                  <td className="px-4 py-3">
                    {incident.assigneeId ?? "Unassigned"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <time dateTime={incident.startedAt}>
                      {startedDate.format(new Date(incident.startedAt))}
                    </time>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
