"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/use-toast";
import { createIncident, incidentsQueryKey } from "@/features/incidents/api";
import { IncidentForm, type IncidentFormValues } from "@/features/incidents/incident-form";
import { useProjectBySlug } from "@/features/projects/hooks";

export default function CreateIncidentPage({
  params,
}: {
  params: { workspaceSlug: string; projectSlug: string };
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const listHref = `/${params.workspaceSlug}/${params.projectSlug}/incidents`;
  const { project, isLoading, isError } = useProjectBySlug(params.projectSlug);
  const creation = useMutation({
    mutationFn: ({ projectId, values }: { projectId: string; values: IncidentFormValues }) =>
      createIncident(projectId, { ...values, description: values.description.trim() || undefined }),
    retry: false,
    onSuccess: (incident, { projectId }) => {
      void queryClient.invalidateQueries({ queryKey: incidentsQueryKey(projectId) });
      toast({ title: "Incident created", description: incident.title, variant: "success" });
      router.replace(`${listHref}/${incident.id}`);
    },
  });

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
        <IncidentForm
          key={project.id}
          projectId={project.id}
          cancelHref={listHref}
          submitLabel={creation.isPending ? "Creating incident…" : "Create incident"}
          disabled={creation.isPending || creation.isSuccess}
          error={creation.error?.message}
          onSubmit={(values) => creation.mutate({ projectId: project.id, values })}
        />
      )}
    </div>
  );
}
