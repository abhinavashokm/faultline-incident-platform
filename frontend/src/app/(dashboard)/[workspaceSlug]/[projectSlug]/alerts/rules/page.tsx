"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronRight,
  Plus,
  SlidersHorizontal,
  Bell,
  AlertTriangle,
  Loader2,
  ShieldCheck,
  Zap,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { useProjectBySlug } from "@/features/projects/hooks";
import { AlertRulesList } from "@/features/alerts/components/alert-rules-list";
import {
  listAlertRules,
  deleteAlertRule,
  toggleAlertRule,
} from "@/features/alerts/api/alertRulesApi";
import { AlertRule } from "@/features/alerts/types";

export default function AlertRulesPage() {
  const params = useParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const workspaceSlug = (params?.workspaceSlug as string) || "";
  const projectSlug = (params?.projectSlug as string) || "";

  const { project, isLoading: isProjectLoading } = useProjectBySlug(projectSlug);
  const projectId = project?.id;

  const alertsHref = `/${workspaceSlug}/${projectSlug}/alerts`;
  const createRuleHref = `/${workspaceSlug}/${projectSlug}/alerts/rules/new`;

  // Fetch alert rules with React Query
  const {
    data: rules = [],
    isLoading: isRulesLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["alert-rules", projectId],
    queryFn: () => listAlertRules(projectId!),
    enabled: Boolean(projectId),
  });

  const isLoading = isProjectLoading || (Boolean(projectId) && isRulesLoading);
  const loadError = isError
    ? error instanceof Error
      ? error.message
      : "Failed to load alert rules"
    : null;

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => {
      if (!projectId) throw new Error("Project ID is missing");
      return deleteAlertRule(projectId, id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-rules", projectId] });
      toast({
        title: "Rule deleted",
        description: "The alert rule has been removed successfully.",
        variant: "default",
      });
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "Failed to delete alert rule";
      toast({
        title: "Delete failed",
        description: message,
        variant: "destructive",
      });
    },
  });

  // Toggle mutation
  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => {
      if (!projectId) throw new Error("Project ID is missing");
      return toggleAlertRule(projectId, id, enabled);
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["alert-rules", projectId] });
      toast({
        title: updated.enabled ? "Rule activated" : "Rule disabled",
        description: `Rule "${updated.name}" is now ${
          updated.enabled ? "active" : "disabled"
        }.`,
        variant: "default",
      });
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "Failed to update alert rule";
      toast({
        title: "Update failed",
        description: message,
        variant: "destructive",
      });
    },
  });

  const handleDeleteRule = async (id: string) => {
    await deleteMutation.mutateAsync(id);
  };

  const handleToggleRule = (id: string) => {
    const rule = rules.find((r) => r.id === id);
    if (!rule) return;
    toggleMutation.mutate({ id, enabled: !rule.enabled });
  };

  const activeRulesCount = rules.filter((r) => r.enabled).length;

  return (
    <div className="flex-1 space-y-6 p-6 max-w-7xl mx-auto">
      {/* Breadcrumb & Header matching Notification Channels page */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between border-b pb-5">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <Link
              href={alertsHref}
              className="hover:text-foreground transition-colors"
            >
              Alerts
            </Link>
            <ChevronRight className="h-3 w-3" />
            <span className="text-primary font-semibold">Alert Rules</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Alert Rules
          </h1>
          <p className="text-sm text-muted-foreground max-w-2xl">
            Configure automated rules to detect and dispatch notifications when error conditions occur in {projectSlug || "your project"}.
          </p>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <Button asChild className="gap-2">
            <Link href={createRuleHref}>
              <Plus className="h-4 w-4" />
              Create rule
            </Link>
          </Button>
        </div>
      </div>

      {/* Stat Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border bg-card text-card-foreground shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <SlidersHorizontal className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold">
                {isLoading ? "--" : `${rules.length} Configured`}
              </div>
              <div className="text-xs text-muted-foreground">
                Total telemetry rules
              </div>
            </div>
          </div>
          <span className="px-2.5 py-0.5 rounded-full bg-muted text-xs font-medium text-muted-foreground">
            {isLoading ? "--" : `${activeRulesCount} Active`}
          </span>
        </div>

        <div className="p-4 rounded-xl border bg-card text-card-foreground shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold">Real-time</div>
              <div className="text-xs text-muted-foreground">
                Evaluation latency
              </div>
            </div>
          </div>
          <span className="px-2.5 py-0.5 rounded-full bg-muted text-xs font-mono text-muted-foreground">
            &lt; 50ms
          </span>
        </div>

        <div className="p-4 rounded-xl border bg-card text-card-foreground shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-600 dark:text-purple-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold">Deduplicated</div>
              <div className="text-xs text-muted-foreground">
                Fingerprint aggregation
              </div>
            </div>
          </div>
          <span className="px-2.5 py-0.5 rounded-full bg-muted text-xs font-mono text-muted-foreground">
            Active
          </span>
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        /* Loading Skeleton matching table style */
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-20" />
          </div>
          <div className="space-y-3">
            <Skeleton className="h-12 w-full rounded-lg" />
            <Skeleton className="h-12 w-full rounded-lg" />
            <Skeleton className="h-12 w-full rounded-lg" />
          </div>
        </div>
      ) : loadError ? (
        /* Error State */
        <div className="flex min-h-[360px] flex-col items-center justify-center rounded-xl border border-dashed border-error/40 p-8 text-center bg-error-container/10">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-error/10 text-error mb-4">
            <AlertTriangle className="h-7 w-7" />
          </div>
          <h2 className="text-lg font-semibold text-foreground mb-1">
            Failed to load alert rules
          </h2>
          <p className="text-sm text-muted-foreground max-w-md mb-6">
            {loadError}
          </p>
          <Button variant="outline" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      ) : rules.length === 0 ? (
        /* Empty State */
        <div className="flex min-h-[380px] flex-col items-center justify-center rounded-xl border border-dashed p-8 text-center bg-card/40">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary mb-4">
            <Bell className="h-8 w-8" />
          </div>
          <h2 className="text-lg font-semibold text-foreground mb-1">
            No alert rules yet
          </h2>
          <p className="text-sm text-muted-foreground max-w-md mb-6">
            Get notified when new issues and exceptions occur in your codebase by configuring your first rule.
          </p>
          <Button asChild className="gap-2">
            <Link href={createRuleHref}>
              <Plus className="h-4 w-4" />
              Create rule
            </Link>
          </Button>
        </div>
      ) : (
        /* Populated Rules List */
        <AlertRulesList
          rules={rules}
          onDeleteRule={handleDeleteRule}
          onToggleRule={handleToggleRule}
        />
      )}
    </div>
  );
}
