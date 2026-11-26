"use client";

import { skipToken, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/use-toast";
import { getIncident, incidentsQueryKey, updateIncidentDetails } from "@/features/incidents/api";
import { IncidentForm, type IncidentFormValues } from "@/features/incidents/incident-form";
import { useProjectBySlug } from "@/features/projects/hooks";
import { ApiError } from "@/lib/api-client";

type Incident = Awaited<ReturnType<typeof getIncident>>;

function IncidentEditForm({ incident, projectId, detailHref }: {
  incident: Incident;
  projectId: string;
  detailHref: string;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const save = useMutation({
    mutationFn: (values: IncidentFormValues) => updateIncidentDetails(projectId, incident.id, {
      ...values,
      description: values.description || null,
    }),
    retry: false,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: incidentsQueryKey(projectId), exact: true }),
        queryClient.invalidateQueries({ queryKey: ["incident-detail", projectId, incident.id], exact: true }),
      ]);
      toast({ title: "Incident updated", variant: "success" });
      router.replace(detailHref);
    },
  });

  return (
    <IncidentForm
      projectId={projectId}
      initialValues={{
        title: incident.title,
        severity: incident.severity,
        description: incident.description,
        relatedIssues: incident.relatedIssues.map((issue) => ({
          id: issue.issueId,
          title: issue.issueTitle ?? issue.issueId,
        })),
      }}
      cancelHref={detailHref}
      submitLabel={save.isPending ? "Saving…" : "Save changes"}
      disabled={save.isPending || save.isSuccess}
      error={save.error?.message}
      onSubmit={save.mutate}
    />
  );
}

export default function EditIncidentPage({
  params,
}: {
  params: { workspaceSlug: string; projectSlug: string; incidentId: string };
}) {
  const { workspaceSlug, projectSlug, incidentId } = params;
  const detailHref = `/${workspaceSlug}/${projectSlug}/incidents/${incidentId}`;
  const projectQuery = useProjectBySlug(projectSlug);
  const projectId = projectQuery.project?.id;
  const detail = useQuery({
    queryKey: ["incident-detail", projectId, incidentId],
    queryFn: projectId ? ({ signal }) => getIncident(projectId, incidentId, signal) : skipToken,
    retry: (count, error) => count < 2 && !(error instanceof ApiError && error.status < 500),
  });
  const unavailable = detail.error instanceof ApiError && [403, 404].includes(detail.error.status);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <header className="space-y-2">
        <Button variant="ghost" size="sm" className="-ml-2 gap-2" asChild>
          <Link href={detailHref}><ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to incident</Link>
        </Button>
        <h1 className="text-3xl font-semibold tracking-tight">Edit incident</h1>
      </header>
      {projectQuery.isLoading || detail.isLoading ? (
        <p role="status" className="text-sm text-muted-foreground">Loading incident…</p>
      ) : projectQuery.isError || !projectId || unavailable || !detail.data ? (
        <div className="space-y-3 rounded-xl border bg-card p-5">
          <p role="alert" className="text-sm text-error">
            {projectQuery.isError ? "Couldn’t load the project." : !projectId ? "Project not found." : unavailable ? "Incident not found." : "Couldn’t load the incident."}
          </p>
          {!projectQuery.isError && detail.isError && !unavailable && (
            <Button variant="outline" size="sm" onClick={() => void detail.refetch()}>Try again</Button>
          )}
        </div>
      ) : (
        <IncidentEditForm key={`${projectId}/${incidentId}`} incident={detail.data} projectId={projectId} detailHref={detailHref} />
      )}
    </div>
  );
}
