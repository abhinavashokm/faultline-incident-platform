import React from "react";
import Link from "next/link";
import { Logo } from "@/components/brand/logo";

interface AuthShellProps {
  children: React.ReactNode;
  subtitle?: string;
  title?: string;
  footerContent?: React.ReactNode;
}

export function AuthShell({
  children,
  title,
  subtitle,
  footerContent,
}: AuthShellProps) {
  return (
    <div className="min-h-screen flex flex-col justify-between bg-canvas px-4 py-8">
      {/* Top micro status bar */}
      <header className="w-full max-w-5xl mx-auto flex items-center justify-between py-2 text-label-sm text-text-muted">
        <Link href="/login" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <Logo size={24} />
        </Link>
        <div className="flex items-center gap-4">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-card border border-border text-label-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-success"></span>
            <span className="text-text-secondary">All Systems Operational</span>
          </div>
          <span className="hidden sm:inline font-mono text-[11px] text-text-muted">v1.0.0</span>
        </div>
      </header>

      {/* Centered Auth Card */}
      <main className="w-full flex-1 flex items-center justify-center py-6">
        <div className="w-full max-w-[420px]">
          <div className="bg-card rounded-lg border border-border p-7 sm:p-8 shadow-level-1 relative">
            <div className="flex flex-col items-center text-center mb-6">
              <div className="mb-4">
                <Logo size={36} showWordmark={false} />
              </div>
              {title && (
                <h1 className="text-headline-sm font-semibold tracking-tight text-text-primary">
                  {title}
                </h1>
              )}
              {subtitle && (
                <p className="text-body-sm text-text-secondary mt-1">
                  {subtitle}
                </p>
              )}
            </div>

            {children}
          </div>

          {footerContent && (
            <div className="mt-4 text-center text-body-sm text-text-secondary">
              {footerContent}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-5xl mx-auto py-3 text-center text-label-sm text-text-muted border-t border-border/60">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>&copy; {new Date().getFullYear()} Faultline Inc. All rights reserved.</span>
          <div className="flex items-center gap-4 text-text-secondary">
            <span className="hover:text-text-primary cursor-pointer">Security</span>
            <span className="hover:text-text-primary cursor-pointer">Privacy</span>
            <span className="hover:text-text-primary cursor-pointer">Terms</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

