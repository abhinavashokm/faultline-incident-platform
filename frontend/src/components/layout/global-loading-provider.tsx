"use client";

import React from "react";
import { useAuth } from "@/features/auth/auth-context";
import { GlobalLoadingScreen } from "@/components/layout/global-loading-screen";

export function GlobalLoadingProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isReady } = useAuth();

  if (!isReady) {
    return <GlobalLoadingScreen />;
  }

  return <>{children}</>;
}
