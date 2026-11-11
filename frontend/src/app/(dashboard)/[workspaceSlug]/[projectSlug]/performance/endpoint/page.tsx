"use client";

import React, { Suspense } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, Clock, Gauge, Layers } from "lucide-react";

function EndpointDetailStubContent() {
  const params = useParams();
  const searchParams = useSearchParams();

  const workspaceSlug = (params?.workspaceSlug as string) || "";
  const projectSlug = (params?.projectSlug as string) || "";

  const route = searchParams?.get("route") || "/unknown";
  const method = searchParams?.get("method") || "GET";

  const backUrl = `/${workspaceSlug}/${projectSlug}/performance`;

  return (
    <div className="min-h-full bg-background p-6">
      <div className="max-w-[1200px] mx-auto space-y-6">
        <div>
          <Link
            href={backUrl}
            className="inline-flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors mb-3 font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Performance Overview
          </Link>

          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 rounded text-xs font-mono font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
              {method}
            </span>
            <h1 className="text-xl font-bold font-mono text-text-primary tracking-tight">
              {route}
            </h1>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Endpoint performance detail view (stubbed for upcoming implementation).
          </p>
        </div>

        <div className="bg-card rounded-2xl border border-border p-8 text-center space-y-3 shadow-xs">
          <div className="w-12 h-12 mx-auto rounded-full bg-surface-container flex items-center justify-center text-primary">
            <Gauge className="w-6 h-6" />
          </div>
          <h2 className="text-base font-semibold text-text-primary">
            Endpoint Detail Page Coming Next
          </h2>
          <p className="text-xs text-text-secondary max-w-md mx-auto">
            This route accepts <code>route</code> and <code>method</code> as query parameters in compliance with the Faultline API contract. Detailed breakdown, latency histograms, and release comparisons will be rendered here.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function EndpointDetailStubPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 max-w-3xl mx-auto space-y-4 animate-pulse">
          <div className="h-4 w-32 bg-surface-container rounded" />
          <div className="h-8 w-64 bg-surface-container rounded" />
          <div className="h-40 w-full bg-surface-container rounded-2xl" />
        </div>
      }
    >
      <EndpointDetailStubContent />
    </Suspense>
  );
}
