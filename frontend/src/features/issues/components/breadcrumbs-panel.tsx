"use client";

import React, { useState } from "react";
import { Breadcrumb } from "../types";
import { Tag, Globe, User } from "lucide-react";
import { cn } from "@/lib/utils";

interface BreadcrumbsPanelProps {
  breadcrumbs?: Breadcrumb[];
  tags: Record<string, string>;
  user?: {
    id: string;
    ipAddress: string;
    email?: string;
  };
  request?: {
    method: string;
    url: string;
    statusCode?: number;
  };
}

export function BreadcrumbsPanel({
  tags,
  user,
  request,
}: BreadcrumbsPanelProps) {
  const [activeTab, setActiveTab] = useState<"tags" | "context">("tags");

  return (
    <div className="rounded-lg border border-border bg-card shadow-level-1 overflow-hidden">
      {/* Header Tabs */}
      <div className="flex items-center justify-between border-b border-border bg-canvas/40 px-4 py-2">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setActiveTab("tags")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-label-md font-medium transition-colors",
              activeTab === "tags"
                ? "bg-card text-primary font-semibold shadow-level-1"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            <Tag className="h-3.5 w-3.5" />
            <span>Tags ({Object.keys(tags).length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("context")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-label-md font-medium transition-colors",
              activeTab === "context"
                ? "bg-card text-primary font-semibold shadow-level-1"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            <Globe className="h-3.5 w-3.5" />
            <span>Request Context</span>
          </button>
        </div>

        <span className="font-mono text-[11px] text-text-muted hidden sm:inline">
          Event Context
        </span>
      </div>

      {/* Content Panes */}
      <div className="p-4">
        {/* Tags Tab */}
        {activeTab === "tags" && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
            {Object.entries(tags).map(([key, value]) => (
              <div
                key={key}
                className="p-2.5 rounded-md border border-border bg-canvas flex flex-col justify-between"
              >
                <span className="font-mono text-[11px] text-text-muted truncate">
                  {key}
                </span>
                <span className="font-mono text-[12px] font-semibold text-text-primary truncate mt-0.5">
                  {value}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Request & User Context Tab */}
        {activeTab === "context" && (
          <div className="space-y-4">
            {/* Request Info */}
            {request && (
              <div className="p-3.5 rounded-md border border-border bg-canvas space-y-2">
                <div className="flex items-center gap-2 text-body-sm font-semibold text-text-primary">
                  <Globe className="h-4 w-4 text-primary" />
                  <span>HTTP Ingestion Trigger</span>
                </div>
                <div className="font-mono text-[12px] text-text-secondary flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded bg-card border border-border font-bold text-text-primary">
                    {request.method}
                  </span>
                  <span className="truncate">{request.url}</span>
                  {request.statusCode && (
                    <span className="text-error font-semibold">
                      [{request.statusCode}]
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* User Info */}
            {user && (
              <div className="p-3.5 rounded-md border border-border bg-canvas space-y-2">
                <div className="flex items-center gap-2 text-body-sm font-semibold text-text-primary">
                  <User className="h-4 w-4 text-primary" />
                  <span>Impacted Identity</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-[12px]">
                  <div>
                    <span className="text-text-muted text-[11px] block">User ID:</span>
                    <span className="text-text-primary font-medium">{user.id}</span>
                  </div>
                  <div>
                    <span className="text-text-muted text-[11px] block">IP Address:</span>
                    <span className="text-text-primary font-medium">{user.ipAddress}</span>
                  </div>
                  <div>
                    <span className="text-text-muted text-[11px] block">Email:</span>
                    <span className="text-text-primary font-medium">{user.email || "N/A"}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

