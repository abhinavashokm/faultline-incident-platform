"use client";

import React from "react";
import { useParams } from "next/navigation";
import { ProjectCreateForm } from "@/features/projects/components/project-create-form";

export default function CreateProjectPage() {
  const params = useParams();
  const workspaceSlug = (params.workspaceSlug as string) || "";

  return (
    <div className="max-w-3xl w-full mx-auto py-4 sm:py-8">
      <ProjectCreateForm workspaceSlug={workspaceSlug} />
    </div>
  );
}
