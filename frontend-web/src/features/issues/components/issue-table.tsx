"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CheckCircle2, EyeOff, AlertOctagon } from "lucide-react";
import { IssueListItem, IssueStatus } from "../types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface IssueTableProps {
  issues: IssueListItem[];
  workspaceSlug: string;
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: () => void;
  onBulkAction: (status: IssueStatus) => void;
  isBulkLoading?: boolean;
}

export function IssueTable({
  issues,
  workspaceSlug,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onBulkAction,
  isBulkLoading,
}: IssueTableProps) {
  const router = useRouter();

  const allSelected = issues.length > 0 && selectedIds.length === issues.length;

  return (
    <div className="rounded-lg border border-border bg-card shadow-level-1 overflow-hidden">
      {/* Bulk Action Header Bar (visible when items selected) */}
      {selectedIds.length > 0 && (
        <div className="bg-primary-tint px-4 py-2.5 border-b border-primary-subdued flex items-center justify-between animate-in fade-in-50">
          <div className="flex items-center gap-2">
            <span className="font-mono text-label-md font-semibold text-primary">
              {selectedIds.length} {selectedIds.length === 1 ? "issue" : "issues"} selected
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onBulkAction("resolved")}
              disabled={isBulkLoading}
              className="h-7 text-label-sm gap-1 bg-card hover:bg-canvas text-success-foreground border-success/30"
            >
              <CheckCircle2 className="h-3.5 w-3.5 text-success" />
              <span>Mark Resolved</span>
            </Button>

            <Button
              size="sm"
              variant="secondary"
              onClick={() => onBulkAction("ignored")}
              disabled={isBulkLoading}
              className="h-7 text-label-sm gap-1 bg-card hover:bg-canvas text-text-secondary"
            >
              <EyeOff className="h-3.5 w-3.5" />
              <span>Ignore</span>
            </Button>
          </div>
        </div>
      )}

      {/* Data Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            {/* Header: #F8FAFC background, 1px solid #E2E8F0 bottom boundary, uppercase 11px text in #475569 */}
            <tr className="bg-canvas border-b border-border text-label-sm uppercase text-text-secondary h-9">
              <th className="py-2 px-3.5 w-10 text-center">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={onToggleSelectAll}
                  aria-label="Select all issues"
                  className="h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary focus:ring-offset-0 cursor-pointer"
                />
              </th>
              <th className="py-2 px-3 font-medium">Issue &amp; Root Cause Culprit</th>
              <th className="py-2 px-3 font-medium">Environment</th>
              <th className="py-2 px-3 font-medium text-right">Events</th>
              <th className="py-2 px-3 font-medium text-right">Users</th>
              <th className="py-2 px-3 font-medium">First Seen</th>
              <th className="py-2 px-3 font-medium text-right">Last Seen</th>
              <th className="py-2 px-3.5 font-medium text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {issues.map((issue) => {
              const isSelected = selectedIds.includes(issue.id);

              return (
                <tr
                  key={issue.id}
                  onClick={() => router.push(`/${workspaceSlug}/issues/${issue.id}`)}
                  className={cn(
                    "h-11 transition-colors cursor-pointer text-body-sm select-none",
                    isSelected
                      ? "bg-primary-tint border-l-2 border-primary"
                      : "bg-card hover:bg-canvas"
                  )}
                >
                  {/* Checkbox column */}
                  <td
                    className="py-2 px-3.5 text-center"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleSelect(issue.id)}
                      aria-label={`Select issue ${issue.title}`}
                      className="h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary focus:ring-offset-0 cursor-pointer"
                    />
                  </td>

                  {/* Title & Culprit */}
                  <td className="py-2 px-3 min-w-[280px]">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/${workspaceSlug}/issues/${issue.id}`}
                        className="font-medium text-text-primary hover:text-primary transition-colors truncate max-w-md block"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {issue.title}
                      </Link>
                    </div>
                    <div className="font-mono text-[11px] text-text-muted truncate max-w-lg mt-0.5">
                      {issue.culprit}
                    </div>
                  </td>

                  {/* Environment chip */}
                  <td className="py-2 px-3">
                    <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-canvas border border-border text-text-secondary">
                      {issue.environment}
                    </span>
                  </td>

                  {/* Events (Mono tabular) */}
                  <td className="py-2 px-3 text-right font-mono text-[12px] tabular-nums font-semibold text-text-primary">
                    {issue.occurrenceCount.toLocaleString()}
                  </td>

                  {/* Users (Mono tabular) */}
                  <td className="py-2 px-3 text-right font-mono text-[12px] tabular-nums text-text-secondary">
                    {issue.affectedUsersCount.toLocaleString()}
                  </td>

                  {/* First Seen (Mono) */}
                  <td className="py-2 px-3 font-mono text-[11px] text-text-muted whitespace-nowrap">
                    {new Date(issue.firstSeen).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })}
                  </td>

                  {/* Last Seen (Mono) */}
                  <td className="py-2 px-3 text-right font-mono text-[11px] text-text-secondary whitespace-nowrap">
                    {new Date(issue.lastSeen).toLocaleTimeString("en-US", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>

                  {/* Status Badge (Pill, mono 11px uppercase with dot) */}
                  <td className="py-2 px-3.5 text-center">
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
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

