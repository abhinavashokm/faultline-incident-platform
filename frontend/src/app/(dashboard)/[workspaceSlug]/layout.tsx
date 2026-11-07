"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { useCurrentWorkspace } from "@/features/workspace/hooks";
import { useListProjects } from "@/features/projects/hooks";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const params = useParams();
  const workspaceSlug = (params.workspaceSlug as string) || "";
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const { data: workspace } = useCurrentWorkspace();
  const workspaceName = workspace?.name ?? workspaceSlug;

  const { data: projects, isLoading: projectsLoading } = useListProjects();

  // If the workspace has no projects, redirect to onboarding.
  // Use router.replace so the dashboard URL is not added to history.
  useEffect(() => {
    if (!projectsLoading && projects && projects.length === 0) {
      router.replace("/onboarding/create-project");
    }
  }, [projectsLoading, projects, router]);

  // Show a full-page spinner while loading or while the redirect is pending
  // (projects.length === 0 but the router hasn't navigated yet).
  if (projectsLoading || (projects && projects.length === 0)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
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
