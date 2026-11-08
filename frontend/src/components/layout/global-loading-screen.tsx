"use client";

import React from "react";
import { LogoMark } from "@/components/brand/logo";

export function GlobalLoadingScreen() {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-canvas">
      <div className="relative flex flex-col items-center">
        {/* Pulsing glow behind the logo */}
        <div className="absolute -inset-4 rounded-full bg-primary/10 blur-xl animate-pulse" />
        
        {/* Logo with smooth pulse animation */}
        <div className="relative flex items-center justify-center">
          <LogoMark size={48} className="animate-pulse" />
        </div>

        {/* Brand name and loading indicator */}
        <div className="mt-5 flex flex-col items-center gap-2">
          <span className="font-sans font-semibold tracking-tight text-text-primary text-body-lg">
            Faultline
          </span>
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" />
          </div>
        </div>
      </div>
    </div>
  );
}
