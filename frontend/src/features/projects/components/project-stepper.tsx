import React from "react";
import { CheckCircle2 } from "lucide-react";

interface ProjectStepperProps {
  currentStep: 1 | 2;
}

export function ProjectStepper({ currentStep }: ProjectStepperProps) {
  return (
    <div className="hidden sm:flex items-center gap-3 text-label-sm">
      {/* Step 1: Create Project */}
      {currentStep === 1 ? (
        <div className="flex items-center gap-1.5 font-medium text-text-primary">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[11px] font-mono text-primary-foreground">
            1
          </span>
          <span>Create Project</span>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 text-success">
          <CheckCircle2 className="h-4 w-4" />
          <span>Project created</span>
        </div>
      )}

      <span className="text-border">•</span>

      {/* Step 2: Install SDK */}
      {currentStep === 2 ? (
        <div className="flex items-center gap-1.5 font-medium text-text-primary">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[11px] font-mono text-primary-foreground">
            2
          </span>
          <span>Install SDK</span>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 text-text-muted">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-border text-[11px] font-mono text-text-secondary">
            2
          </span>
          <span>Install SDK</span>
        </div>
      )}
    </div>
  );
}
