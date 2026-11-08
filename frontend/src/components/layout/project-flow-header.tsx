"use client";

import React from "react";
import { Logo } from "@/components/brand/logo";
import { ProjectStepper } from "@/features/projects/components/project-stepper";

interface ProjectFlowHeaderProps {
  currentStep: 1 | 2;
  workspaceName?: string;
}

export function ProjectFlowHeader({ currentStep, workspaceName }: ProjectFlowHeaderProps) {
  return (
    <header className="border-b border-border bg-card px-6 py-4">
      <div className="max-w-5xl mx-auto flex items-center justify-between">
        <Logo size={26} />
        <ProjectStepper currentStep={currentStep} />
        <div className="text-label-sm text-text-secondary font-mono">
          {workspaceName ?? "—"}
        </div>
      </div>
    </header>
  );
}
