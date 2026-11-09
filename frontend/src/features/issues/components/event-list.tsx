"use client";

import React from "react";
import { EventListItem } from "../types";
import { EventListItemRow } from "./event-list-item";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Loader2, RefreshCw } from "lucide-react";

interface EventListProps {
  events: EventListItem[];
  selectedEventId: string | null;
  onSelectEvent: (eventId: string) => void;
  isLoading: boolean;
  isError: boolean;
  error?: unknown;
  onRetry: () => void;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  onLoadMore: () => void;
}

export function EventList({
  events,
  selectedEventId,
  onSelectEvent,
  isLoading,
  isError,
  error,
  onRetry,
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
}: EventListProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card shadow-level-1 overflow-hidden divide-y divide-border">
        <div className="p-3 bg-canvas/40 border-b border-border">
          <Skeleton className="h-4 w-28" />
        </div>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="p-3.5 space-y-2">
            <div className="flex justify-between items-center">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-12" />
            </div>
            <div className="flex justify-between items-center">
              <Skeleton className="h-3 w-1/3" />
              <Skeleton className="h-3 w-14" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 shadow-level-1 text-center space-y-3">
        <p className="text-body-sm text-error">
          Failed to load issue events.
        </p>
        <Button
          variant="secondary"
          size="sm"
          onClick={onRetry}
          className="gap-1.5 h-8 text-label-sm"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Retry</span>
        </Button>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 shadow-level-1 text-center">
        <p className="text-body-sm text-text-secondary">
          No events recorded for this issue.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card shadow-level-1 overflow-hidden flex flex-col">
      {/* Header bar */}
      <div className="px-3.5 py-2.5 bg-canvas/40 border-b border-border flex items-center justify-between text-label-sm text-text-secondary">
        <span className="font-semibold text-text-primary">Events</span>
        <span className="font-mono text-[11px] text-text-muted">
          {events.length} loaded
        </span>
      </div>

      {/* List items */}
      <div className="divide-y divide-border max-h-[680px] overflow-y-auto">
        {events.map((event) => (
          <EventListItemRow
            key={event.id}
            event={event}
            isSelected={event.id === selectedEventId}
            onSelect={() => onSelectEvent(event.id)}
          />
        ))}

        {/* Load more button */}
        {hasNextPage && (
          <div className="p-3 bg-canvas/30 text-center">
            <Button
              variant="secondary"
              size="sm"
              onClick={onLoadMore}
              disabled={isFetchingNextPage}
              className="w-full text-label-sm h-8 gap-2"
            >
              {isFetchingNextPage ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Loading more...</span>
                </>
              ) : (
                <span>Load more events</span>
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
