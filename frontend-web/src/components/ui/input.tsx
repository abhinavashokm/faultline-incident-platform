import * as React from "react";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-md border border-border bg-card px-3 py-1.5 text-body-md text-text-primary shadow-level-1 transition-colors file:border-0 file:bg-transparent file:text-body-sm file:font-medium placeholder:text-text-muted focus-visible:outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary-subdued disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };

