"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const workspaceSlug = (params.workspaceSlug as string) || "acme-cloud";
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-canvas text-text-primary">
      {/* Sidebar: Fixed 240px desktop, 56px tablet, off-canvas mobile */}
      <Sidebar
        workspaceSlug={workspaceSlug}
        isMobileOpen={mobileMenuOpen}
        onMobileClose={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex flex-col transition-all duration-200 ease-in-out md:pl-14 lg:pl-60">
        <Topbar
          workspaceSlug={workspaceSlug}
          onMobileMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)}
        />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

