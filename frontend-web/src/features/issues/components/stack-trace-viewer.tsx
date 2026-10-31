"use client";

import React, { useState } from "react";
import { StackFrame } from "../types";
import { ChevronDown, ChevronRight, Code2, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

interface StackTraceViewerProps {
  frames: StackFrame[];
}

export function StackTraceViewer({ frames }: StackTraceViewerProps) {
  const [showVendorFrames, setShowVendorFrames] = useState(false);

  const vendorFrameCount = frames.filter((f) => !f.inApp).length;
  const inAppFrameCount = frames.filter((f) => f.inApp).length;

  return (
    <div className="rounded-lg border border-border bg-card shadow-level-1 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-border bg-canvas/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Code2 className="h-4 w-4 text-primary" />
          <h3 className="text-title-md font-semibold text-text-primary">
            Exception Stack Trace
          </h3>
          <span className="font-mono text-label-sm text-text-muted">
            ({inAppFrameCount} in-app, {vendorFrameCount} library frames)
          </span>
        </div>

        {vendorFrameCount > 0 && (
          <button
            type="button"
            onClick={() => setShowVendorFrames(!showVendorFrames)}
            className="inline-flex items-center gap-1.5 text-label-md font-medium text-primary hover:underline select-none"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>
              {showVendorFrames
                ? "Hide library / vendor frames"
                : `Expand ${vendorFrameCount} library frames`}
            </span>
            {showVendorFrames ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </button>
        )}
      </div>

      {/* Frame List */}
      <div className="divide-y divide-border bg-canvas">
        {frames.map((frame, idx) => {
          if (!frame.inApp && !showVendorFrames) {
            return null;
          }

          return (
            <div
              key={idx}
              className={cn(
                "transition-colors",
                frame.inApp
                  ? "bg-card border-l-4 border-l-primary py-3 px-4"
                  : "bg-canvas/40 opacity-70 hover:opacity-100 py-2.5 px-4"
              )}
            >
              {/* Frame Location Header */}
              <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-[12px] mb-2">
                <div className="flex items-center gap-2 truncate">
                  <span
                    className={cn(
                      "font-semibold truncate",
                      frame.inApp ? "text-text-primary" : "text-text-secondary"
                    )}
                  >
                    {frame.file}
                  </span>
                  <span className="text-text-muted">in</span>
                  <span className="font-medium text-primary">{frame.function}</span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-text-muted">line {frame.line}</span>
                  {frame.inApp ? (
                    <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-primary-tint border border-primary-subdued text-primary font-semibold">
                      In-App
                    </span>
                  ) : (
                    <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-muted border border-border text-text-muted">
                      Vendor
                    </span>
                  )}
                </div>
              </div>

              {/* Context Code Block */}
              {frame.contextLines && frame.contextLines.length > 0 && (
                <div className="rounded-md border border-border bg-canvas font-mono text-[12px] overflow-x-auto shadow-inner py-1">
                  {frame.contextLines.map((ctx) => (
                    <div
                      key={ctx.line}
                      className={cn(
                        "flex items-center leading-6 px-2",
                        ctx.isError
                          ? "bg-error-container/60 text-error font-semibold border-l-2 border-l-error"
                          : "text-text-primary hover:bg-muted/40"
                      )}
                    >
                      {/* Line Number (40px width, right-aligned per DESIGN.md) */}
                      <span className="w-10 pr-3 select-none text-right text-text-muted shrink-0 text-[11px]">
                        {ctx.line}
                      </span>
                      <pre className="font-mono whitespace-pre overflow-x-auto py-0.5">
                        {ctx.code}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

