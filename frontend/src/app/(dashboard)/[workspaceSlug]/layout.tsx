"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter, usePathname } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { ProjectFlowHeader } from "@/components/layout/project-flow-header";
import { useCurrentWorkspace } from "@/features/workspace/hooks";
import { useListProjects } from "@/features/projects/hooks";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const params = useParams();
  const pathname = usePathname();
  const workspaceSlug = (params.workspaceSlug as string) || "";
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const { data: workspace } = useCurrentWorkspace();
  const workspaceName = workspace?.name ?? workspaceSlug;

  const { data: projects, isLoading: projectsLoading } = useListProjects();

  const isProjectsNew = pathname.endsWith("/projects/new");
  const isProjectsSetup = pathname.includes("/projects/") && pathname.endsWith("/setup");
  const isFocusedFlow = isProjectsNew || isProjectsSetup;

  // If the workspace has no projects, redirect to the new project creation page.
  // Use router.replace so the previous dashboard URL is not left in history.
  // Avoid redirecting if the user is already on /projects/new or /projects/{slug}/setup.
  useEffect(() => {
    if (!projectsLoading && projects && projects.length === 0 && !isFocusedFlow) {
      router.replace(`/${workspaceSlug}/projects/new`);
    }
  }, [projectsLoading, projects, isFocusedFlow, workspaceSlug, router]);

  // Show a full-page spinner while loading or while the zero-projects redirect is pending
  if (projectsLoading || (!isFocusedFlow && projects && projects.length === 0)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Focused full-width layout for /projects/new and /projects/{slug}/setup
  if (isFocusedFlow) {
    const currentStep = isProjectsNew ? 1 : 2;
    return (
      <div className="min-h-screen bg-canvas text-text-primary flex flex-col justify-between">
        <ProjectFlowHeader
          currentStep={currentStep}
          workspaceName={workspaceName}
        />
        <main className="flex-1 px-4 py-8 sm:py-12 max-w-5xl w-full mx-auto">
          {children}
        </main>
        <footer className="border-t border-border bg-card py-3 px-6 text-center text-label-sm text-text-muted">
          Faultline Project Telemetry &bull; High Precision Ingestion
        </footer>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-canvas text-text-primary">
      {/* Sidebar: Fixed 240px desktop, 56px tablet, off-canvas mobile */}
      <Sidebar
        workspaceSlug={workspaceSlug}
        workspaceName={workspaceName}
        isMobileOpen={mobileMenuOpen}
        onMobileClose={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex flex-col transition-all duration-200 ease-in-out md:pl-14 lg:pl-60">
        <Topbar
          workspaceSlug={workspaceSlug}
          workspaceName={workspaceName}
          onMobileMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)}
        />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
