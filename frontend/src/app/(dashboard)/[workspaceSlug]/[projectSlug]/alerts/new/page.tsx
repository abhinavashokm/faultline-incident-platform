"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Radio,
  Plus,
  Loader2,
  AlertTriangle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { CreateAlertRuleForm } from "@/features/alerts/components/create-alert-rule-form";
import { listChannels } from "@/features/alerts/api/alertRulesApi";
import { useProjectBySlug } from "@/features/projects/hooks";

export default function CreateAlertRulePage() {
  const params = useParams();
  const workspaceSlug = (params?.workspaceSlug as string) || "";
  const projectSlug = (params?.projectSlug as string) || "";

  const { project, isLoading: isProjectLoading } = useProjectBySlug(projectSlug);
  const projectId = project?.id;

  const alertsListHref = `/${workspaceSlug}/${projectSlug}/alerts`;
  const channelsHref = `/${workspaceSlug}/${projectSlug}/alerts/channels`;

  const {
    data: channels = [],
    isLoading: isChannelsLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["notification-channels", projectId],
    queryFn: () => listChannels(projectId!),
    enabled: Boolean(projectId),
  });

  const isLoading = isProjectLoading || (Boolean(projectId) && isChannelsLoading);
  const loadError = isError
    ? error instanceof Error
      ? error.message
      : "Failed to load notification channels"
    : null;

  return (
    <div className="flex-1 space-y-6 p-6 max-w-4xl mx-auto">
      {/* Page Header with Back Link */}
      <div className="space-y-2 border-b pb-5">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="gap-1.5 -ml-2 text-text-secondary" asChild>
            <Link href={alertsListHref}>
              <ArrowLeft className="h-4 w-4" />
              <span>Back to Alerts</span>
            </Link>
          </Button>
        </div>
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Create Alert Rule
            </h1>
            <p className="text-sm text-muted-foreground">
              Define triggers and dispatch destinations to notify your team when issues occur.
            </p>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {isLoading ? (
        <div className="flex min-h-[360px] flex-col items-center justify-center rounded-xl border border-dashed p-8 text-center animate-in fade-in-50">
          <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
          <p className="text-sm text-muted-foreground">
            Loading notification channels...
          </p>
        </div>
      ) : loadError ? (
        /* Error State loading channels */
        <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed border-error/40 p-8 text-center animate-in fade-in-50 bg-error-container/20">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-error/10 text-error mb-3">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-semibold text-foreground mb-1">
            Failed to load channels
          </h2>
          <p className="text-sm text-muted-foreground max-w-md mb-5">
            {loadError}
          </p>
          <Button variant="outline" onClick={() => refetch()}>
            Try again
          </Button>
        </div>
      ) : channels.length === 0 ? (
        /* Empty State: If channel list is empty */
        <div className="flex min-h-[420px] flex-col items-center justify-center rounded-xl border border-dashed p-8 text-center animate-in fade-in-50 bg-card">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary mb-4">
            <Radio className="h-8 w-8" />
          </div>
          <h2 className="text-lg font-semibold text-foreground mb-1">
            Add a notification channel first
          </h2>
          <p className="text-sm text-muted-foreground max-w-md mb-6">
            Alert rules require at least one active notification channel to dispatch alerts. Configure an email or integration destination before creating rules.
          </p>
          <Button className="gap-2" asChild>
            <Link href={channelsHref}>
              <Plus className="h-4 w-4" />
              Configure notification channels
            </Link>
          </Button>
        </div>
      ) : (
        /* Active Form */
        <CreateAlertRuleForm projectId={projectId!} channels={channels} />
      )}
    </div>
  );
}
