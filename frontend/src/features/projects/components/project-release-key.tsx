"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { createReleaseKeyApi } from "../api";

export function ProjectReleaseKey({ projectId }: { projectId: string }) {
  const [token, setToken] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);
  const [copyStatus, setCopyStatus] = useState("");

  async function generate() {
    setPending(true);
    setFailed(false);
    try {
      const result = await createReleaseKeyApi(projectId);
      setToken(result.token);
    } catch {
      setFailed(true);
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
      {token ? (
        <>
          <p className="text-body-sm text-text-secondary">
            Save this key as the <code>FAULTLINE_RELEASE_TOKEN</code> secret in your CI provider.
            This is the only time Faultline displays the full key.
          </p>
          <code className="block select-all break-all rounded-md border border-border bg-canvas px-3 py-2 font-mono text-body-sm">
            {token}
          </code>
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
      ) : (
        <Button type="button" variant="secondary" size="sm" disabled={pending} onClick={() => void generate()}>
          {pending ? "Generating…" : "Generate release key"}
        </Button>
      )}
      {failed && <p role="alert" className="text-body-sm text-error">Couldn’t generate a release key.</p>}
    </section>
  );
}
