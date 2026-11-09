"use client";

import React from "react";
import { EventListItem } from "../types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface EventListItemRowProps {
  event: EventListItem;
  isSelected: boolean;
  onSelect: () => void;
}

function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSec < 60) return "just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 30) return `${diffDays}d ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return dateString;
  }
}

export function EventListItemRow({
  event,
  isSelected,
  onSelect,
}: EventListItemRowProps) {
  const relativeTime = formatRelativeTime(event.occurredAt);
  const occurredDate = new Date(event.occurredAt).toLocaleString();
  const receivedDate = new Date(event.receivedAt).toLocaleString();
  const tooltipText = `Occurred: ${occurredDate}\nReceived: ${receivedDate}`;

  // Primary line: "exception_type: message" (one line, truncated)
  const primaryTitle = event.exceptionType
    ? `${event.exceptionType}: ${event.message || "(No message)"}`
    : event.message || "(No exception info)";

  // Secondary line: "release · environment"
  const secondaryParts = [event.release, event.environment].filter(Boolean);
  const secondaryText = secondaryParts.join(" · ");

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full text-left p-3.5 transition-colors border-b border-border flex flex-col gap-1.5 focus:outline-none focus:bg-canvas/80",
        isSelected
          ? "bg-primary/5 border-l-4 border-l-primary pl-[10px]"
          : "hover:bg-canvas/60 border-l-4 border-l-transparent"
      )}
    >
      {/* Top Row: Primary Title and Relative Time */}
      <div className="flex items-start justify-between gap-3 w-full">
        <span
          className={cn(
            "text-body-sm font-medium truncate flex-1 min-w-0",
            isSelected ? "text-primary font-semibold" : "text-text-primary"
          )}
          title={primaryTitle}
        >
          {primaryTitle}
        </span>

        <span
          className="font-mono text-[11px] text-text-muted shrink-0 cursor-help"
          title={tooltipText}
        >
          {relativeTime}
        </span>
      </div>

      {/* Bottom Row: Secondary Line + Badges */}
      <div className="flex items-center justify-between gap-2 w-full text-[12px]">
        <span className="font-mono text-text-secondary truncate text-[11px]">
          {secondaryText || "—"}
        </span>

        <div className="flex items-center gap-1.5 shrink-0">
          {event.eventType !== "error" && (
            <Badge variant="neutral" showDot={false} className="text-[10px] px-1.5 py-0">
              {event.eventType}
            </Badge>
          )}

          {event.level === "warning" && (
            <Badge variant="warning" showDot className="text-[10px] px-1.5 py-0">
              warning
            </Badge>
          )}

          {event.level === "fatal" && (
            <Badge variant="error" showDot className="text-[10px] px-1.5 py-0">
              fatal
            </Badge>
          )}
        </div>
      </div>
    </button>
  );
}
