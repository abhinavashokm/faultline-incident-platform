"use client";

import { useEffect, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Search, X } from "lucide-react";

import { badgeVariants } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { listIssuesApi } from "@/features/issues/api";
import type { IssueListItem } from "@/features/issues/types";
import { cn } from "@/lib/utils";

type IssuePickerProps = {
  projectId: string;
  selected: IssueListItem[];
  onChange: (issues: IssueListItem[]) => void;
};

const lastSeenFormat = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

export function IssuePicker({ projectId, selected, onChange }: IssuePickerProps) {
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState(false);
  const waitingForSearch = input.trim() !== search;
  const status = search || showAll ? undefined : "unresolved";

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(input.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [input]);

  const query = useInfiniteQuery({
    queryKey: ["incident-issue-picker", projectId, search, status],
    queryFn: ({ pageParam, signal }) =>
      listIssuesApi(projectId, { limit: 15, search, status, cursor: pageParam }, signal),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.meta.hasMore ? page.meta.nextCursor ?? undefined : undefined,
    enabled: !waitingForSearch,
  });

  const pageItems = waitingForSearch ? [] : query.data?.pages.flatMap((page) => page.items) ?? [];
  const issues = Array.from(new Map(pageItems.map((issue) => [issue.id, issue])).values());
  const selectedIds = new Set(selected.map((issue) => issue.id));
  const showRetry = query.isError && !issues.length;

  function toggle(issue: IssueListItem) {
    onChange(selectedIds.has(issue.id)
      ? selected.filter((item) => item.id !== issue.id)
      : [...selected, issue]);
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-48 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            type="search"
            aria-label="Search related issues by title"
            autoComplete="off"
            placeholder="Search issues by title…"
            value={input}
            maxLength={500}
            className="bg-canvas pl-9"
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.nativeEvent.isComposing) event.preventDefault();
            }}
          />
        </div>
        {!input.trim() && (
          <Button type="button" variant="outline" onClick={() => setShowAll(!showAll)}>
            {showAll ? "Show open issues" : "Show all statuses"}
          </Button>
        )}
      </div>
      {selected.length > 0 && (
        <ul aria-label="Selected issues" className="flex flex-wrap gap-2">
          {selected.map((issue) => (
            <li key={issue.id} className="flex min-w-0 max-w-full items-center gap-1 rounded-full border bg-primary-tint py-0.5 pl-2.5 pr-1 text-xs">
              <span className="truncate" title={issue.title}>{issue.title}</span>
              <button
                type="button"
                className="shrink-0 rounded-full p-1 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label={`Remove ${issue.title}`}
                onClick={() => toggle(issue)}
              >
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
      {issues.length > 0 && (
        <ul aria-label="Matching issues" className="max-h-80 space-y-2 overflow-y-auto p-0.5">
          {issues.map((issue) => {
            const checked = selectedIds.has(issue.id);

            return (
              <li key={issue.id}>
                <label className={cn(
                  "flex cursor-pointer items-start gap-3 rounded-lg border bg-canvas px-3 py-3 transition-colors hover:border-border-hover focus-within:ring-2 focus-within:ring-ring",
                  checked && "border-primary bg-primary-tint hover:border-primary",
                )}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(issue)}
                    className="mt-0.5 h-4 w-4 shrink-0 accent-primary"
                    aria-label={issue.title}
                  />
                  <span className="grid min-w-0 flex-1 gap-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.55fr)_auto] lg:items-center">
                    <span className="min-w-0">
                      <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <span className="min-w-0 break-words text-sm font-medium">{issue.title}</span>
                        <span className={badgeVariants({
                          variant: issue.status === "unresolved" ? "error" : issue.status === "resolved" ? "success" : "neutral",
                        })}>
                          {issue.status === "unresolved" ? "Open" : issue.status}
                        </span>
                      </span>
                      {issue.exceptionType && (
                        <span className="block break-words font-mono text-xs text-muted-foreground">{issue.exceptionType}</span>
                      )}
                    </span>
                    <span className={cn("min-w-0 break-words font-mono text-xs text-muted-foreground", !issue.culprit && "hidden lg:block")}>
                      {issue.culprit}
                    </span>
                    <span className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground lg:justify-end">
                      <span className="font-medium tabular-nums text-foreground">
                        {issue.occurrenceCount.toLocaleString()} {issue.occurrenceCount === 1 ? "event" : "events"}
                      </span>
                      <span>Last seen {lastSeenFormat.format(new Date(issue.lastSeen))}</span>
                    </span>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      )}
      {waitingForSearch || query.isPending ? (
        <p role="status" className="rounded-lg bg-canvas p-3 text-sm text-muted-foreground">Loading issues…</p>
      ) : showRetry ? (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-canvas p-3">
          <p role="alert" className="text-sm text-error">Couldn’t load issues.</p>
          <Button type="button" size="sm" variant="outline" onClick={() => void query.refetch()}>Retry</Button>
        </div>
      ) : !issues.length ? (
        <p role="status" className="rounded-lg bg-canvas p-3 text-sm text-muted-foreground">
          {status ? "No open issues." : search ? "No matching issues." : "No issues in this project."}
        </p>
      ) : null}
      {!waitingForSearch && query.hasNextPage && (
        <Button
          type="button"
          size="sm"
          variant="outline"
          aria-disabled={query.isFetching}
          onClick={() => {
            if (!query.isFetching) void query.fetchNextPage();
          }}
        >
          {query.isFetchingNextPage ? "Loading more…" : query.isFetchNextPageError ? "Retry loading more" : "Load more"}
        </Button>
      )}
    </div>
  );
}
