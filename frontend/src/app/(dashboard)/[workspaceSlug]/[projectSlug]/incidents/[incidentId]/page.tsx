"use client";

import { skipToken, useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowUpRight, Bug, Clock3 } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getIncident } from "@/features/incidents/api";
import { useProjectBySlug } from "@/features/projects/hooks";
import { ApiError } from "@/lib/api-client";

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

function IncidentTime({ value }: { value: string }) {
  return <time dateTime={value}>{dateFormat.format(new Date(value))}</time>;
}

export default function IncidentDetailPage({
  params,
}: {
  params: { workspaceSlug: string; projectSlug: string; incidentId: string };
}) {
  const { workspaceSlug, projectSlug, incidentId } = params;
  const projectHref = `/${workspaceSlug}/${projectSlug}`;
  const projectQuery = useProjectBySlug(projectSlug);
  const projectId = projectQuery.project?.id;
  const detail = useQuery({
    queryKey: ["incident-detail", projectId, incidentId],
    queryFn: projectId ? ({ signal }) => getIncident(projectId, incidentId, signal) : skipToken,
    retry: (count, error) => count < 2 && !(error instanceof ApiError && error.status < 500),
  });
  const incident = detail.data;
  const unavailable = detail.error instanceof ApiError && [403, 404].includes(detail.error.status);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <Button variant="ghost" size="sm" className="-ml-2 gap-2" asChild>
        <Link href={`${projectHref}/incidents`}>
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to incidents
        </Link>
      </Button>

      {projectQuery.isLoading || detail.isLoading ? (
        <p role="status" className="text-sm text-muted-foreground">Loading incident…</p>
      ) : projectQuery.isError || !projectId || !incident ? (
        <div className="space-y-3 rounded-xl border bg-card p-6">
          <h1 className="text-headline-sm">Incident details</h1>
          <p role="alert" className="text-sm text-muted-foreground">
            {projectQuery.isError ? "Couldn’t load the project." : !projectId ? "Project not found." : unavailable ? "Incident not found." : "Couldn’t load the incident."}
          </p>
          {!projectQuery.isError && detail.isError && !unavailable && (
            <Button variant="outline" size="sm" onClick={() => void detail.refetch()}>
              Try again
            </Button>
          )}
        </div>
      ) : (
        <>
          <header className="space-y-4">
            <h1 className="break-words text-3xl font-semibold tracking-tight">{incident.title}</h1>
            <div className="flex flex-wrap gap-2">
              <Badge variant={incident.severity === "critical" ? "error" : incident.severity === "high" ? "warning" : "neutral"}>
                {incident.severity} severity
              </Badge>
              <Badge variant={incident.status === "resolved" ? "success" : "info"}>
                {incident.status.replaceAll("_", " ")}
              </Badge>
            </div>
          </header>
          <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <section aria-labelledby="overview-heading" className="min-w-0 rounded-xl border bg-card p-5 shadow-level-1">
              <h2 id="overview-heading" className="text-headline-sm">Overview</h2>
              <p className="mt-3 whitespace-pre-wrap break-words text-sm text-text-secondary">
                {incident.description?.trim() ? incident.description : "No description provided."}
              </p>
            </section>
            <section aria-labelledby="details-heading" className="min-w-0 rounded-xl border bg-card p-5 shadow-level-1">
              <h2 id="details-heading" className="text-headline-sm">Details</h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div>
                  <dt className="text-muted-foreground">Started</dt>
                  <dd className="mt-1"><IncidentTime value={incident.startedAt} /></dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Assignee</dt>
                  <dd className="mt-1 break-all">{incident.assigneeId ?? "Unassigned"}</dd>
                </div>
              </dl>
            </section>
          </div>

          <section aria-labelledby="issues-heading" className="overflow-hidden rounded-xl border bg-card shadow-level-1">
            <h2 id="issues-heading" className="flex items-center gap-2 border-b bg-canvas px-5 py-4 text-headline-sm">
              <Bug className="h-5 w-5 text-primary" aria-hidden="true" />
              Related issues
            </h2>
            {incident.relatedIssues.length ? (
              <ul className="divide-y divide-border">
                {incident.relatedIssues.map((issue) => (
                  <li key={issue.issueId} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3">
                    <div className="min-w-0">
                      <Link href={`${projectHref}/issues/${issue.issueId}`} className="inline-flex max-w-full items-start gap-1.5 text-sm font-medium text-primary hover:underline">
                        <span className="min-w-0 break-words">{issue.issueTitle ?? issue.issueId}</span>
                        <ArrowUpRight className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                      </Link>
                      {issue.errorType && <p className="break-words font-mono text-xs text-muted-foreground">{issue.errorType}</p>}
                    </div>
                    {issue.occurrenceCount !== null && (
                      <span className="text-xs tabular-nums text-muted-foreground">
                        {issue.occurrenceCount.toLocaleString()} {issue.occurrenceCount === 1 ? "event" : "events"} at link time
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            ) : <p className="px-5 py-4 text-sm text-muted-foreground">No related issues linked.</p>}
          </section>

          <section aria-labelledby="timeline-heading" className="overflow-hidden rounded-xl border bg-card shadow-level-1">
            <h2 id="timeline-heading" className="flex items-center gap-2 border-b bg-canvas px-5 py-4 text-headline-sm">
              <Clock3 className="h-5 w-5 text-primary" aria-hidden="true" />
              Timeline
            </h2>
            {incident.timeline.length ? (
              <ol className="divide-y divide-border">
                {incident.timeline.map((entry) => (
                  <li key={entry.id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-5 py-3">
                    <p className="min-w-0 whitespace-pre-wrap break-words text-sm">{entry.message}</p>
                    <span className="shrink-0 text-xs tabular-nums text-muted-foreground"><IncidentTime value={entry.createdAt} /></span>
                  </li>
                ))}
              </ol>
            ) : <p className="px-5 py-4 text-sm text-muted-foreground">No timeline entries yet.</p>}
          </section>
        </>
      )}
    </div>
  );
}
