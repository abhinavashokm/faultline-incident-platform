"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import {
  AlertOctagon,
  RefreshCw,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Terminal,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { IssueFilterBar } from "@/features/issues/components/issue-filter-bar";
import { IssueTable } from "@/features/issues/components/issue-table";
import {
  useIssuesList,
  useBulkUpdateIssueStatus,
} from "@/features/issues/hooks";
import { IssueFilterParams, IssueStatus } from "@/features/issues/types";

export default function IssuesListPage() {
  const params = useParams();
  const workspaceSlug = (params.workspaceSlug as string) || "acme-cloud";

  const [filters, setFilters] = useState<IssueFilterParams>({
    status: "unresolved",
    environment: "all",
    timeRange: "24h",
    search: "",
    limit: 25,
  });

  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const { data, isLoading, isError, error, refetch, isFetching } = useIssuesList(
    workspaceSlug,
    filters
  );

  const { mutate: bulkUpdateStatus, isPending: isBulkUpdating } =
    useBulkUpdateIssueStatus();

  const handleFilterChange = (newFilters: Partial<IssueFilterParams>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
    setSelectedIds([]);
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleToggleSelectAll = () => {
    if (!data?.items) return;
    if (selectedIds.length === data.items.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(data.items.map((i) => i.id));
    }
  };

  const handleBulkAction = (status: IssueStatus) => {
    if (selectedIds.length === 0) return;
    bulkUpdateStatus(
      { issueIds: selectedIds, status },
      {
        onSuccess: () => {
          setSelectedIds([]);
        },
      }
    );
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-headline-md font-semibold text-text-primary tracking-tight">
              Issues
            </h1>
            <span className="font-mono text-label-sm px-2 py-0.5 rounded-full bg-card border border-border text-text-secondary">
              Fingerprinted &amp; Grouped
            </span>
          </div>
          <p className="text-body-sm text-text-secondary mt-0.5">
            Grouped error occurrences and exceptions triaged across cluster services.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
            <span>Sync</span>
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <IssueFilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        unresolvedCount={filters.status === "unresolved" ? data?.totalCount : undefined}
      />

      {/* ERROR STATE */}
      {isError && (
        <Alert variant="destructive" className="shadow-level-2">
          <AlertCircle className="h-5 w-5" />
          <AlertTitle className="text-body-md font-semibold">
            Unable to load issues
          </AlertTitle>
          <AlertDescription className="mt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span>
              {(error as any)?.message ||
                "Failed to query the processing issues repository."}
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
      )}

      {/* SKELETON LOADING STATE */}
      {isLoading && (
        <div className="rounded-lg border border-border bg-card p-6 space-y-4 shadow-level-1">
          <div className="space-y-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-11 w-full" />
            ))}
          </div>
        </div>
      )}

      {/* LOADED CONTENT */}
      {!isLoading && !isError && data && (
        <>
          {data.items.length === 0 ? (
            /* EMPTY STATE */
            <div className="rounded-lg border border-border bg-card p-12 text-center shadow-level-1">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary-tint border border-primary-subdued text-primary mb-3">
                <AlertOctagon className="h-6 w-6" />
              </div>
              <h3 className="text-headline-sm font-semibold text-text-primary">
                No issues found
              </h3>
              <p className="text-body-sm text-text-secondary max-w-sm mx-auto mt-1 mb-5">
                {filters.search
                  ? `No issues matching "${filters.search}". Try adjusting your search query or filters.`
                  : `There are currently no ${filters.status} issues in this environment.`}
              </p>
              {filters.search && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleFilterChange({ search: "" })}
                >
                  Clear search query
                </Button>
              )}
            </div>
          ) : (
            <>
              {/* Data Table */}
              <IssueTable
                issues={data.items}
                workspaceSlug={workspaceSlug}
                selectedIds={selectedIds}
                onToggleSelect={handleToggleSelect}
                onToggleSelectAll={handleToggleSelectAll}
                onBulkAction={handleBulkAction}
                isBulkLoading={isBulkUpdating}
              />

              {/* Pagination Footer */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-label-sm text-text-secondary px-1">
                <span>
                  Showing {data.items.length} of {data.totalCount} issues
                </span>

                <div className="flex items-center gap-1.5">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled
                    className="h-8 gap-1 text-label-sm"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    <span>Previous</span>
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={!data.hasMore}
                    className="h-8 gap-1 text-label-sm"
                  >
                    <span>Next</span>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

