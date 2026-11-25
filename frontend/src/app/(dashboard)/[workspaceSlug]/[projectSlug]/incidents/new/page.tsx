"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "@/components/ui/use-toast";
import { createIncident, incidentsQueryKey, type IncidentSeverity } from "@/features/incidents/api";
import { useProjectBySlug } from "@/features/projects/hooks";

const severities: { value: IncidentSeverity; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
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

  const creation = useMutation({
    mutationFn: (projectId: string) =>
      createIncident(projectId, {
        title: title.trim(),
        severity,
        description: description.trim() || undefined,
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
    <div className="mx-auto w-full max-w-3xl space-y-6 p-6">
      <header className="space-y-2 border-b pb-5">
        <Button variant="ghost" size="sm" className="-ml-2 gap-2" asChild>
          <Link href={listHref}>
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to Incidents
          </Link>
        </Button>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Create incident
        </h1>
      </header>

      {isLoading ? (
        <p role="status" className="text-sm text-muted-foreground">Loading project…</p>
      ) : isError ? (
        <p role="alert" className="text-sm text-error">Couldn’t load the project.</p>
      ) : project?.status !== "active" ? (
        <p role="alert" className="text-sm text-error">This project is unavailable for incident creation.</p>
      ) : (
        <form onSubmit={handleSubmit} className="rounded-lg border bg-card p-5 sm:p-6">
          <fieldset disabled={creation.isPending || creation.isSuccess} className="min-w-0 space-y-5">
            <div className="space-y-2">
              <Label htmlFor="incident-title">Title</Label>
              <Input
                id="incident-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={255}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="incident-severity">Severity</Label>
              <Select value={severity} onValueChange={(value: IncidentSeverity) => setSeverity(value)}
                disabled={creation.isPending || creation.isSuccess}>
                <SelectTrigger id="incident-severity">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {severities.map(({ value, label }) => (
                    <SelectItem key={value} value={value}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="incident-description">Description (optional)</Label>
              <textarea
                id="incident-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={5}
                className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
              />
            </div>
            {creation.isError && (
              <p role="alert" className="text-sm text-error">
                {creation.error instanceof Error ? creation.error.message : "Couldn’t create the incident."}
              </p>
            )}
            <div className="flex justify-end gap-2 border-t pt-4">
              <Button variant="outline" asChild><Link href={listHref}>Cancel</Link></Button>
              <Button type="submit" disabled={!title.trim()}>
                {creation.isPending ? "Creating incident…" : "Create incident"}
              </Button>
            </div>
          </fieldset>
        </form>
      )}
    </div>
  );
}
