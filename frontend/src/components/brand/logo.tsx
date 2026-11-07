import React from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";

interface LogoMarkProps extends Omit<React.ComponentPropsWithoutRef<typeof Image>, "src" | "alt" | "width" | "height"> {
  className?: string;
  size?: number;
}

export function LogoMark({ className, size = 28, ...props }: LogoMarkProps) {
  return (
    <Image
      src="/logo.png"
      alt="Faultline Logo"
      width={size}
      height={size}
      className={cn("shrink-0 object-contain", className)}
      {...props}
    />
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

