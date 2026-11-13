"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Bell, Radio, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function AlertsPage() {
  const params = useParams();
  const workspaceSlug = (params?.workspaceSlug as string) || "";
  const projectSlug = (params?.projectSlug as string) || "";
  const channelsHref = `/${workspaceSlug}/${projectSlug}/alerts/channels`;
  const rulesHref = `/${workspaceSlug}/${projectSlug}/alerts/rules`;

  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b pb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Alerts
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            View fired alerts and manage notification destinations for {projectSlug || "your project"}.
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
            <Link href={rulesHref}>
              <SlidersHorizontal className="h-4 w-4" />
              Manage rules
            </Link>
          </Button>
        </div>
      </div>

      {/* Empty State / Fired Alerts Placeholder */}
      <div className="flex min-h-[420px] flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center animate-in fade-in-50">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary mb-4">
          <Bell className="h-8 w-8" />
        </div>
        <h2 className="text-lg font-semibold text-foreground mb-1">
          No alerts yet. Create a rule to get notified.
        </h2>
        <p className="text-sm text-muted-foreground max-w-md mb-6">
          Set up automated alert rules to trigger when issues, spikes, or error regressions occur in real time.
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
            <Link href={rulesHref}>
              <SlidersHorizontal className="h-4 w-4" />
              Manage rules
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
