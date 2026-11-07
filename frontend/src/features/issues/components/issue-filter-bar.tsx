"use client";

import React from "react";
import { Search, Filter } from "lucide-react";
import { IssueStatus, IssueFilterParams } from "../types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

interface IssueFilterBarProps {
  filters: IssueFilterParams;
  onFilterChange: (newFilters: Partial<IssueFilterParams>) => void;
  unresolvedCount?: number;
}

export function IssueFilterBar({
  filters,
  onFilterChange,
  unresolvedCount = 0,
}: IssueFilterBarProps) {
  const currentStatus = filters.status || "unresolved";

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 rounded-lg border border-border bg-card p-2.5 shadow-level-1">
      {/* Left: Status Segmented Controls */}
      <div className="flex items-center gap-1 bg-canvas p-1 rounded-md border border-border">
        {(["unresolved", "resolved", "ignored"] as IssueStatus[]).map((status) => {
          const isActive = currentStatus === status;
          return (
            <button
              key={status}
              type="button"
              onClick={() => onFilterChange({ status })}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1 rounded text-label-md font-medium capitalize transition-all select-none",
                isActive
                  ? "bg-card text-text-primary font-semibold shadow-level-1"
                  : "text-text-secondary hover:text-text-primary"
              )}
            >
              <span>{status}</span>
              {status === "unresolved" && unresolvedCount > 0 && (
                <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-full bg-warning-container text-warning-foreground font-semibold">
                  {unresolvedCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Right: Environment, Time Range & Search */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Environment Filter */}
        <div className="w-32">
          <Select
            value={filters.environment || "all"}
            onValueChange={(val) => onFilterChange({ environment: val })}
          >
            <SelectTrigger className="h-8 text-label-md bg-canvas">
              <SelectValue placeholder="Environment" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Envs</SelectItem>
              <SelectItem value="production">production</SelectItem>
              <SelectItem value="staging">staging</SelectItem>
              <SelectItem value="development">development</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Time Range Filter */}
        <div className="w-28">
          <Select
            value={filters.timeRange || "24h"}
            onValueChange={(val) =>
              onFilterChange({ timeRange: val as IssueFilterParams["timeRange"] })
            }
          >
            <SelectTrigger className="h-8 text-label-md bg-canvas">
              <SelectValue placeholder="Time range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last 1 hour</SelectItem>
              <SelectItem value="24h">Last 24 hours</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="14d">Last 14 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Search Bar */}
        <div className="relative min-w-[200px] flex-1 md:w-56">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-muted" />
          <input
            type="text"
            value={filters.search || ""}
            onChange={(e) => onFilterChange({ search: e.target.value })}
            placeholder="Search issues or SHA..."
            className="w-full h-8 pl-8 pr-3 rounded-md border border-border bg-canvas text-body-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary-subdued focus:outline-none transition-all"
          />
        </div>
      </div>
    </div>
  );
}

