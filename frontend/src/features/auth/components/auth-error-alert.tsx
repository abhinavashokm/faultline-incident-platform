import * as React from "react";
import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export interface AuthErrorAlertProps extends React.HTMLAttributes<HTMLDivElement> {
  error?: string | null;
}

export function AuthErrorAlert({
  error,
  className,
  children,
  ...props
}: AuthErrorAlertProps) {
  const content = error || children;

  if (!content) {
    return null;
  }

  return (
    <div
      role="alert"
      className={cn(
        "mb-4 flex items-center gap-2 rounded-md border border-red-200/50 bg-red-50/50 p-2.5 text-xs text-red-500 font-normal dark:border-red-900/30 dark:bg-red-950/20 dark:text-red-400",
        className
      )}
      {...props}
    >
      <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
      <span>{content}</span>
    </div>
  );
}
