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
      <header className="w-full max-w-5xl mx-auto flex items-center py-2">
        <Link href="/login" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <Logo size={24} />
        </Link>
      </header>

      {/* Centered Auth Card */}
      <main className="w-full flex-1 flex items-center justify-center py-6">
        <div className="w-full max-w-[420px]">
          <div className="bg-card rounded-lg border border-border p-7 sm:p-8 shadow-level-1">
            <div className="mb-6 space-y-2">
              {title && (
                <h1 className="text-headline-md text-text-primary">
                  {title}
                </h1>
              )}
              {subtitle && (
                <p className="text-body-sm text-text-secondary">
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

      <footer className="mx-auto w-full max-w-5xl border-t border-border py-3 text-center text-label-sm text-text-muted">
        &copy; {new Date().getFullYear()} Faultline Inc.
      </footer>
    </div>
  );
}

