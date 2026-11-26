"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Search, X } from "lucide-react";

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
  const [cursors, setCursors] = useState<string[]>([]);
  const cursor = cursors[cursors.length - 1];
  const waitingForSearch = input.trim() !== search;
  const status = search || showAll ? undefined : "unresolved";

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(input.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [input]);

  const query = useQuery({
    queryKey: ["incident-issue-picker", projectId, search, status, cursor],
    queryFn: ({ signal }) => listIssuesApi(projectId, { limit: 5, search, status, cursor }, signal),
    enabled: !waitingForSearch,
  });

  const issues = waitingForSearch ? [] : query.data?.items ?? [];
  const nextCursor = query.data?.meta.hasMore ? query.data.meta.nextCursor : undefined;
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
        <div className="relative min-w-0 basis-full sm:flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            type="search"
            aria-label="Search related issues by title"
            autoComplete="off"
            placeholder="Search issues by title…"
            value={input}
            maxLength={500}
            className="bg-canvas pl-9"
            onChange={(event) => {
              if (event.target.value.trim() !== input.trim()) setCursors([]);
              setInput(event.target.value);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.nativeEvent.isComposing) event.preventDefault();
            }}
          />
        </div>
        {!input.trim() && (
          <Button type="button" variant="outline" aria-pressed={showAll} onClick={() => {
            setCursors([]);
            setShowAll(!showAll);
          }}>
            All statuses
          </Button>
        )}
      </div>
      {selected.length > 0 && (
        <ul aria-label="Selected issues" className="flex flex-wrap gap-2">
          {selected.map((issue) => (
            <li key={issue.id} className="flex min-w-0 max-w-full items-center gap-1 rounded-md border bg-canvas py-0.5 pl-2.5 pr-1 text-xs">
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
      <div className="rounded-lg border">
        {issues.length > 0 && (
          <ul aria-label="Matching issues" className="divide-y divide-border">
            {issues.map((issue) => {
              const checked = selectedIds.has(issue.id);

              return (
                <li key={issue.id} className="first:[&>label]:rounded-t-lg">
                  <label className={cn(
                    "flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-canvas focus-within:ring-2 focus-within:ring-inset focus-within:ring-ring",
                    checked && "bg-primary-tint hover:bg-primary-tint",
                  )}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(issue)}
                      className="mt-0.5 h-4 w-4 shrink-0 accent-primary"
                      aria-label={issue.title}
                    />
                    <span className="grid min-w-0 flex-1 gap-x-4 gap-y-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.45fr)_auto] lg:items-center">
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
          <p role="status" className="px-4 py-5 text-sm text-muted-foreground">Loading issues…</p>
        ) : showRetry ? (
          <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-5">
            <p role="alert" className="text-sm text-error">Couldn’t load issues.</p>
            <Button type="button" size="sm" variant="outline" onClick={() => void query.refetch()}>Retry</Button>
          </div>
        ) : !issues.length ? (
          <p role="status" className="px-4 py-5 text-sm text-muted-foreground">
            {status ? "No open issues." : search ? "No matching issues." : "No issues in this project."}
          </p>
        ) : null}
        <nav aria-label="Issue pagination" className="flex flex-wrap items-center justify-between gap-2 rounded-b-lg border-t bg-canvas px-4 py-2">
          <span aria-live="polite" className="text-xs font-medium tabular-nums text-muted-foreground">
            Page {cursors.length + 1}
          </span>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={!cursors.length || waitingForSearch}
              onClick={() => setCursors((history) => history.slice(0, -1))}
            >
              <ChevronLeft className="mr-1 h-4 w-4" aria-hidden="true" />
              Previous
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={!nextCursor || waitingForSearch || query.isFetching}
              onClick={() => {
                if (nextCursor) setCursors((history) => [...history, nextCursor]);
              }}
            >
              Next
              <ChevronRight className="ml-1 h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </nav>
      </div>
    </div>
  );
}
