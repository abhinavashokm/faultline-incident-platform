"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import {
  AlertOctagon,
  RefreshCw,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
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
import { useProjectBySlug } from "@/features/projects/hooks";
import { ProjectNotFound } from "@/features/projects/components/project-not-found";

export default function IssuesListPage() {
  const params = useParams();
  const workspaceSlug = (params.workspaceSlug as string) || "acme-cloud";
  const projectSlug = (params.projectSlug as string) || "";

  const {
    project,
    isLoading: isProjectLoading,
    isNotFound: isProjectNotFound,
    isArchived: isProjectArchived,
  } = useProjectBySlug(projectSlug);

  const [filters, setFilters] = useState<IssueFilterParams>({
    status: "unresolved",
    limit: 25,
  });

  // Cursor pagination state: stack of previous cursors for backwards navigation
  const [cursorStack, setCursorStack] = useState<(string | undefined)[]>([]);
  const currentCursor = cursorStack[cursorStack.length - 1];

  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const {
    data,
    isLoading: isIssuesLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useIssuesList(project?.id, {
    ...filters,
    cursor: currentCursor,
  });

  const { mutate: bulkUpdateStatus, isPending: isBulkUpdating } =
    useBulkUpdateIssueStatus();

  const handleFilterChange = (newFilters: Partial<IssueFilterParams>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
    setCursorStack([]);
    setSelectedIds([]);
  };

  const handleNextPage = () => {
    if (data?.meta.nextCursor) {
      setCursorStack((prev) => [...prev, data.meta.nextCursor!]);
      setSelectedIds([]);
    }
  };

  const handlePrevPage = () => {
    if (cursorStack.length > 0) {
      setCursorStack((prev) => prev.slice(0, prev.length - 1));
      setSelectedIds([]);
    }
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

  if (isProjectNotFound || isProjectArchived) {
    return (
      <ProjectNotFound
        slug={projectSlug}
        workspaceSlug={workspaceSlug}
        isArchived={isProjectArchived}
      />
    );
  }

  const isLoading = isProjectLoading || isIssuesLoading;

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
            disabled={isFetching || isProjectLoading}
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
                {`There are currently no ${filters.status} issues for this project.`}
              </p>
            </div>
          ) : (
            <>
              {/* Data Table */}
              <IssueTable
                issues={data.items}
                workspaceSlug={workspaceSlug}
                projectSlug={projectSlug}
                selectedIds={selectedIds}
                onToggleSelect={handleToggleSelect}
                onToggleSelectAll={handleToggleSelectAll}
                onBulkAction={handleBulkAction}
                isBulkLoading={isBulkUpdating}
              />

              {/* Pagination Footer */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-label-sm text-text-secondary px-1">
                <span>
                  Showing {data.items.length} {data.items.length === 1 ? "issue" : "issues"}
                  {cursorStack.length > 0 && ` (Page ${cursorStack.length + 1})`}
                </span>

                <div className="flex items-center gap-1.5">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handlePrevPage}
                    disabled={cursorStack.length === 0 || isFetching}
                    className="h-8 gap-1 text-label-sm"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    <span>Previous</span>
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleNextPage}
                    disabled={!data.meta.hasMore || !data.meta.nextCursor || isFetching}
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

