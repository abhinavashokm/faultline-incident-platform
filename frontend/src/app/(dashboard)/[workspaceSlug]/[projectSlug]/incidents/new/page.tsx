"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Bug, ClipboardList } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/use-toast";
import { createIncident, incidentsQueryKey, type IncidentSeverity } from "@/features/incidents/api";
import { IssuePicker } from "@/features/incidents/issue-picker";
import type { IssueListItem } from "@/features/issues/types";
import { useProjectBySlug } from "@/features/projects/hooks";

const severities: { value: IncidentSeverity; label: string; description: string }[] = [
  { value: "critical", label: "P0 · Critical", description: "Widespread outage or data loss" },
  { value: "high", label: "P1 · High", description: "Core functionality severely degraded" },
  { value: "medium", label: "P2 · Medium", description: "Limited impact or localized errors" },
  { value: "low", label: "P3 · Low", description: "Minor impact or background failure" },
];

export default function CreateIncidentPage({
  params,
}: {
  params: { workspaceSlug: string; projectSlug: string };
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const listHref = `/${params.workspaceSlug}/${params.projectSlug}/incidents`;
  const { project, isLoading, isError } = useProjectBySlug(params.projectSlug);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState<IncidentSeverity>("medium");
  const [description, setDescription] = useState("");
  const [issueSelection, setIssueSelection] = useState<{ projectId: string; issues: IssueListItem[] }>();
  const selectedIssues = issueSelection && issueSelection.projectId === project?.id
    ? issueSelection.issues
    : [];

  const creation = useMutation({
    mutationFn: (projectId: string) =>
      createIncident(projectId, {
        title: title.trim(),
        severity,
        description: description.trim() || undefined,
        relatedIssueIds: selectedIssues.length ? selectedIssues.map((issue) => issue.id) : undefined,
      }),
    retry: false,
    onSuccess: (incident, projectId) => {
      void queryClient.invalidateQueries({ queryKey: incidentsQueryKey(projectId) });
      toast({ title: "Incident created", description: incident.title, variant: "success" });
      router.replace(listHref);
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (project?.status === "active" && title.trim() && !creation.isPending && !creation.isSuccess) {
      creation.mutate(project.id);
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <header className="space-y-2">
        <Button variant="ghost" size="sm" className="-ml-2 gap-2" asChild>
          <Link href={listHref}>
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to Incidents
          </Link>
        </Button>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Create incident
        </h1>
        <p className="text-sm text-muted-foreground">Record an incident and link the telemetry issues involved.</p>
      </header>

      {isLoading ? (
        <p role="status" className="text-sm text-muted-foreground">Loading project…</p>
      ) : isError ? (
        <p role="alert" className="text-sm text-error">Couldn’t load the project.</p>
      ) : project?.status !== "active" ? (
        <p role="alert" className="text-sm text-error">This project is unavailable for incident creation.</p>
      ) : (
        <form onSubmit={handleSubmit}>
          <fieldset disabled={creation.isPending || creation.isSuccess} className="min-w-0 space-y-6">
            <section aria-labelledby="incident-overview" className="overflow-hidden rounded-xl border bg-card shadow-level-1">
              <header className="flex items-center gap-3 border-b bg-canvas px-4 py-4 sm:px-6">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary-tint text-primary">
                  <ClipboardList className="h-5 w-5" aria-hidden="true" />
                </span>
                <h2 id="incident-overview" className="text-headline-sm">Incident overview</h2>
              </header>
              <div className="space-y-5 p-4 sm:p-6">
                <div className="space-y-2">
                  <Label htmlFor="incident-title">Incident title <span className="text-error" aria-hidden="true">*</span></Label>
                  <Input
                    id="incident-title"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder="e.g. Payment processing failures after deployment"
                    maxLength={255}
                    required
                    className="bg-canvas"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="incident-description">Description <span className="text-muted-foreground">(optional)</span></Label>
                  <textarea
                    id="incident-description"
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder="Describe the symptoms, impact, or recent changes."
                    rows={4}
                    className="block w-full rounded-control border border-border bg-canvas px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </div>
                <fieldset className="min-w-0">
                  <legend className="mb-2 text-sm font-medium">Severity</legend>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {severities.map(({ value, label, description }) => (
                      <label key={value} className="relative flex cursor-pointer">
                        <input
                          type="radio"
                          name="severity"
                          value={value}
                          checked={severity === value}
                          onChange={() => setSeverity(value)}
                          className="peer absolute left-3 top-3.5 h-4 w-4 accent-primary"
                        />
                        <span className="w-full rounded-lg border bg-canvas py-3 pl-9 pr-3 text-sm font-medium hover:border-border-hover peer-checked:border-primary peer-checked:bg-primary-tint peer-focus-visible:ring-2 peer-focus-visible:ring-ring">
                          <span className="block">{label}</span>
                          <span className="mt-1 block text-xs font-normal text-muted-foreground">{description}</span>
                        </span>
                      </label>
                    ))}
                  </div>
                </fieldset>
              </div>
            </section>
            <section aria-labelledby="incident-issues" className="overflow-hidden rounded-xl border bg-card shadow-level-1">
              <header className="flex items-start gap-3 border-b bg-canvas px-4 py-4 sm:px-6">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-ai-container text-ai-foreground">
                  <Bug className="h-5 w-5" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-2">
                    <h2 id="incident-issues" className="text-headline-sm">Link telemetry issues</h2>
                    <span className="text-xs text-muted-foreground">Optional</span>
                  </div>
                  <p className="text-sm text-muted-foreground">Select related issues from this project.</p>
                </div>
                <span aria-live="polite" className="shrink-0 pt-1 text-xs font-medium text-muted-foreground">
                  {selectedIssues.length} selected
                </span>
              </header>
              <div className="p-4 sm:p-6">
                <IssuePicker
                  key={project.id}
                  projectId={project.id}
                  selected={selectedIssues}
                  onChange={(issues) => setIssueSelection({ projectId: project.id, issues })}
                />
              </div>
            </section>
            <footer className="flex flex-wrap items-center justify-end gap-3 rounded-xl border bg-card p-4 shadow-level-1">
              {creation.isError && (
                <p role="alert" className="mr-auto text-sm text-error">
                  {creation.error instanceof Error ? creation.error.message : "Couldn’t create the incident."}
                </p>
              )}
              <Button variant="outline" asChild><Link href={listHref}>Cancel</Link></Button>
              <Button type="submit" disabled={!title.trim()}>
                {creation.isPending ? "Creating incident…" : "Create incident"}
              </Button>
            </footer>
          </fieldset>
        </form>
      )}
    </div>
  );
}
