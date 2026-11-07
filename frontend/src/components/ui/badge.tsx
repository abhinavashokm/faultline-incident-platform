import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 font-mono text-label-sm font-medium uppercase tracking-wider select-none",
  {
    variants: {
      variant: {
        default:
          "bg-canvas border border-border text-text-secondary",
        error:
          "bg-error-container text-error border border-error/20",
        warning:
          "bg-warning-container text-warning-foreground border border-warning/20",
        success:
          "bg-success-container text-success-foreground border border-success/20",
        info:
          "bg-info-container text-info border border-info/20",
        ai:
          "bg-ai-container text-ai-foreground border border-ai/20",
        neutral:
          "bg-muted text-text-secondary border border-border",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

const dotColors: Record<string, string> = {
  default: "bg-text-muted",
  error: "bg-error",
  warning: "bg-warning",
  success: "bg-success",
  info: "bg-info",
  ai: "bg-ai",
  neutral: "bg-text-secondary",
};

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  showDot?: boolean;
}

function Badge({ className, variant = "default", showDot = true, children, ...props }: BadgeProps) {
  const currentVariant = variant || "default";
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props}>
      {showDot && (
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full shrink-0",
            dotColors[currentVariant] || "bg-current"
          )}
        />
      )}
      <span>{children}</span>
    </div>
  );
}

export { Badge, badgeVariants };

