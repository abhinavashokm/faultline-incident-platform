"use client";

import React from "react";
import { Activity } from "lucide-react";

interface EventsFrequencyChartProps {
  timeline: { time: string; count: number }[];
  totalEvents: number;
}

export function EventsFrequencyChart({
  timeline,
  totalEvents,
}: EventsFrequencyChartProps) {
  if (!timeline || timeline.length === 0) return null;

  const maxCount = Math.max(...timeline.map((t) => t.count), 1);

  return (
    <div className="rounded-lg border border-border bg-card p-4 shadow-level-1">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-error" />
          <h3 className="text-body-sm font-semibold text-text-primary">
            Event Frequency Timeline (Last 60 Minutes)
          </h3>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px] text-text-secondary">
          <span>Total:</span>
          <span className="font-semibold text-text-primary tabular-nums">
            {totalEvents.toLocaleString()} occurrences
          </span>
        </div>
      </div>

      <div className="h-28 flex items-end justify-between gap-2 pt-2 border-b border-border">
        {timeline.map((point) => {
          const heightPercent = Math.max((point.count / maxCount) * 100, 10);
          return (
            <div
              key={point.time}
              className="flex-1 flex flex-col items-center gap-1.5 group relative"
            >
              {/* Tooltip */}
              <div className="absolute -top-8 hidden group-hover:flex flex-col items-center z-10 pointer-events-none">
                <div className="rounded bg-text-primary text-canvas px-2 py-0.5 text-[10px] font-mono shadow-level-2 whitespace-nowrap">
                  {point.time}: {point.count} events
                </div>
              </div>

              {/* Bar */}
              <div className="w-full flex flex-col justify-end h-20">
                <div
                  style={{ height: `${heightPercent}%` }}
                  className="w-full rounded-t-sm bg-error/75 group-hover:bg-error transition-all"
                />
              </div>

              <span className="font-mono text-[10px] text-text-muted">
                {point.time}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

