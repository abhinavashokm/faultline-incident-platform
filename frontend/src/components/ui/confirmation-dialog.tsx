"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

type ConfirmationDialogProps = {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  pending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ConfirmationDialog({
  title, children, confirmLabel, pending, onCancel, onConfirm,
}: ConfirmationDialogProps) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);

  return (
    <dialog
      ref={dialog}
      aria-busy={pending}
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      onCancel={(event) => {
        event.preventDefault();
        if (!pending) onCancel();
      }}
      className="fixed inset-auto left-1/2 top-1/2 m-0 -translate-x-1/2 -translate-y-1/2 max-h-[calc(100dvh-2rem)] w-11/12 max-w-md overflow-y-auto rounded-2xl border bg-card p-6 text-card-foreground shadow-2xl backdrop:bg-black/50"
    >
      <h2 id={titleId} className="text-lg font-semibold">{title}</h2>
      <div id={descriptionId} className="mt-3 text-sm text-muted-foreground">{children}</div>
      <div className="mt-5 flex justify-end gap-3">
        <Button type="button" variant="outline" autoFocus disabled={pending} onClick={onCancel}>
          Cancel
        </Button>
        <Button type="button" variant="destructive" disabled={pending} onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </dialog>
  );
}
