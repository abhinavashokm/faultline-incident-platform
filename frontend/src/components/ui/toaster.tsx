"use client";

import { useToast } from "@/components/ui/use-toast";
import { cn } from "@/lib/utils";
import { X, CheckCircle2, AlertCircle } from "lucide-react";

export function Toaster() {
  const { toasts, dismiss } = useToast();

  if (!toasts.length) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex max-w-md flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "pointer-events-auto flex items-start gap-3 rounded-lg border p-4 shadow-level-3 transition-all",
            t.variant === "destructive"
              ? "border-error/30 bg-error-container text-error"
              : t.variant === "success"
              ? "border-success/30 bg-success-container text-success-foreground"
              : "border-border bg-card text-text-primary"
          )}
        >
          {t.variant === "destructive" && (
            <AlertCircle className="h-5 w-5 shrink-0 text-error" />
          )}
          {t.variant === "success" && (
            <CheckCircle2 className="h-5 w-5 shrink-0 text-success" />
          )}
          <div className="flex-1">
            {t.title && <div className="font-semibold text-body-sm">{t.title}</div>}
            {t.description && (
              <div className="text-body-sm opacity-90 mt-0.5">{t.description}</div>
            )}
          </div>
          <button
            onClick={() => dismiss(t.id)}
            className="p-1 rounded hover:opacity-75 transition-opacity"
            aria-label="Dismiss toast"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}

