"use client";

import React, { useState } from "react";
import { Breadcrumb } from "../types";
import { History, Tag, Globe, User, Shield, Database, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

// TODO(mock): Contextual breadcrumbs telemetry planned in SDK spec; providing mock history
interface BreadcrumbsPanelProps {
  breadcrumbs: Breadcrumb[];
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
  breadcrumbs,
  tags,
  user,
  request,
}: BreadcrumbsPanelProps) {
  const [activeTab, setActiveTab] = useState<"breadcrumbs" | "tags" | "context">("breadcrumbs");

  return (
    <div className="rounded-lg border border-border bg-card shadow-level-1 overflow-hidden">
      {/* Header Tabs */}
      <div className="flex items-center justify-between border-b border-border bg-canvas/40 px-4 py-2">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setActiveTab("breadcrumbs")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-label-md font-medium transition-colors",
              activeTab === "breadcrumbs"
                ? "bg-card text-primary font-semibold shadow-level-1"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            <History className="h-3.5 w-3.5" />
            <span>Breadcrumbs ({breadcrumbs.length})</span>
          </button>

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
        {/* Breadcrumbs Tab */}
        {activeTab === "breadcrumbs" && (
          <div className="space-y-3">
            <p className="text-[12px] text-text-secondary">
              Chronological actions leading up to the unhandled exception:
            </p>
            <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
              {breadcrumbs.map((crumb, idx) => (
                <div key={idx} className="relative flex items-start gap-3">
                  <span
                    className={cn(
                      "absolute -left-6 top-1 h-2.5 w-2.5 rounded-full border-2 border-card ring-2 ring-border",
                      crumb.level === "error"
                        ? "bg-error ring-error/30"
                        : crumb.level === "warning"
                        ? "bg-warning ring-warning/30"
                        : "bg-primary ring-primary/30"
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-text-muted">
                        {crumb.timestamp}
                      </span>
                      <span
                        className={cn(
                          "font-mono text-[10px] px-1.5 rounded font-semibold uppercase",
                          crumb.category === "db"
                            ? "bg-primary-tint text-primary"
                            : crumb.category === "auth"
                            ? "bg-success-container text-success-foreground"
                            : "bg-canvas border border-border text-text-secondary"
                        )}
                      >
                        {crumb.category}
                      </span>
                    </div>
                    <p className="font-mono text-[12px] text-text-primary mt-1">
                      {crumb.message}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

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

