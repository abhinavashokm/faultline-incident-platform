"use client";

import { useState } from "react";
import { Eye, EyeOff, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/use-toast";
import { useProjectApiKey, useRotateProjectApiKey } from "../hooks";

export function ProjectDsn({ projectId, canRotate }: { projectId: string; canRotate: boolean }) {
  const [revealed, setRevealed] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const apiKey = useProjectApiKey(projectId);
  const rotation = useRotateProjectApiKey(projectId);
  const dsn = apiKey.data?.dsn;
  const maskedDsn = dsn?.match(/^(\w[\w+.-]*:\/\/)[^@]+@([^@]+)$/);

  function confirmRotation() {
    if (!canRotate || rotation.isPending) return;
    rotation.mutate(undefined, {
      onSuccess: () => {
        setRevealed(false);
        setConfirming(false);
        toast({
          title: "Ingestion DSN rotated",
          description: "Update your SDK configuration with the new DSN.",
          variant: "success",
        });
      },
    });
  }

  return (
    <section aria-labelledby="ingestion-dsn-heading" className="space-y-3 border-t border-border px-6 py-5">
      <h2 id="ingestion-dsn-heading" className="text-label-md font-semibold">Ingestion DSN</h2>
      {apiKey.isPending ? (
        <div role="status">
          <span className="sr-only">Loading ingestion DSN…</span>
          <Skeleton aria-hidden="true" className="h-9 rounded-md" />
        </div>
      ) : apiKey.isError ? (
        <div className="flex flex-wrap items-center gap-3">
          <p role="alert" className="text-body-sm text-text-secondary">Couldn’t load the ingestion DSN.</p>
          <Button variant="secondary" size="sm" disabled={apiKey.isFetching} onClick={() => void apiKey.refetch()}>
            Try again
          </Button>
        </div>
      ) : dsn ? (
        <code className="block break-all rounded-md border border-border bg-canvas px-3 py-2 font-mono text-body-sm text-text-primary">
          {revealed ? dsn : maskedDsn ? `${maskedDsn[1]}••••••••@${maskedDsn[2]}` : "••••••••"}
        </code>
      ) : (
        <p className="text-body-sm text-text-secondary">No active ingestion DSN.</p>
      )}
      <div className="flex flex-wrap gap-2">
        {dsn && !apiKey.isError && (
          <Button type="button" variant="secondary" size="sm" className="gap-2" onClick={() => setRevealed(!revealed)}>
            {revealed ? <EyeOff aria-hidden="true" className="h-4 w-4" /> : <Eye aria-hidden="true" className="h-4 w-4" />}
            {revealed ? "Hide DSN" : "Reveal DSN"}
          </Button>
        )}
        {canRotate && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-2"
            disabled={apiKey.isPending || rotation.isPending}
            onClick={() => {
              rotation.reset();
              setConfirming(true);
            }}
          >
            <RefreshCw aria-hidden="true" className="h-4 w-4" />
            Rotate DSN
          </Button>
        )}
      </div>
      {confirming && canRotate && (
        <ConfirmationDialog
          title="Rotate ingestion DSN?"
          confirmLabel={rotation.isPending ? "Rotating…" : "Rotate DSN"}
          pending={rotation.isPending}
          onCancel={() => setConfirming(false)}
          onConfirm={confirmRotation}
        >
          <p>
            Rotation replaces the current DSN. The old DSN stops working once the ingestion cache expires.
            Update every application using it with the new DSN to avoid interrupting event ingestion.
          </p>
          {rotation.isError && <p role="alert" className="mt-3 text-error">{rotation.error.message}</p>}
        </ConfirmationDialog>
      )}
    </section>
  );
}
