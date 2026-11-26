"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Check, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  const id = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState(false);
  const [activeId, setActiveId] = useState<string>();
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
    enabled: open && !waitingForSearch,
  });

  const pageItems = waitingForSearch ? [] : query.data?.pages.flatMap((page) => page.items) ?? [];
  const issues = Array.from(new Map(pageItems.map((issue) => [issue.id, issue])).values());
  const activeIndex = issues.findIndex((issue) => issue.id === activeId);
  const activeOption = open && activeIndex >= 0 ? `${id}-${activeId}` : undefined;
  const selectedIds = new Set(selected.map((issue) => issue.id));
  const showRetry = query.isError && !issues.length;

  useEffect(() => {
    if (activeOption) document.getElementById(activeOption)?.scrollIntoView({ block: "nearest" });
  }, [activeOption]);

  function toggle(issue: IssueListItem) {
    onChange(selectedIds.has(issue.id)
      ? selected.filter((item) => item.id !== issue.id)
      : [...selected, issue]);
  }

  function close() {
    setOpen(false);
    setActiveId(undefined);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.nativeEvent.isComposing) return;

    if (event.key === "Escape" && open) {
      event.preventDefault();
      close();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      const next = event.key === "ArrowDown"
        ? Math.min(activeIndex + 1, issues.length - 1)
        : activeIndex < 0 ? issues.length - 1 : Math.max(activeIndex - 1, 0);
      setActiveId(issues[next]?.id);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (open && activeIndex >= 0) toggle(issues[activeIndex]);
      else setOpen(true);
    }
  }

  return (
    <div className="space-y-2" onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) close();
    }}>
      <Label htmlFor={id}>Related issues (optional)</Label>
      <div className="relative">
        <Input
          ref={inputRef}
          id={id}
          role="combobox"
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={open ? `${id}-list` : undefined}
          aria-activedescendant={activeOption}
          placeholder="Search by issue title"
          value={input}
          maxLength={500}
          onFocus={() => setOpen(true)}
          onClick={() => setOpen(true)}
          onChange={(event) => {
            setInput(event.target.value);
            setActiveId(undefined);
            setOpen(true);
          }}
          onKeyDown={handleKeyDown}
        />
        {open && (
          <div className="absolute inset-x-0 top-full z-20 mt-1 rounded-md border bg-popover text-popover-foreground shadow-md">
            <ul
              id={`${id}-list`}
              role="listbox"
              aria-label="Matching issues"
              aria-multiselectable="true"
              className="max-h-64 overflow-y-auto"
            >
              {issues.map((issue) => (
                <li
                  key={issue.id}
                  id={`${id}-${issue.id}`}
                  role="option"
                  aria-selected={selectedIds.has(issue.id)}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => toggle(issue)}
                  className={cn(
                    "flex cursor-pointer items-start gap-2 px-3 py-2 hover:bg-accent",
                    activeOption === `${id}-${issue.id}` && "bg-accent",
                  )}
                >
                  <Check className={cn("mt-0.5 h-4 w-4 shrink-0", !selectedIds.has(issue.id) && "invisible")} aria-hidden="true" />
                  <div className="min-w-0">
                    <div className="break-words text-sm font-medium">{issue.title}</div>
                    <div className="flex flex-wrap gap-x-2 text-xs text-muted-foreground">
                      <span className="capitalize">{issue.status}</span>
                      <span>{issue.occurrenceCount.toLocaleString()} {issue.occurrenceCount === 1 ? "event" : "events"}</span>
                      <span>Last seen {lastSeenFormat.format(new Date(issue.lastSeen))}</span>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
            {(waitingForSearch || query.isPending) ? (
              <p role="status" className="px-3 py-2 text-sm text-muted-foreground">Loading issues…</p>
            ) : showRetry ? (
              <p role="alert" className="px-3 py-2 text-sm text-error">Couldn’t load issues.</p>
            ) : !issues.length ? (
              <p role="status" className="px-3 py-2 text-sm text-muted-foreground">
                {status ? "No open issues." : "No matching issues."}
              </p>
            ) : null}
            {!waitingForSearch && (!search || query.hasNextPage || showRetry) && (
              <div className="flex flex-wrap items-center gap-1 border-t p-1">
                {!search && (
                  <Button type="button" size="sm" variant="ghost" onClick={() => {
                    setActiveId(undefined);
                    setShowAll(!showAll);
                  }}>
                    {showAll ? "Show open issues" : "Show all statuses"}
                  </Button>
                )}
                {query.hasNextPage && (
                  <Button type="button" size="sm" variant="ghost" aria-disabled={query.isFetching}
                    onClick={() => {
                      if (query.isFetching) return;
                      inputRef.current?.focus();
                      void query.fetchNextPage();
                    }}>
                    {query.isFetchingNextPage ? "Loading more…" : query.isFetchNextPageError ? "Retry loading more" : "Load more"}
                  </Button>
                )}
                {showRetry && (
                  <Button type="button" size="sm" variant="ghost" onClick={() => {
                    inputRef.current?.focus();
                    void query.refetch();
                  }}>
                    Retry
                  </Button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
      {selected.length > 0 && (
        <ul aria-label="Selected issues" className="flex flex-wrap gap-2">
          {selected.map((issue) => (
            <li key={issue.id} className="min-w-0 max-w-full">
              <Badge variant="neutral" className="max-w-full gap-1">
                <span className="truncate" title={issue.title}>{issue.title}</span>
                <button
                  type="button"
                  className="shrink-0 rounded-sm p-0.5 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label={`Remove ${issue.title}`}
                  onClick={() => toggle(issue)}
                >
                  <X className="h-3 w-3" aria-hidden="true" />
                </button>
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
