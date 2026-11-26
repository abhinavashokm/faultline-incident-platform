"use client";

import { useId, useState } from "react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { Label } from "@/components/ui/label";
import type { StatusTransition } from "@/features/incidents/status";

export function StatusBadge({ status, variant }: { status: string; variant: BadgeProps["variant"] }) {
  return (
    <Badge variant={variant}>
      <span className="sr-only">Incident status: </span>
      {status.replaceAll("_", " ")}
    </Badge>
  );
}

export function StatusActionButton({ transition, onClick }: {
  transition: StatusTransition;
  onClick: () => void;
}) {
  return (
    <Button type="button" size="sm" aria-label={transition.label} onClick={onClick}>
      {transition.label}
    </Button>
  );
}

export function StatusChangeModal({ transition, pending, error, onCancel, onConfirm }: {
  transition: StatusTransition;
  pending: boolean;
  error?: string;
  onCancel: () => void;
  onConfirm: (note?: string) => void;
}) {
  const id = useId();
  const [note, setNote] = useState("");

  return (
    <ConfirmationDialog
      title={transition.title}
      confirmLabel={pending ? "Updating…" : "Confirm"}
      confirmVariant="primary"
      pending={pending}
      onCancel={onCancel}
      onConfirm={() => onConfirm(note.trim() || undefined)}
    >
      <div className="space-y-2">
        <Label htmlFor={id}>Timeline note <span className="text-muted-foreground">(optional)</span></Label>
        <textarea
          id={id}
          rows={3}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          disabled={pending}
          className="block w-full rounded-control border bg-canvas px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
        />
      </div>
      {error && <p role="alert" className="mt-3 text-sm text-error">{error}</p>}
    </ConfirmationDialog>
  );
}
