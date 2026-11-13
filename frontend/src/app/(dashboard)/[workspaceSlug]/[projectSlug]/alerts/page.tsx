"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Bell, Plus, Radio } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function AlertsPage() {
  const params = useParams();
  const workspaceSlug = (params?.workspaceSlug as string) || "";
  const projectSlug = (params?.projectSlug as string) || "";
  const channelsHref = `/${workspaceSlug}/${projectSlug}/alerts/channels`;
  const createAlertHref = `/${workspaceSlug}/${projectSlug}/alerts/new`;

  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b pb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Alerts
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure alert rules and manage notification destinations for {projectSlug || "your project"}.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            className="gap-2"
            asChild
          >
            <Link href={channelsHref}>
              <Radio className="h-4 w-4" />
              Manage notification channels
            </Link>
          </Button>
          <Button
            className="gap-2"
            asChild
          >
            <Link href={createAlertHref}>
              <Plus className="h-4 w-4" />
              Create new alert
            </Link>
          </Button>
        </div>
      </div>

      {/* Dummy Placeholder Content */}
      <div className="flex min-h-[420px] flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center animate-in fade-in-50">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary mb-4">
          <Bell className="h-8 w-8" />
        </div>
        <h2 className="text-lg font-semibold text-foreground mb-1">
          No alert rules configured yet
        </h2>
        <p className="text-sm text-muted-foreground max-w-md mb-6">
          Set up alerts to get notified when error spikes, performance regressions, or critical failures occur in real time.
        </p>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            className="gap-2"
            asChild
          >
            <Link href={channelsHref}>
              <Radio className="h-4 w-4" />
              Manage notification channels
            </Link>
          </Button>
          <Button
            className="gap-2"
            asChild
          >
            <Link href={createAlertHref}>
              <Plus className="h-4 w-4" />
              Create new alert
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
