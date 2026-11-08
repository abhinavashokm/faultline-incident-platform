"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Copy,
  Check,
  Eye,
  EyeOff,
  ArrowRight,
  Loader2,
  Terminal,
  KeyRound,
  ExternalLink,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Project } from "@/features/projects/types";
import { useProjectApiKey, useLiveEventStatus } from "@/features/projects/hooks";
import {
  getPlatformConfig,
  interpolateSnippets,
} from "@/features/projects/platform-registry";

interface ProjectSetupContentProps {
  project: Project;
  workspaceSlug: string;
}

export function ProjectSetupContent({ project, workspaceSlug }: ProjectSetupContentProps) {
  const router = useRouter();
  const [copiedSection, setCopiedSection] = useState<string | null>(null);
  const [showDsn, setShowDsn] = useState<boolean>(false);

  // Fetch the real DSN via GET /api/v1/projects/{id}/api-key
  const { data: apiKeyData, isLoading: isKeyLoading } = useProjectApiKey(project.id);
  useLiveEventStatus(project.id);

  const rawDsn = apiKeyData?.dsn || project.dsn || "";
  const platformConfig = getPlatformConfig(project.platform);
  const steps = interpolateSnippets(platformConfig.steps, rawDsn);

  const handleCopy = (text: string, section: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(section);
    setTimeout(() => {
      setCopiedSection((curr) => (curr === section ? null : curr));
    }, 2000);
  };

  const handleFinish = () => {
    router.push(`/${workspaceSlug}/overview`);
  };

  const maskedDsn = rawDsn
    ? rawDsn.replace(/:\/\/([^@]+)@/, "://••••••••@")
    : "https://••••••••@ingest.faultline.io/project";

  return (
    <div className="space-y-6">
      {/* Sub-header / Title Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 mb-1.5">
            <span className="text-label-sm font-mono px-2 py-0.5 rounded bg-card border border-border text-text-secondary">
              {project.name}
            </span>
            <span className="text-border">•</span>
            <span className="text-label-sm font-mono text-text-muted">
              {project.slug}
            </span>
            <span className="text-border">•</span>
            <span className="text-label-sm font-mono text-text-muted">
              {platformConfig.label}
            </span>
          </div>
          <h1 className="text-headline-md font-semibold text-text-primary">
            Connect your application
          </h1>
          <p className="text-body-sm text-text-secondary mt-0.5">
            Install the Faultline SDK to start capturing errors, performance regressions, and traces.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={handleFinish}
            className="text-body-sm"
          >
            Skip for now
          </Button>
          <Button
            onClick={handleFinish}
            className="gap-2 text-body-sm"
          >
            <span>Go to dashboard</span>
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Live Status Banner */}
      <div className="rounded-lg border border-border bg-card p-4 shadow-level-1 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="relative flex h-3 w-3 items-center justify-center">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-warning opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-warning"></span>
          </div>
          <div>
            <div className="text-body-sm font-medium text-text-primary">
              Waiting for first event...
            </div>
            <div className="text-label-sm text-text-secondary">
              The status updates automatically when your application triggers its first captured error or trace.
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 text-label-sm font-mono text-text-muted">
          <span>Polling stream</span>
        </div>
      </div>

      {/* Main Instruction Card */}
      <div className="bg-card rounded-lg border border-border p-6 sm:p-8 shadow-level-1">
        {/* Project Ingestion DSN Box */}
        <div className="mb-8 p-4 rounded-lg border border-border bg-canvas space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <KeyRound className="h-4 w-4 text-primary" />
              <span className="text-label-md font-semibold text-text-primary">
                Data Source Name (DSN)
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowDsn(!showDsn)}
                className="inline-flex items-center gap-1 text-label-sm text-text-secondary hover:text-text-primary"
              >
                {showDsn ? (
                  <>
                    <EyeOff className="h-3.5 w-3.5" />
                    <span>Hide</span>
                  </>
                ) : (
                  <>
                    <Eye className="h-3.5 w-3.5" />
                    <span>Reveal</span>
                  </>
                )}
              </button>

              <span className="text-border">|</span>

              <button
                type="button"
                onClick={() => handleCopy(rawDsn, "dsn")}
                disabled={!rawDsn}
                className="inline-flex items-center gap-1 text-label-sm text-text-secondary hover:text-text-primary"
              >
                {copiedSection === "dsn" ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-success" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy DSN</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="font-mono text-[12px] text-text-secondary break-all bg-card p-2.5 rounded border border-border">
            {isKeyLoading ? (
              <Skeleton className="h-4 w-3/4" />
            ) : showDsn ? (
              rawDsn || "No active DSN generated"
            ) : (
              maskedDsn
            )}
          </div>
          <p className="text-[11px] text-text-muted">
            The DSN informs the SDK where to send events and identifies this project at the ingestion gateway.
          </p>
        </div>

        {/* Dynamic Step-by-Step Snippets */}
        <div className="space-y-6">
          {steps.map((step, idx) => (
            <div key={idx} className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-body-sm font-semibold text-text-primary">
                    {step.title}
                  </span>
                  {step.description && (
                    <p className="text-[12px] text-text-secondary mt-0.5">
                      {step.description}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => handleCopy(step.code, `step-${idx}`)}
                  className="inline-flex items-center gap-1.5 text-label-sm text-text-secondary hover:text-text-primary font-medium"
                >
                  {copiedSection === `step-${idx}` ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-success" />
                      <span>Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
              <div className="rounded-md border border-border bg-canvas p-4 font-mono text-[12px] text-text-primary overflow-x-auto whitespace-pre">
                <code>{step.code}</code>
              </div>
            </div>
          ))}
        </div>

        {/* Card Footer Actions */}
        <div className="mt-8 pt-4 border-t border-border flex items-center justify-between">
          <Link
            href={`/${workspaceSlug}/projects/new`}
            className="text-body-sm text-text-secondary hover:text-text-primary"
          >
            ← Create another project
          </Link>

          <Button onClick={handleFinish} className="gap-2">
            <span>Go to Overview Dashboard</span>
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
