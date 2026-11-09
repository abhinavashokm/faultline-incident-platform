"use client";

import React, { useState } from "react";
import { Copy, Check, ChevronDown, ChevronRight, Terminal } from "lucide-react";

interface EventMetadataProps {
  environment?: string | null;
  release?: string | null;
  userHash?: string | null;
  fingerprint?: string | null;
}

export function EventMetadata({
  environment,
  release,
  userHash,
  fingerprint,
}: EventMetadataProps) {
  const [copiedFingerprint, setCopiedFingerprint] = useState(false);
  const [isDebugOpen, setIsDebugOpen] = useState(false);

  const hasEnvOrRelease = Boolean(environment || release);
  const hasUser = Boolean(userHash);
  const hasDebug = Boolean(fingerprint);

  if (!hasEnvOrRelease && !hasUser && !hasDebug) {
    return null;
  }

  const handleCopyFingerprint = () => {
    if (!fingerprint) return;
    navigator.clipboard.writeText(fingerprint);
    setCopiedFingerprint(true);
    setTimeout(() => setCopiedFingerprint(false), 2000);
  };

  return (
    <div className="space-y-4">
      {/* Environment, Release & User Tags */}
      {(hasEnvOrRelease || hasUser) && (
        <div className="rounded-lg border border-border bg-card p-4 shadow-level-1 grid grid-cols-1 sm:grid-cols-3 gap-4 text-label-md">
          {environment && (
            <div className="space-y-0.5">
              <span className="text-text-muted text-[11px] uppercase tracking-wider block font-medium">
                Environment
              </span>
              <span className="font-mono text-body-sm text-text-primary">
                {environment}
              </span>
            </div>
          )}

          {release && (
            <div className="space-y-0.5">
              <span className="text-text-muted text-[11px] uppercase tracking-wider block font-medium">
                Release
              </span>
              <span className="font-mono text-body-sm text-text-primary truncate block" title={release}>
                {release}
              </span>
            </div>
          )}

          {userHash && (
            <div className="space-y-0.5">
              <span className="text-text-muted text-[11px] uppercase tracking-wider block font-medium">
                Anonymous User ID
              </span>
              <span className="font-mono text-body-sm text-text-primary truncate block" title={userHash}>
                {userHash}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Debug Fingerprint (Collapsed by default) */}
      {hasDebug && (
        <div className="rounded-lg border border-border bg-card shadow-level-1 overflow-hidden">
          <button
            type="button"
            onClick={() => setIsDebugOpen(!isDebugOpen)}
            className="w-full px-4 py-2.5 bg-canvas/40 flex items-center justify-between text-label-sm font-semibold text-text-secondary hover:text-text-primary transition-colors text-left"
          >
            <div className="flex items-center gap-2">
              <Terminal className="h-3.5 w-3.5 text-text-muted" />
              <span>Debug Information</span>
            </div>
            {isDebugOpen ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>

          {isDebugOpen && (
            <div className="p-4 border-t border-border bg-canvas/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[12px] font-mono">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-text-muted">Fingerprint:</span>
                <code className="bg-card px-2 py-1 rounded border border-border text-text-primary truncate max-w-sm sm:max-w-md">
                  {fingerprint}
                </code>
              </div>
              <button
                type="button"
                onClick={handleCopyFingerprint}
                className="flex items-center gap-1.5 text-primary hover:underline shrink-0 text-label-sm"
              >
                {copiedFingerprint ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-success" />
                    <span className="text-success">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy Fingerprint</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
