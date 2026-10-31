"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Copy,
  Check,
  Eye,
  EyeOff,
  ArrowRight,
  Loader2,
  Terminal,
  KeyRound,
  CheckCircle2,
} from "lucide-react";

import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSdkConfig, useLiveEventStatus } from "@/features/projects/hooks";
import { PlatformId } from "@/features/projects/types";

function InstallSdkContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const projectName = searchParams.get("name") || "Payments API";
  const initialPlatform = (searchParams.get("platform") as PlatformId) || "python";
  const projectId = searchParams.get("projectId") || "proj_9a82f1b4";

  const [activePlatform, setActivePlatform] = useState<PlatformId>(initialPlatform);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);
  const [showKey, setShowKey] = useState<boolean>(false);

  const { data: config, isLoading } = useSdkConfig(activePlatform);
  useLiveEventStatus(projectId);

  const handleCopy = (text: string, section: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(section);
    setTimeout(() => {
      setCopiedSection((curr) => (curr === section ? null : curr));
    }, 2000);
  };

  const handleFinish = () => {
    router.push("/acme-cloud/overview");
  };

  return (
    <div className="min-h-screen bg-canvas flex flex-col justify-between">
      {/* Top Header */}
      <header className="border-b border-border bg-card px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <Logo size={26} />

          {/* Stepper */}
          <div className="hidden sm:flex items-center gap-3 text-label-sm">
            <div className="flex items-center gap-1.5 text-success">
              <CheckCircle2 className="h-4 w-4" />
              <span>Workspace configured</span>
            </div>
            <span className="text-border">•</span>
            <div className="flex items-center gap-1.5 text-success">
              <CheckCircle2 className="h-4 w-4" />
              <span>Project created</span>
            </div>
            <span className="text-border">•</span>
            <div className="flex items-center gap-1.5 font-medium text-text-primary">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[11px] font-mono text-primary-foreground">
                2
              </span>
              <span>Install SDK</span>
            </div>
          </div>

          <div className="text-label-sm text-text-secondary font-mono">
            Acme Cloud
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 sm:py-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <div className="inline-flex items-center gap-2 mb-1.5">
              <span className="text-label-sm font-mono px-2 py-0.5 rounded bg-card border border-border text-text-secondary">
                {projectName}
              </span>
              <span className="text-border">•</span>
              <span className="text-label-sm font-mono text-text-muted">production</span>
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
        <div className="mb-6 rounded-lg border border-border bg-card p-4 shadow-level-1 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="relative flex h-3 w-3 items-center justify-center">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-warning opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-warning"></span>
            </div>
            <div>
              <div className="text-body-sm font-medium text-text-primary">
                Waiting for first event...
              </div>
              <p className="text-[11px] text-text-secondary">
                The ingestion daemon is listening on <code className="font-mono text-[11px] bg-canvas px-1 rounded">ingest.faultline.io</code>. Send an error or run your app to test.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-label-sm font-mono text-text-muted">
              Auto-refreshing
            </span>
          </div>
        </div>

        {/* Credentials Card: DSN & API Key */}
        <div className="rounded-lg border border-border bg-card p-5 mb-6 shadow-level-1 space-y-4">
          <div className="flex items-center gap-2 text-body-sm font-semibold text-text-primary">
            <KeyRound className="h-4 w-4 text-primary" />
            <span>Project Ingestion Credentials</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* DSN */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-label-sm">
                <span className="text-text-secondary font-medium">Project DSN</span>
                <span className="text-text-muted text-[11px]">Client-safe</span>
              </div>
              <div className="flex items-center gap-2 rounded-md border border-border bg-canvas px-3 py-2">
                <code className="flex-1 font-mono text-[12px] text-text-primary truncate">
                  {config?.dsn || "https://fl_pub_9a82f1b4@ingest.faultline.io/42019"}
                </code>
                <button
                  type="button"
                  onClick={() => handleCopy(config?.dsn || "", "dsn")}
                  className="text-text-secondary hover:text-text-primary p-1 rounded hover:bg-card transition-colors"
                  aria-label="Copy DSN"
                >
                  {copiedSection === "dsn" ? (
                    <Check className="h-3.5 w-3.5 text-success" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>

            {/* Secret API Key */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-label-sm">
                <span className="text-text-secondary font-medium">Secret Key (Ingest Token)</span>
                <span className="text-text-muted text-[11px]">Server-only</span>
              </div>
              <div className="flex items-center gap-2 rounded-md border border-border bg-canvas px-3 py-2">
                <code className="flex-1 font-mono text-[12px] text-text-primary truncate">
                  {showKey
                    ? config?.apiKey || "fl_sec_9a82f1b4892cfa7eb40"
                    : "fl_sec_••••••••••••••••••••"}
                </code>
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="text-text-secondary hover:text-text-primary p-1 rounded hover:bg-card transition-colors"
                  aria-label={showKey ? "Hide key" : "Show key"}
                >
                  {showKey ? (
                    <EyeOff className="h-3.5 w-3.5" />
                  ) : (
                    <Eye className="h-3.5 w-3.5" />
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => handleCopy(config?.apiKey || "", "key")}
                  className="text-text-secondary hover:text-text-primary p-1 rounded hover:bg-card transition-colors"
                  aria-label="Copy API Key"
                >
                  {copiedSection === "key" ? (
                    <Check className="h-3.5 w-3.5 text-success" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Instructions by Platform */}
        <div className="rounded-lg border border-border bg-card p-6 shadow-level-1">
          <div className="mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-headline-sm font-semibold text-text-primary">
                SDK Installation &amp; Configuration
              </h2>
              <p className="text-body-sm text-text-secondary">
                Select your language or runtime to view the setup instructions.
              </p>
            </div>
          </div>

          <Tabs
            defaultValue={activePlatform}
            onValueChange={(val) => setActivePlatform(val as PlatformId)}
          >
            <TabsList className="mb-6 flex flex-wrap h-auto gap-1">
              <TabsTrigger value="python">Python</TabsTrigger>
              <TabsTrigger value="javascript">JavaScript / React</TabsTrigger>
              <TabsTrigger value="node">Node.js</TabsTrigger>
              <TabsTrigger value="java">Java / Spring</TabsTrigger>
              <TabsTrigger value="go">Go</TabsTrigger>
              <TabsTrigger value="other">OpenTelemetry</TabsTrigger>
            </TabsList>

            {isLoading ? (
              <div className="flex items-center justify-center py-12 text-text-muted">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : (
              <div className="space-y-6">
                {/* Step 1: Package Install */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-body-sm font-semibold text-text-primary">
                      1. Install package
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(config?.installCommand || "", "install")}
                      className="inline-flex items-center gap-1.5 text-label-sm text-text-secondary hover:text-text-primary font-medium"
                    >
                      {copiedSection === "install" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-success" />
                          <span>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          <span>Copy command</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div className="rounded-md border border-border bg-canvas p-3 font-mono text-[12px] text-text-primary flex items-center justify-between overflow-x-auto">
                    <code>{config?.installCommand}</code>
                  </div>
                </div>

                {/* Step 2: Initialize */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-body-sm font-semibold text-text-primary">
                      2. Initialize SDK in application code
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(config?.initSnippet || "", "init")}
                      className="inline-flex items-center gap-1.5 text-label-sm text-text-secondary hover:text-text-primary font-medium"
                    >
                      {copiedSection === "init" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-success" />
                          <span>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          <span>Copy snippet</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div className="rounded-md border border-border bg-canvas p-4 font-mono text-[12px] text-text-primary overflow-x-auto whitespace-pre">
                    <code>{config?.initSnippet}</code>
                  </div>
                </div>

                {/* Step 3: Environment Credentials */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-body-sm font-semibold text-text-primary">
                      3. (Optional) Set environment variables
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(config?.envSnippet || "", "env")}
                      className="inline-flex items-center gap-1.5 text-label-sm text-text-secondary hover:text-text-primary font-medium"
                    >
                      {copiedSection === "env" ? (
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
                  <div className="rounded-md border border-border bg-canvas p-3 font-mono text-[12px] text-text-primary overflow-x-auto">
                    <code>{config?.envSnippet}</code>
                  </div>
                </div>
              </div>
            )}
          </Tabs>

          <div className="mt-8 pt-4 border-t border-border flex items-center justify-between">
            <Link
              href="/onboarding/create-project"
              className="text-body-sm text-text-secondary hover:text-text-primary"
            >
              ← Back to project setup
            </Link>

            <Button onClick={handleFinish} className="gap-2">
              <span>Go to Overview Dashboard</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card py-3 px-6 text-center text-label-sm text-text-muted">
        Faultline SDK Ingestion Gateway • End-to-End Tracing
      </footer>
    </div>
  );
}

export default function InstallSdkPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-canvas">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <InstallSdkContent />
    </Suspense>
  );
}
