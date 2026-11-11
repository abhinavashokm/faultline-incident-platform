"use client";

import React from "react";
import { RefreshCw, SlidersHorizontal, AlertCircle } from "lucide-react";
import { PerformanceFilterOptions } from "../types";

export type PresetRange = "1h" | "6h" | "24h" | "7d" | "custom";

interface PerformanceFilterBarProps {
  filters?: PerformanceFilterOptions;
  activePreset: PresetRange;
  onSelectPreset: (preset: PresetRange) => void;
  environment: string;
  onChangeEnvironment: (env: string) => void;
  release: string;
  onChangeRelease: (rel: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  mockState?: "normal" | "empty" | "error" | "truncated";
  onChangeMockState: (state: "normal" | "empty" | "error" | "truncated") => void;
  customFrom: string;
  customTo: string;
  onChangeCustomFrom: (val: string) => void;
  onChangeCustomTo: (val: string) => void;
  onApplyCustomRange: () => void;
  rangeValidationError?: string | null;
}

export function PerformanceFilterBar({
  filters,
  activePreset,
  onSelectPreset,
  environment,
  onChangeEnvironment,
  release,
  onChangeRelease,
  onRefresh,
  isRefreshing,
  mockState = "normal",
  onChangeMockState,
  customFrom,
  customTo,
  onChangeCustomFrom,
  onChangeCustomTo,
  onApplyCustomRange,
  rangeValidationError,
}: PerformanceFilterBarProps) {
  const [showCustomRange, setShowCustomRange] = React.useState(activePreset === "custom");

  const presets: { id: PresetRange; label: string }[] = [
    { id: "1h", label: "1h" },
    { id: "6h", label: "6h" },
    { id: "24h", label: "24h" },
    { id: "7d", label: "7d" },
  ];

  return (
    <div className="bg-card p-3 rounded-2xl border border-border shadow-xs space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left: Range presets, Environment dropdown, Release dropdown */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Segmented Control for Time Presets */}
          <div className="inline-flex items-center p-0.5 rounded-lg bg-surface-container-low border border-border">
            {presets.map((p) => {
              const isActive = activePreset === p.id && !showCustomRange;
              return (
                <button
                  key={p.id}
                  onClick={() => {
                    setShowCustomRange(false);
                    onSelectPreset(p.id);
                  }}
                  className={`px-3 py-1 rounded-md text-xs transition-colors ${
                    isActive
                      ? "bg-card text-primary font-semibold shadow-xs"
                      : "text-text-secondary hover:text-text-primary font-medium"
                  }`}
                >
                  {p.label}
                </button>
              );
            })}
            <button
              onClick={() => {
                setShowCustomRange(!showCustomRange);
                if (!showCustomRange) onSelectPreset("custom");
              }}
              className={`px-2.5 py-1 rounded-md text-xs transition-colors flex items-center gap-1 ${
                showCustomRange
                  ? "bg-card text-primary font-semibold shadow-xs"
                  : "text-text-secondary hover:text-text-primary font-medium"
              }`}
            >
              <SlidersHorizontal className="w-3 h-3" />
              <span>Custom</span>
            </button>
          </div>

          {/* Environment dropdown */}
          <select
            value={environment}
            onChange={(e) => onChangeEnvironment(e.target.value)}
            className="appearance-none bg-surface-container-low hover:bg-surface-container text-text-primary text-xs font-medium px-3 py-1.5 rounded-lg border border-border cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">Environment: All</option>
            {filters?.environments.map((env) => (
              <option key={env} value={env}>
                Environment: {env}
              </option>
            ))}
          </select>

          {/* Release dropdown */}
          <select
            value={release}
            onChange={(e) => onChangeRelease(e.target.value)}
            className="appearance-none bg-surface-container-low hover:bg-surface-container text-text-primary text-xs font-medium px-3 py-1.5 rounded-lg border border-border cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">Release: All</option>
            {filters?.releases.map((rel) => (
              <option key={rel} value={rel}>
                Release: {rel}
              </option>
            ))}
          </select>
        </div>

        {/* Right: Refresh button and Mock Simulator switcher */}
        <div className="flex items-center gap-2.5">
          {/* Mock State Simulator (allows forcing states) */}
          <div className="hidden lg:flex items-center p-0.5 rounded-lg bg-surface-container-low border border-border text-xs">
            <span className="px-2 text-[10px] uppercase font-semibold text-text-secondary">Mock:</span>
            {(["normal", "empty", "error", "truncated"] as const).map((state) => (
              <button
                key={state}
                onClick={() => onChangeMockState(state)}
                className={`px-2 py-0.5 rounded text-[11px] capitalize transition-colors ${
                  mockState === state
                    ? "bg-card text-primary font-semibold shadow-xs"
                    : "text-text-secondary hover:text-text-primary"
                }`}
              >
                {state}
              </button>
            ))}
          </div>

          {/* Refresh Action */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-low hover:bg-surface-container text-xs font-medium text-text-primary border border-border transition-colors disabled:opacity-50"
            title="Refresh metrics with current pinned time"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-primary" : "text-text-secondary"}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Custom Date Range Picker Accordion */}
      {showCustomRange && (
        <div className="pt-2 border-t border-border/60 flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-text-secondary">From (UTC):</span>
            <input
              type="datetime-local"
              value={customFrom}
              onChange={(e) => onChangeCustomFrom(e.target.value)}
              className="bg-surface-container-low border border-border rounded-lg px-2.5 py-1 text-xs font-mono text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-text-secondary">To (UTC):</span>
            <input
              type="datetime-local"
              value={customTo}
              onChange={(e) => onChangeCustomTo(e.target.value)}
              className="bg-surface-container-low border border-border rounded-lg px-2.5 py-1 text-xs font-mono text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <button
            onClick={onApplyCustomRange}
            disabled={Boolean(rangeValidationError)}
            className="px-3 py-1 rounded-lg bg-primary text-white font-semibold text-xs hover:bg-primary/90 transition-colors disabled:opacity-40"
          >
            Apply Range
          </button>

          {rangeValidationError && (
            <div className="flex items-center gap-1 text-xs text-error font-medium">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{rangeValidationError}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
