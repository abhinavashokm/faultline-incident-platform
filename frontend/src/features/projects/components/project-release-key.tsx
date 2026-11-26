"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { createReleaseKeyApi, getReleaseKeyApi, rotateReleaseKeyApi } from "../api";

// The Control Plane adds an 11-character prefix to 43 URL-safe characters.
const RELEASE_TOKEN_LENGTH = 54;

export function ProjectReleaseKey({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const queryKey = ["project-release-key-prefix", projectId];
  const status = useQuery({
    queryKey,
    queryFn: ({ signal }) => getReleaseKeyApi(projectId, signal),
  });
  const [confirming, setConfirming] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);
  const [copyStatus, setCopyStatus] = useState("");
  const keyPrefix = status.data?.keyPrefix;

  async function save(rotate: boolean) {
    setPending(true);
    setFailed(false);
    try {
      const result = await (rotate ? rotateReleaseKeyApi(projectId) : createReleaseKeyApi(projectId));
      await queryClient.cancelQueries({ queryKey, exact: true });
      queryClient.setQueryData(queryKey, { keyPrefix: result.keyPrefix });
      setToken(result.token);
      setConfirming(false);
    } catch {
      setFailed(true);
      void status.refetch();
    } finally {
      setPending(false);
    }
  }

  async function copy() {
    if (!token) return;
    try {
      await navigator.clipboard.writeText(token);
      setCopyStatus("Release key copied.");
    } catch {
      setCopyStatus("Clipboard unavailable. Select and copy the key manually.");
    }
  }

  return (
    <section aria-labelledby="release-keys-heading" className="space-y-3 border-t border-border px-6 py-5">
      <h2 id="release-keys-heading" className="text-label-md font-semibold">Release API keys</h2>
      {token && (
        <p className="text-body-sm text-text-secondary">
          Save this key as the <code>FAULTLINE_RELEASE_TOKEN</code> secret in your CI provider.
          This is the only time Faultline displays the full key.
        </p>
      )}
      {(token || keyPrefix) && (
        <code className="block select-all break-all rounded-md border border-border bg-canvas px-3 py-2 font-mono text-body-sm">
          {token ?? (
            <>
              <span className="sr-only">Active release key prefix </span>
              {keyPrefix}
              <span aria-hidden="true">{"*".repeat(Math.max(0, RELEASE_TOKEN_LENGTH - (keyPrefix?.length ?? 0)))}</span>
            </>
          )}
        </code>
      )}
      {token ? (
        <>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" size="sm" onClick={() => void copy()}>
              Copy release key
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => {
              setToken(null);
              setCopyStatus("");
            }}>
              Done
            </Button>
          </div>
          <p role="status" className="text-body-sm text-text-secondary">{copyStatus}</p>
        </>
      ) : status.isPending ? (
        <p role="status" className="text-body-sm text-text-secondary">Loading release key…</p>
      ) : status.isError ? (
        <div className="flex flex-wrap items-center gap-3">
          <p role="alert" className="text-body-sm text-error">Couldn’t load the active release key.</p>
          <Button type="button" variant="secondary" size="sm" onClick={() => void status.refetch()}>
            Try again
          </Button>
        </div>
      ) : keyPrefix ? (
        <Button type="button" variant="outline" size="sm" disabled={pending} onClick={() => {
          setFailed(false);
          setConfirming(true);
        }}>
          Rotate release key
        </Button>
      ) : (
        <Button type="button" variant="secondary" size="sm" disabled={pending} onClick={() => void save(false)}>
          {pending ? "Generating…" : "Generate release key"}
        </Button>
      )}
      {failed && !confirming && <p role="alert" className="text-body-sm text-error">Couldn’t generate a release key.</p>}
      {confirming && (
        <ConfirmationDialog
          title="Rotate release key?"
          confirmLabel={pending ? "Rotating…" : "Rotate release key"}
          pending={pending}
          onCancel={() => {
            setConfirming(false);
            setFailed(false);
          }}
          onConfirm={() => void save(true)}
        >
          <p>Rotation revokes previous release keys. Update your CI secret with the replacement.</p>
          {failed && <p role="alert" className="mt-3 text-error">Couldn’t rotate the release key.</p>}
        </ConfirmationDialog>
      )}
    </section>
  );
}
