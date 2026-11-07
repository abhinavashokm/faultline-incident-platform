"use client";

import React from "react";
import { Sparkles, BrainCircuit, CheckCircle2, AlertOctagon } from "lucide-react";
import { InvestigationResult } from "../types";

// TODO(mock): Investigation / AI Service integration pending; using mock root cause synthesis
interface AiInvestigationCardProps {
  investigation?: InvestigationResult;
  onRunInvestigation?: () => void;
}

export function AiInvestigationCard({
  investigation,
  onRunInvestigation,
}: AiInvestigationCardProps) {
  if (!investigation) {
    return (
      <div className="rounded-lg border border-ai/30 bg-ai-container/40 p-5 shadow-level-1 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-ai-container text-ai-foreground border border-ai/20 shadow-level-1 shrink-0">
            <Sparkles className="h-5 w-5 text-ai" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-body-sm font-semibold text-text-primary">
                AI Root Cause Investigation
              </h3>
              <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-full bg-ai-container text-ai-foreground font-semibold border border-ai/30">
                Preview
              </span>
            </div>
            <p className="text-body-sm text-text-secondary mt-0.5">
              Synthesize telemetry anomalies, exception traces, and git commits to determine probable cause.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onRunInvestigation}
          className="inline-flex items-center gap-1.5 rounded-md bg-ai px-3.5 py-2 text-label-md font-medium text-white hover:opacity-90 shadow-level-1 shrink-0 transition-opacity"
        >
          <BrainCircuit className="h-4 w-4" />
          <span>Investigate with AI</span>
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-ai/30 bg-card shadow-level-1 overflow-hidden">
      {/* AI Header */}
      <div className="p-4 bg-ai-container/40 border-b border-ai/20 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded bg-card border border-ai/20 shadow-level-1">
            <Sparkles className="h-4 w-4 text-ai" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-title-md font-semibold text-text-primary">
                AI Root Cause Synthesis
              </h3>
              <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-full bg-ai-container text-ai-foreground font-semibold border border-ai/30">
                Preview
              </span>
            </div>
            <span className="text-[11px] text-text-secondary">
              Evidence synthesized across code commits, connection pool traces, and ASGI events
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-card px-2.5 py-1 rounded-md border border-ai/20 shadow-level-1">
          <span className="text-[11px] text-text-secondary font-medium">Confidence:</span>
          <span className="font-mono text-[12px] font-semibold text-ai-foreground">
            {investigation.confidence}%
          </span>
        </div>
      </div>

      {/* Synthesis Content */}
      <div className="p-5 space-y-4 text-body-sm">
        {/* Likely Cause */}
        <div>
          <h4 className="font-semibold text-text-primary flex items-center gap-1.5 mb-1 text-[13px]">
            <AlertOctagon className="h-4 w-4 text-error" />
            <span>Likely Cause</span>
          </h4>
          <p className="text-text-secondary leading-relaxed pl-5">
            {investigation.likelyCause}
          </p>
        </div>

        {/* Recommended Fix */}
        <div>
          <h4 className="font-semibold text-text-primary flex items-center gap-1.5 mb-1 text-[13px]">
            <CheckCircle2 className="h-4 w-4 text-success" />
            <span>Recommended Fix</span>
          </h4>
          <p className="text-text-secondary leading-relaxed pl-5 mb-2">
            {investigation.recommendation}
          </p>
        </div>

        {/* Mitigation Plan */}
        <div className="p-3.5 rounded-md bg-canvas border border-border">
          <span className="text-[11px] font-mono font-semibold uppercase text-text-muted block mb-1">
            Immediate Mitigation Strategy
          </span>
          <p className="text-text-secondary text-[13px]">
            {investigation.mitigationPlan}
          </p>
        </div>
      </div>
    </div>
  );
}

