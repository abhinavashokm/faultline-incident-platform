"use client";

import React from "react";
import { EventDetail } from "../types";
import { EventHeader } from "./event-header";
import { EventStackTrace } from "./event-stack-trace";
import { EventRequestService } from "./event-request-service";
import { EventMetadata } from "./event-metadata";
import { EventContextViewer } from "./event-context-viewer";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw } from "lucide-react";

interface EventDetailPanelProps {
  event?: EventDetail | null;
  isLoading: boolean;
  isError: boolean;
  error?: unknown;
  onRetry: () => void;
  currentIndex: number | null;
  totalCount: number | null;
  onNavigatePrev: () => void;
  onNavigateNext: () => void;
  canNavigatePrev: boolean;
  canNavigateNext: boolean;
  isNavigating?: boolean;
}

export function EventDetailPanel({
  event,
  isLoading,
  isError,
  error,
  onRetry,
  currentIndex,
  totalCount,
  onNavigatePrev,
  onNavigateNext,
  canNavigatePrev,
  canNavigateNext,
  isNavigating,
}: EventDetailPanelProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 shadow-level-1 space-y-6">
        <div className="flex justify-between items-center pb-3 border-b border-border">
          <Skeleton className="h-4 w-48" />
          <div className="flex gap-2">
            <Skeleton className="h-7 w-16" />
            <Skeleton className="h-7 w-16" />
          </div>
        </div>
        <div className="space-y-3">
          <Skeleton className="h-6 w-1/3" />
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-16 w-full" />
        </div>
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (isError || !event) {
    const is404 = (error as any)?.status === 404;

    return (
      <div className="rounded-lg border border-border bg-card p-6 shadow-level-1">
        <Alert variant="destructive">
          <AlertCircle className="h-5 w-5" />
          <AlertTitle className="text-body-md font-semibold">
            {is404 ? "Event Not Found" : "Error Loading Event"}
          </AlertTitle>
          <AlertDescription className="mt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span>
              {is404
                ? "The requested event could not be found or does not belong to this issue."
                : (error as any)?.message || "Failed to load event details."}
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={onRetry}
              className="bg-card shrink-0 gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Retry</span>
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Event Header Card */}
      <div className="rounded-lg border border-border bg-card p-6 shadow-level-1">
        <EventHeader
          event={event}
          currentIndex={currentIndex}
          totalCount={totalCount}
          onNavigatePrev={onNavigatePrev}
          onNavigateNext={onNavigateNext}
          canNavigatePrev={canNavigatePrev}
          canNavigateNext={canNavigateNext}
          isNavigating={isNavigating}
        />
      </div>

      {/* Stack Trace */}
      {event.stackFrames && event.stackFrames.length > 0 && (
        <EventStackTrace frames={event.stackFrames} />
      )}

      {/* Request & Service */}
      <EventRequestService
        httpMethod={event.httpMethod}
        routeTemplate={event.routeTemplate}
        statusCode={event.statusCode}
        service={event.service}
      />

      {/* Environment, Release, User & Debug */}
      <EventMetadata
        environment={event.environment}
        release={event.release}
        userHash={event.userHash}
        fingerprint={event.fingerprint}
      />

      {/* Generic Context Viewer */}
      {event.context && (
        <EventContextViewer context={event.context} />
      )}
    </div>
  );
}
