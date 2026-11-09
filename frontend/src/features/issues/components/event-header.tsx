"use client";

import React, { useState } from "react";
import { EventDetail } from "../types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Copy, Check, ChevronLeft, ChevronRight } from "lucide-react";

interface EventHeaderProps {
  event: EventDetail;
  currentIndex: number | null; // 1-based index if in list
  totalCount: number | null;
  onNavigatePrev: () => void;
  onNavigateNext: () => void;
  canNavigatePrev: boolean; // Newer (higher in list / lower index)
  canNavigateNext: boolean; // Older (lower in list / higher index)
  isNavigating?: boolean;
}

export function EventHeader({
  event,
  currentIndex,
  totalCount,
  onNavigatePrev,
  onNavigateNext,
  canNavigatePrev,
  canNavigateNext,
  isNavigating,
}: EventHeaderProps) {
  const [copiedId, setCopiedId] = useState(false);

  const handleCopyId = () => {
    navigator.clipboard.writeText(event.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const occurredDate = new Date(event.occurredAt).toLocaleString();
  const receivedDate = new Date(event.receivedAt).toLocaleString();

  return (
    <div className="space-y-4">
      {/* Navigation & Event Index Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-border text-label-md">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-text-primary">Viewing Event:</span>
          {currentIndex !== null && totalCount !== null ? (
            <span className="font-mono text-text-secondary">
              #{currentIndex} of {totalCount} {currentIndex === 1 ? "(Newest)" : ""}
            </span>
          ) : (
            <span className="font-mono text-text-muted text-[11px]">
              (Direct link)
            </span>
          )}

          <span className="text-border hidden sm:inline">•</span>

          <div className="flex items-center gap-1.5 font-mono text-[11px] text-text-muted">
            <span>ID:</span>
            <code className="text-text-secondary bg-canvas px-1.5 py-0.5 rounded border border-border">
              {event.id}
            </code>
            <button
              type="button"
              onClick={handleCopyId}
              className="text-primary hover:text-primary-hover p-1 transition-colors"
              title="Copy event ID"
            >
              {copiedId ? (
                <Check className="h-3.5 w-3.5 text-success" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
        </div>

        {/* Prev / Next controls */}
        <div className="flex items-center gap-1.5 self-end sm:self-auto">
          <Button
            variant="secondary"
            size="sm"
            onClick={onNavigatePrev}
            disabled={!canNavigatePrev || isNavigating}
            className="h-7 text-label-sm gap-1 px-2.5"
            title="Navigate to newer event"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            <span>Newer</span>
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={onNavigateNext}
            disabled={!canNavigateNext || isNavigating}
            className="h-7 text-label-sm gap-1 px-2.5"
            title="Navigate to older event"
          >
            <span>Older</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Main Exception Title & Badges */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          {event.level === "warning" && (
            <Badge variant="warning" showDot>
              warning
            </Badge>
          )}
          {event.level === "fatal" && (
            <Badge variant="error" showDot>
              fatal
            </Badge>
          )}
          {event.eventType !== "error" && (
            <Badge variant="neutral" showDot={false}>
              {event.eventType}
            </Badge>
          )}
          <span className="font-mono text-[12px] text-text-muted">
            Occurred: {occurredDate}
          </span>
          <span className="text-text-muted font-mono text-[11px]">
            (Received: {receivedDate})
          </span>
        </div>

        <h2 className="text-headline-sm font-semibold text-text-primary tracking-tight break-words">
          {event.exceptionType || "Error"}
        </h2>

        {event.message && (
          <p className="font-mono text-body-sm text-text-secondary break-words bg-canvas/60 p-3 rounded-md border border-border">
            {event.message}
          </p>
        )}
      </div>
    </div>
  );
}
