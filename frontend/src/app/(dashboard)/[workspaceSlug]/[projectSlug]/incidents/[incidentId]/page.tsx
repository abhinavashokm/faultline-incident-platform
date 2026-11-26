"use client";

import { useState } from "react";
import { skipToken, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ChevronRight } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/use-toast";
import { getIncident, incidentsQueryKey, updateIncidentStatus } from "@/features/incidents/api";
import { getStatusPresentation, type StatusTransition } from "@/features/incidents/status";
import { StatusActionButton, StatusBadge, StatusChangeModal } from "@/features/incidents/status-controls";
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
  const detailKey = ["incident-detail", projectId, incidentId] as const;
  const queryClient = useQueryClient();
  const [confirmation, setConfirmation] = useState<{ incidentId: string; transition: StatusTransition }>();
  const detail = useQuery({
    queryKey: detailKey,
    queryFn: projectId ? ({ signal }) => getIncident(projectId, incidentId, signal) : skipToken,
    retry: (count, error) => count < 2 && !(error instanceof ApiError && error.status < 500),
  });
  const incident = detail.data;
  const presentation = incident ? getStatusPresentation(incident.status) : undefined;
  const nextTransition = presentation?.transition;
  const transition = confirmation && confirmation.incidentId === incident?.id
    ? confirmation.transition
    : undefined;
  const statusUpdate = useMutation({
    mutationFn: ({ id, transition, note }: { id: string; projectId: string; transition: StatusTransition; note?: string }) =>
      updateIncidentStatus(id, transition.target, note),
    retry: false,
    onSuccess: async (updated, target) => {
      const key = ["incident-detail", target.projectId, target.id] as const;
      await queryClient.cancelQueries({ queryKey: key, exact: true });
      queryClient.setQueryData<Awaited<ReturnType<typeof getIncident>>>(key, (current) =>
        current ? { ...current, status: updated.status, resolvedAt: updated.resolvedAt } : current,
      );
      setConfirmation((current) => current?.incidentId === target.id ? undefined : current);
      toast({ title: "Incident status updated", variant: "success" });
      void queryClient.invalidateQueries({ queryKey: key, exact: true });
      void queryClient.invalidateQueries({ queryKey: incidentsQueryKey(target.projectId), exact: true });
    },
  });
  const statusError = statusUpdate.isError
    ? statusUpdate.error instanceof ApiError && statusUpdate.error.status === 409
      ? statusUpdate.error.message
      : "Couldn’t update the incident status. Try again."
    : undefined;
  const unavailable = detail.error instanceof ApiError && [403, 404].includes(detail.error.status);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-6 sm:px-6 lg:px-8">
      <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-2 text-label-md text-text-secondary">
        <Link
          href={`${projectHref}/incidents`}
          className="inline-flex shrink-0 items-center gap-1 transition-colors hover:text-text-primary"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Incidents</span>
        </Link>
        <span className="text-text-muted" aria-hidden="true">/</span>
        {incident && (
          <>
            <span className="shrink-0 font-mono text-text-muted">{incident.id.slice(0, 8)}</span>
            <span className="text-text-muted" aria-hidden="true">/</span>
          </>
        )}
        <span aria-current="page" className="truncate font-semibold text-text-primary">
          {incident?.title ?? "Incident details"}
        </span>
      </nav>

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
          <header className="rounded-xl border bg-card shadow-level-1">
            <div className="space-y-4 p-5 sm:p-6">
              <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={incident.status} variant={presentation?.variant} />
                  <Badge variant={incident.severity === "critical" ? "error" : incident.severity === "high" ? "warning" : "neutral"} showDot={false}>
                    {incident.severity} severity
                  </Badge>
                </div>
                {nextTransition && (
                  <StatusActionButton
                    transition={nextTransition}
                    onClick={() => {
                      statusUpdate.reset();
                      setConfirmation({ incidentId: incident.id, transition: nextTransition });
                    }}
                  />
                )}
              </div>
              <h1 className="break-words text-display-lg-mobile text-foreground sm:text-display-lg">{incident.title}</h1>
              <p className="max-w-prose whitespace-pre-wrap break-words text-body-md text-text-secondary">
                {incident.description?.trim() ? incident.description : "No description provided."}
              </p>
            </div>

            <dl className="grid gap-x-6 gap-y-4 rounded-b-xl border-t bg-canvas px-5 py-4 sm:grid-cols-2 sm:px-6">
              <div>
                <dt className="text-label-sm text-text-secondary">Started</dt>
                <dd className="mt-1 text-body-sm font-medium tabular-nums"><IncidentTime value={incident.startedAt} /></dd>
              </div>
              {incident.status === "resolved" && incident.resolvedAt && (
                <div>
                  <dt className="text-label-sm text-text-secondary">Resolved</dt>
                  <dd className="mt-1 text-body-sm font-medium tabular-nums"><IncidentTime value={incident.resolvedAt} /></dd>
                </div>
              )}
            </dl>
          </header>

          <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
            <section aria-labelledby="timeline-heading" className="min-w-0 rounded-xl border bg-card shadow-level-1">
              <h2 id="timeline-heading" className="border-b px-5 py-4 text-title-md">Timeline</h2>
              {incident.timeline.length ? (
                <ol className="px-5 py-4">
                  {incident.timeline.map((entry) => (
                    <li key={entry.id} className="relative pb-5 pl-5 last:pb-0 before:absolute before:-bottom-2 before:left-[3px] before:top-2 before:w-px before:bg-border last:before:hidden">
                      <span className="absolute left-0 top-1.5 h-[7px] w-[7px] rounded-full bg-border-hover" aria-hidden="true" />
                      <p className="whitespace-pre-wrap break-words text-body-sm text-foreground">{entry.message}</p>
                      <p className="mt-0.5 text-label-sm tabular-nums text-text-secondary"><IncidentTime value={entry.createdAt} /></p>
                    </li>
                  ))}
                </ol>
              ) : <p className="px-5 py-5 text-body-sm text-text-secondary">No timeline entries yet.</p>}
            </section>

            <section aria-labelledby="issues-heading" className="min-w-0 rounded-xl border bg-card shadow-level-1">
              <div className="flex items-center justify-between gap-3 border-b px-5 py-4">
                <h2 id="issues-heading" className="text-title-md">Related issues</h2>
                {incident.relatedIssues.length > 0 && (
                  <span className="text-label-md tabular-nums text-text-secondary">{incident.relatedIssues.length}</span>
                )}
              </div>
              {incident.relatedIssues.length ? (
                <ul className="divide-y divide-border">
                  {incident.relatedIssues.map((issue) => (
                    <li key={issue.issueId} className="last:[&>a]:rounded-b-xl">
                      <Link
                        href={projectHref + "/issues/" + issue.issueId}
                        className="group flex items-start justify-between gap-3 px-5 py-3 transition-colors hover:bg-canvas focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                      >
                        <span className="min-w-0 space-y-1">
                          <span className="block break-words text-body-sm font-medium group-hover:text-primary">{issue.issueTitle ?? issue.issueId}</span>
                          {issue.errorType && <span className="block break-words font-mono text-label-sm text-text-secondary">{issue.errorType}</span>}
                          {issue.occurrenceCount !== null && (
                            <span className="block text-label-sm tabular-nums text-text-secondary">
                              {issue.occurrenceCount.toLocaleString()} {issue.occurrenceCount === 1 ? "event" : "events"} at link time
                            </span>
                          )}
                        </span>
                        <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-text-muted group-hover:text-primary" aria-hidden="true" />
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : <p className="px-5 py-5 text-body-sm text-text-secondary">No related issues linked.</p>}
            </section>
          </div>

          {transition && (
            <StatusChangeModal
              transition={transition}
              pending={statusUpdate.isPending}
              error={statusError}
              onCancel={() => setConfirmation(undefined)}
              onConfirm={(note) => {
                if (!statusUpdate.isPending) statusUpdate.mutate({ id: incident.id, projectId, transition, note });
              }}
            />
          )}
        </>
      )}
    </div>
  );
}
