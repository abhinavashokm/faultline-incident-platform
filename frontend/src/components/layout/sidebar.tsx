"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderKanban,
  AlertOctagon,
  Gauge,
  Bell,
  Flame,
  SearchCode,
  X,
  Server,
} from "lucide-react";
import { Logo, LogoMark } from "@/components/brand/logo";
import { cn } from "@/lib/utils";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeVariant?: "default" | "error" | "warning";
}

interface SidebarProps {
  workspaceSlug: string;
  isMobileOpen: boolean;
  onMobileClose: () => void;
}

export function Sidebar({
  workspaceSlug,
  isMobileOpen,
  onMobileClose,
}: SidebarProps) {
  const pathname = usePathname();

  const navItems: NavItem[] = [
    {
      name: "Overview",
      href: `/${workspaceSlug}/overview`,
      icon: LayoutDashboard,
    },
    {
      name: "Projects",
      href: `/${workspaceSlug}/projects`,
      icon: FolderKanban,
    },
    {
      name: "Issues",
      href: `/${workspaceSlug}/issues`,
      icon: AlertOctagon,
      badge: "14",
      badgeVariant: "warning",
    },
    {
      name: "Performance",
      href: `/${workspaceSlug}/performance`,
      icon: Gauge,
    },
    {
      name: "Alerts",
      href: `/${workspaceSlug}/alerts`,
      icon: Bell,
    },
    {
      name: "Incidents",
      href: `/${workspaceSlug}/incidents`,
      icon: Flame,
      badge: "2",
      badgeVariant: "error",
    },
    {
      name: "Investigations",
      href: `/${workspaceSlug}/investigations`,
      icon: SearchCode,
      badge: "AI",
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden"
          onClick={onMobileClose}
        />
      )}

      {/* Sidebar Container:
          - Desktop: fixed 240px width (w-60)
          - Tablet: 56px icon rail (md:w-14 lg:w-60)
          - Mobile: off-canvas drawer (fixed inset-y-0 left-0 -translate-x-full lg:translate-x-0)
      */}
      <aside
        className={cn(
          "fixed top-0 bottom-0 left-0 z-50 flex flex-col border-r border-border bg-card transition-all duration-200 ease-in-out select-none",
          // Mobile state
          isMobileOpen ? "translate-x-0 w-60 shadow-level-3" : "-translate-x-full",
          // Tablet & Desktop state
          "md:translate-x-0 md:w-14 lg:w-60"
        )}
      >
        {/* Brand Header */}
        <div className="flex h-14 items-center justify-between px-3.5 border-b border-border">
          <Link
            href={`/${workspaceSlug}/overview`}
            className="flex items-center gap-2.5 overflow-hidden"
          >
            {/* Expanded on mobile and desktop, mark only on tablet */}
            <div className="hidden lg:block">
              <Logo size={24} />
            </div>
            <div className="block lg:hidden md:block">
              <LogoMark size={24} />
            </div>
            <div className="block md:hidden">
              <Logo size={24} />
            </div>
          </Link>

          {/* Mobile close button */}
          <button
            type="button"
            onClick={onMobileClose}
            className="p-1 rounded text-text-muted hover:text-text-primary md:hidden"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.href ||
              (item.href.endsWith("/overview") && pathname === `/${workspaceSlug}`);

            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={onMobileClose}
                className={cn(
                  "group relative flex items-center gap-3 rounded-md px-2.5 py-2 text-body-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary-tint text-primary font-semibold border-l-2 border-primary"
                    : "text-text-secondary hover:bg-canvas hover:text-text-primary"
                )}
                title={item.name}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 shrink-0 transition-colors",
                    isActive ? "text-primary" : "text-text-secondary group-hover:text-text-primary"
                  )}
                />

                {/* Text visible in expanded mode (desktop & mobile drawer) */}
                <span className="truncate md:hidden lg:inline">{item.name}</span>

                {/* Badge if present */}
                {item.badge && (
                  <span
                    className={cn(
                      "ml-auto font-mono text-[10px] px-1.5 py-0.2 rounded-full font-semibold md:hidden lg:inline-flex",
                      item.badgeVariant === "error"
                        ? "bg-error-container text-error"
                        : item.badgeVariant === "warning"
                        ? "bg-warning-container text-warning-foreground"
                        : "bg-ai-container text-ai-foreground"
                    )}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Workspace Footer Indicator */}
        <div className="p-3 border-t border-border bg-canvas/50">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded bg-card border border-border flex items-center justify-center text-primary shrink-0 shadow-level-1">
              <Server className="h-3.5 w-3.5" />
            </div>
            <div className="min-w-0 flex-1 md:hidden lg:block">
              <div className="text-label-md font-semibold text-text-primary truncate">
                Acme Cloud
              </div>
              <div className="text-[11px] font-mono text-text-muted truncate">
                cluster: us-east-k8s
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

