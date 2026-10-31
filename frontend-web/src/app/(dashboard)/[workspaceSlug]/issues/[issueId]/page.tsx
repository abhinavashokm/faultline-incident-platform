"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  EyeOff,
  RefreshCw,
  AlertCircle,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  GitCommit,
  Layers,
  Calendar,
  Users,
  Clock,
  Sparkles,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { StackTraceViewer } from "@/features/issues/components/stack-trace-viewer";
import { AiInvestigationCard } from "@/features/issues/components/ai-investigation-card";
import { BreadcrumbsPanel } from "@/features/issues/components/breadcrumbs-panel";
import { EventsFrequencyChart } from "@/features/issues/components/events-frequency-chart";
import { useIssueDetail, useUpdateIssueStatus } from "@/features/issues/hooks";

export default function IssueDetailPage() {
  const params = useParams();
  const workspaceSlug = (params.workspaceSlug as string) || "acme-cloud";
  const issueId = params.issueId as string;

  const [copiedFingerprint, setCopiedFingerprint] = useState(false);
  const [currentEventIndex, setCurrentEventIndex] = useState(1);

  const { data: issue, isLoading, isError, error, refetch, isFetching } = useIssueDetail(
    workspaceSlug,
    issueId
  );

  const { mutate: updateStatus, isPending: isUpdating } = useUpdateIssueStatus();

  const handleCopyFingerprint = (fingerprint: string) => {
    navigator.clipboard.writeText(fingerprint);
    setCopiedFingerprint(true);
    setTimeout(() => setCopiedFingerprint(false), 2000);
  };

  const handleResolve = () => {
    if (!issue) return;
    const newStatus = issue.status === "resolved" ? "unresolved" : "resolved";
    updateStatus({ issueId: issue.id, status: newStatus });
  };

  const handleIgnore = () => {
    if (!issue) return;
    const newStatus = issue.status === "ignored" ? "unresolved" : "ignored";
    updateStatus({ issueId: issue.id, status: newStatus });
  };

  // SKELETON LOADING STATE
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="rounded-lg border border-border bg-card p-6 space-y-4 shadow-level-1">
          <Skeleton className="h-7 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-border">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </div>
        <Skeleton className="h-32 w-full rounded-lg" />
        <Skeleton className="h-72 w-full rounded-lg" />
      </div>
    );
  }

  // NOT FOUND / ERROR STATE
  if (isError || !issue) {
    const is404 = (error as any)?.status === 404;

    return (
      <div className="space-y-6">
        <Link
          href={`/${workspaceSlug}/issues`}
          className="inline-flex items-center gap-1.5 text-body-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Issues</span>
        </Link>

        <Alert variant="destructive" className="shadow-level-2">
          <AlertCircle className="h-5 w-5" />
          <AlertTitle className="text-body-md font-semibold">
            {is404 ? "Issue Not Found" : "Error Loading Issue Details"}
          </AlertTitle>
          <AlertDescription className="mt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span>
              {is404
                ? `The issue with ID "${issueId}" does not exist in this workspace or was deleted.`
                : (error as any)?.message || "Failed to fetch issue details."}
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => refetch()}
              className="bg-card shrink-0"
            >
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back Link & Breadcrumb Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-label-md text-text-secondary">
          <Link
            href={`/${workspaceSlug}/issues`}
            className="inline-flex items-center gap-1 hover:text-text-primary transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Issues</span>
          </Link>
          <span className="text-text-muted">/</span>
          <span className="font-mono text-text-muted">
            {issue.id.slice(0, 8)}
          </span>
          <span className="text-text-muted">/</span>
          <span className="font-semibold text-text-primary">
            {issue.exceptionType}
          </span>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          className="h-8 gap-1.5 text-label-sm"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Main Issue Header Card */}
      <div className="rounded-lg border border-border bg-card p-6 shadow-level-1 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
          <div className="space-y-1.5 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <Badge
                variant={
                  issue.status === "resolved"
                    ? "success"
                    : issue.status === "ignored"
                    ? "neutral"
                    : issue.level === "fatal"
                    ? "error"
                    : "warning"
                }
                showDot
              >
                {issue.status}
              </Badge>

              <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-canvas border border-border text-text-secondary">
                {issue.environment}
              </span>

              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-muted border border-border text-text-secondary flex items-center gap-1">
                <GitCommit className="h-3 w-3" />
                <span>{issue.commitSha}</span>
              </span>
            </div>

            <h1 className="text-headline-md font-semibold text-text-primary tracking-tight break-words">
              {issue.title}
            </h1>

            <div className="font-mono text-[12px] text-text-muted">
              {issue.culprit}
            </div>
          </div>

          {/* Action Buttons: Resolve & Ignore */}
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant={issue.status === "resolved" ? "secondary" : "primary"}
              onClick={handleResolve}
              disabled={isUpdating}
              className="gap-1.5 text-body-sm h-9"
            >
              <CheckCircle2 className="h-4 w-4" />
              <span>
                {issue.status === "resolved" ? "Reopen Issue" : "Resolve"}
              </span>
            </Button>

            <Button
              variant="secondary"
              onClick={handleIgnore}
              disabled={isUpdating}
              className="gap-1.5 text-body-sm h-9"
            >
              <EyeOff className="h-4 w-4" />
              <span>
                {issue.status === "ignored" ? "Unignore" : "Ignore"}
              </span>
            </Button>
          </div>
        </div>

        {/* Metadata Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border text-label-md">
          {/* Occurrence Count */}
          <div className="space-y-0.5">
            <span className="text-text-muted flex items-center gap-1 text-[11px]">
              <Layers className="h-3 w-3" />
              <span>Total Events</span>
            </span>
            <div className="font-mono text-body-md font-semibold text-text-primary tabular-nums">
              {issue.occurrenceCount.toLocaleString()}
            </div>
          </div>

          {/* Affected Users */}
          <div className="space-y-0.5">
            <span className="text-text-muted flex items-center gap-1 text-[11px]">
              <Users className="h-3 w-3" />
              <span>Impacted Users</span>
            </span>
            <div className="font-mono text-body-md font-semibold text-text-primary tabular-nums">
              {issue.affectedUsersCount.toLocaleString()}
            </div>
          </div>

          {/* First Seen */}
          <div className="space-y-0.5">
            <span className="text-text-muted flex items-center gap-1 text-[11px]">
              <Calendar className="h-3 w-3" />
              <span>First Seen ({issue.firstRelease})</span>
            </span>
            <div className="font-mono text-body-sm text-text-secondary truncate">
              {new Date(issue.firstSeen).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </div>
          </div>

          {/* Last Seen */}
          <div className="space-y-0.5">
            <span className="text-text-muted flex items-center gap-1 text-[11px]">
              <Clock className="h-3 w-3" />
              <span>Last Seen ({issue.lastRelease})</span>
            </span>
            <div className="font-mono text-body-sm text-text-secondary truncate">
              {new Date(issue.lastSeen).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </div>
          </div>
        </div>

        {/* Fingerprint row */}
        <div className="pt-3 border-t border-border flex items-center justify-between text-[11px] font-mono text-text-muted">
          <div className="flex items-center gap-2 truncate">
            <span>Fingerprint:</span>
            <code className="text-text-secondary bg-canvas px-1.5 py-0.5 rounded border border-border truncate max-w-sm sm:max-w-md">
              {issue.fingerprint}
            </code>
          </div>
          <button
            type="button"
            onClick={() => handleCopyFingerprint(issue.fingerprint)}
            className="flex items-center gap-1 text-primary hover:underline ml-2 shrink-0"
          >
            {copiedFingerprint ? (
              <>
                <Check className="h-3 w-3 text-success" />
                <span className="text-success">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Events-over-time Chart */}
      <EventsFrequencyChart
        timeline={issue.eventsTimeline}
        totalEvents={issue.totalEvents}
      />

      {/* Event Navigation Bar */}
      <div className="rounded-lg border border-border bg-card p-3 shadow-level-1 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-label-md">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-text-primary">Viewing Event:</span>
          <span className="font-mono text-text-secondary">
            #{currentEventIndex} of {issue.totalEvents.toLocaleString()} (Latest)
          </span>
          <span className="text-border">•</span>
          <span className="font-mono text-[11px] text-text-muted truncate">
            ID: {issue.latestEvent.id}
          </span>
        </div>

        <div className="flex items-center gap-1.5 self-end sm:self-auto">
          <Button
            variant="secondary"
            size="sm"
            disabled={currentEventIndex <= 1}
            onClick={() => setCurrentEventIndex((prev) => Math.max(1, prev - 1))}
            className="h-7 text-label-sm gap-1"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            <span>Older</span>
          </Button>

          <Button
            variant="secondary"
            size="sm"
            disabled
            className="h-7 text-label-sm gap-1"
          >
            <span>Newer</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* AI Root Cause Panel */}
      <AiInvestigationCard
        investigation={issue.investigation}
        onRunInvestigation={() => alert("Triggering AI root cause investigation request...")}
      />

      {/* Stack Trace Viewer (per DESIGN.md spec) */}
      <StackTraceViewer frames={issue.latestEvent.stackFrames} />

      {/* Breadcrumbs, Tags & Context Panel */}
      <BreadcrumbsPanel
        breadcrumbs={issue.latestEvent.breadcrumbs}
        tags={issue.latestEvent.tags}
        user={issue.latestEvent.user}
        request={issue.latestEvent.request}
      />
    </div>
  );
}

