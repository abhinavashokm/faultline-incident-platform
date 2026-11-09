"use client";

import React, { useState } from "react";
import { StackFrame } from "../types";
import { ChevronDown, ChevronRight, Code2, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

interface EventStackTraceProps {
  frames: StackFrame[];
}

export function EventStackTrace({ frames }: EventStackTraceProps) {
  const [showAllFrames, setShowAllFrames] = useState(false);

  if (!frames || frames.length === 0) {
    return null;
  }

  // Reverse so that the most recent call is displayed first
  const reversedFrames = [...frames].reverse();

  const inAppFrameCount = frames.filter((f) => f.inApp).length;
  const vendorFrameCount = frames.filter((f) => !f.inApp).length;

  return (
    <div className="rounded-lg border border-border bg-card shadow-level-1 overflow-hidden">
      {/* Header */}
      <div className="p-3.5 border-b border-border bg-canvas/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
        <div className="flex items-center gap-2">
          <Code2 className="h-4 w-4 text-primary" />
          <h3 className="text-title-sm font-semibold text-text-primary">
            Stack Trace
          </h3>
          <span className="font-mono text-label-sm text-text-muted">
            ({inAppFrameCount} in-app, {vendorFrameCount} library frames)
          </span>
        </div>

        {vendorFrameCount > 0 && (
          <button
            type="button"
            onClick={() => setShowAllFrames(!showAllFrames)}
            className="inline-flex items-center gap-1.5 text-label-sm font-medium text-primary hover:underline select-none"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>
              {showAllFrames
                ? "Collapse library frames"
                : `Show all frames (+${vendorFrameCount} library)`}
            </span>
            {showAllFrames ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </button>
        )}
      </div>

      {/* Frame List */}
      <div className="divide-y divide-border bg-canvas">
        {reversedFrames.map((frame, idx) => {
          if (!frame.inApp && !showAllFrames) {
            return null;
          }

          return (
            <div
              key={idx}
              className={cn(
                "transition-colors text-label-sm font-mono",
                frame.inApp
                  ? "bg-card border-l-4 border-l-primary py-2.5 px-3.5"
                  : "bg-canvas/30 opacity-70 hover:opacity-100 py-2 px-3.5 border-l-4 border-l-transparent"
              )}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <span className="font-medium text-text-primary truncate">
                  {frame.function || "<anonymous>"}
                </span>
                <span className="text-[11px] text-text-muted shrink-0">
                  {frame.file}
                  {frame.line !== null && frame.line !== undefined ? `:${frame.line}` : ""}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
