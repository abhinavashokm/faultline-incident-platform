"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Props = {
  secret: string;
  onClose: () => void;
};

export function WebhookSigningSecretDialog({ secret, onClose }: Props) {
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");

  async function copySecret() {
    try {
      await navigator.clipboard.writeText(secret);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("failed");
    }
  }

  return (
    <Dialog.Root open onOpenChange={(open) => { if (!open) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm animate-in fade-in-50" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-border bg-card shadow-2xl animate-in zoom-in-95">
          <div className="space-y-1 border-b border-border px-6 py-5">
            <Dialog.Title className="text-lg font-semibold text-foreground">
              Save your signing secret
            </Dialog.Title>
            <Dialog.Description className="text-sm text-muted-foreground">
              This secret is shown only once. Use it to verify the X-Faultline-Signature header.
            </Dialog.Description>
          </div>
          <div className="space-y-4 p-6">
            <div className="flex gap-2">
              <Input aria-label="Signing secret" className="min-w-0 font-mono" value={secret} readOnly />
              <Button type="button" variant="outline" onClick={copySecret}>
                {copyStatus === "copied" ? "Copied" : "Copy"}
              </Button>
            </div>
            <div className="sr-only" role="status">{copyStatus === "copied" && "Copied"}</div>
            {copyStatus === "failed" && (
              <p className="text-xs text-error" role="alert">Copy failed. Select the secret and copy it manually.</p>
            )}
          </div>
          <div className="flex justify-end border-t border-border bg-muted/30 px-6 py-4">
            <Dialog.Close asChild>
              <Button type="button">I've saved it</Button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
