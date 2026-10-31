import React from "react";
import { cn } from "@/lib/utils";

interface LogoMarkProps extends React.SVGProps<SVGSVGElement> {
  className?: string;
  size?: number;
}

export function LogoMark({ className, size = 28, ...props }: LogoMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("text-primary shrink-0", className)}
      {...props}
    >
      <rect width="32" height="32" rx="7" fill="currentColor" fillOpacity="0.12" />
      <path
        d="M6 16.5H11L14 9L18 23L21 16.5H26"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="18" cy="23" r="1.5" fill="currentColor" />
    </svg>
  );
}

interface LogoProps {
  className?: string;
  markClassName?: string;
  wordmarkClassName?: string;
  size?: number;
  showWordmark?: boolean;
}

export function Logo({
  className,
  markClassName,
  wordmarkClassName,
  size = 28,
  showWordmark = true,
}: LogoProps) {
  return (
    <div className={cn("inline-flex items-center gap-2.5 select-none", className)}>
      <LogoMark size={size} className={markClassName} />
      {showWordmark && (
        <span
          className={cn(
            "font-sans font-semibold tracking-tight text-text-primary text-[17px] leading-none",
            wordmarkClassName
          )}
        >
          Faultline
        </span>
      )}
    </div>
  );
}

