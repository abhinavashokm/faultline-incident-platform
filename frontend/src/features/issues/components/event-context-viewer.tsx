"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, Braces, Copy, Check } from "lucide-react";

interface EventContextViewerProps {
  context?: Record<string, unknown> | null;
}

export function EventContextViewer({ context }: EventContextViewerProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [copied, setCopied] = useState(false);

  if (!context || Object.keys(context).length === 0) {
    return null;
  }

  const jsonString = JSON.stringify(context, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border border-border bg-card shadow-level-1 overflow-hidden">
      {/* Header Toggle */}
      <div className="px-4 py-2.5 bg-canvas/40 border-b border-border flex items-center justify-between">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 text-title-sm font-semibold text-text-primary hover:text-text-primary/80 transition-colors"
        >
          <Braces className="h-4 w-4 text-primary" />
          <span>Context Data ({Object.keys(context).length} keys)</span>
          {isOpen ? (
            <ChevronDown className="h-4 w-4 text-text-muted" />
          ) : (
            <ChevronRight className="h-4 w-4 text-text-muted" />
          )}
        </button>

        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1 text-label-sm text-primary hover:underline"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-success" />
              <span className="text-success">Copied JSON</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              <span>Copy JSON</span>
            </>
          )}
        </button>
      </div>

      {/* Collapsible Content */}
      {isOpen && (
        <div className="p-4 bg-canvas/20">
          <pre className="font-mono text-body-sm text-text-primary bg-card p-3 rounded-md border border-border overflow-x-auto max-h-96">
            <code>{jsonString}</code>
          </pre>
        </div>
      )}
    </div>
  );
}
