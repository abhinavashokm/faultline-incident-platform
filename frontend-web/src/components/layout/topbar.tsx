"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Menu,
  Search,
  ChevronDown,
  Building2,
  FolderOpen,
  User,
  LogOut,
  Settings,
  Bell,
  Moon,
  Sun,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface TopbarProps {
  workspaceSlug: string;
  onMobileMenuToggle: () => void;
}

export function Topbar({ workspaceSlug, onMobileMenuToggle }: TopbarProps) {
  const router = useRouter();
  const [selectedProject, setSelectedProject] = useState("all");
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [isDark, setIsDark] = useState(false);

  const toggleDarkMode = () => {
    if (typeof document !== "undefined") {
      document.documentElement.classList.toggle("dark");
      setIsDark(!isDark);
    }
  };

  const handleLogout = () => {
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-border bg-card/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-card/75">
      {/* Left: Mobile trigger & Selectors */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMobileMenuToggle}
          className="p-1.5 rounded-md text-text-secondary hover:bg-canvas hover:text-text-primary md:hidden"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Workspace Switcher */}
        <div className="flex items-center gap-1.5">
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1.5 rounded-md border border-border bg-canvas text-label-md font-medium text-text-primary">
            <Building2 className="h-3.5 w-3.5 text-primary" />
            <span className="font-semibold">Acme Cloud</span>
            <span className="text-text-muted text-[10px] font-mono px-1 rounded bg-card border border-border">
              prod
            </span>
          </div>

          <span className="text-border hidden sm:inline">/</span>

          {/* Project Selector */}
          <div className="w-36 sm:w-44">
            <Select value={selectedProject} onValueChange={setSelectedProject}>
              <SelectTrigger className="h-8 text-label-md bg-canvas">
                <div className="flex items-center gap-1.5 truncate">
                  <FolderOpen className="h-3.5 w-3.5 text-text-muted shrink-0" />
                  <SelectValue placeholder="Project" />
                </div>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Projects (4)</SelectItem>
                <SelectItem value="payments-api">Payments API</SelectItem>
                <SelectItem value="auth-gateway">Auth Gateway</SelectItem>
                <SelectItem value="billing-worker">Billing Worker</SelectItem>
                <SelectItem value="processing-worker">Processing Worker</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Middle: Global Search Bar with ⌘K chip */}
      <div className="hidden md:flex flex-1 max-w-md mx-4">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-muted" />
          <input
            type="text"
            placeholder="Search issues, trace IDs, releases, or documentation..."
            className="w-full h-8 pl-8 pr-12 rounded-md border border-border bg-canvas text-body-sm text-text-primary placeholder:text-text-muted shadow-level-1 focus:border-primary focus:ring-2 focus:ring-primary-subdued focus:outline-none transition-all"
          />
          <kbd className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none inline-flex h-5 select-none items-center gap-0.5 rounded border border-border bg-card px-1.5 font-mono text-[10px] font-medium text-text-muted shadow-level-1">
            ⌘K
          </kbd>
        </div>
      </div>

      {/* Right: Actions, Notifications, User Menu */}
      <div className="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          onClick={toggleDarkMode}
          className="p-1.5 rounded-md text-text-secondary hover:bg-canvas hover:text-text-primary transition-colors"
          title="Toggle color theme"
          aria-label="Toggle theme"
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>

        <button
          type="button"
          className="relative p-1.5 rounded-md text-text-secondary hover:bg-canvas hover:text-text-primary transition-colors"
          aria-label="View notifications"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-error" />
        </button>

        {/* User Menu Dropdown Trigger */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="flex items-center gap-2 p-1 rounded-md hover:bg-canvas border border-transparent hover:border-border transition-all"
            aria-expanded={userMenuOpen}
          >
            <div className="h-7 w-7 rounded-full bg-primary-tint border border-primary/20 flex items-center justify-center text-primary font-semibold text-[12px] font-mono">
              EV
            </div>
            <div className="hidden lg:flex flex-col text-left">
              <span className="text-label-md font-semibold text-text-primary leading-none">
                Elena Vance
              </span>
              <span className="text-[10px] text-text-secondary font-mono leading-none mt-0.5">
                Lead SRE
              </span>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-text-muted hidden sm:block" />
          </button>

          {/* User Menu Popover */}
          {userMenuOpen && (
            <div
              className="absolute right-0 mt-2 w-56 rounded-md border border-border bg-card p-1 shadow-level-3 z-50 animate-in fade-in-0 zoom-in-95"
              onClick={() => setUserMenuOpen(false)}
            >
              <div className="p-2 border-b border-border">
                <p className="text-label-md font-semibold text-text-primary">
                  Elena Vance
                </p>
                <p className="text-[11px] font-mono text-text-muted truncate">
                  elena@acme-cloud.io
                </p>
                <div className="mt-1 flex items-center gap-1 text-[10px] text-success">
                  <ShieldCheck className="h-3 w-3" />
                  <span>Workspace Admin</span>
                </div>
              </div>

              <div className="py-1">
                <Link
                  href={`/${workspaceSlug}/settings`}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded text-body-sm text-text-secondary hover:bg-canvas hover:text-text-primary"
                >
                  <Settings className="h-4 w-4 text-text-muted" />
                  <span>Workspace Settings</span>
                </Link>
                <Link
                  href={`/${workspaceSlug}/profile`}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded text-body-sm text-text-secondary hover:bg-canvas hover:text-text-primary"
                >
                  <User className="h-4 w-4 text-text-muted" />
                  <span>Personal Settings</span>
                </Link>
              </div>

              <div className="p-1 border-t border-border">
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded text-body-sm text-error hover:bg-error-container/40"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Log out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

