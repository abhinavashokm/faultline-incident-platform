"use client";

import React from "react";
import { Globe, Server } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface EventRequestServiceProps {
  httpMethod?: string | null;
  routeTemplate?: string | null;
  statusCode?: number | null;
  service?: string | null;
}

export function EventRequestService({
  httpMethod,
  routeTemplate,
  statusCode,
  service,
}: EventRequestServiceProps) {
  const hasRequestData = Boolean(httpMethod || routeTemplate || statusCode !== null && statusCode !== undefined);
  const hasServiceData = Boolean(service);

  if (!hasRequestData && !hasServiceData) {
    return null;
  }

  const getStatusBadgeVariant = (code: number) => {
    if (code >= 500) return "error";
    if (code >= 400) return "warning";
    if (code >= 200 && code < 300) return "success";
    return "neutral";
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4 shadow-level-1 space-y-3">
      <div className="flex items-center gap-2 text-title-sm font-semibold text-text-primary">
        <Globe className="h-4 w-4 text-primary" />
        <span>Request & Service</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-body-sm font-mono">
        {hasRequestData && (
          <div className="space-y-1">
            <span className="text-[11px] text-text-muted uppercase tracking-wider block">
              HTTP Endpoint
            </span>
            <div className="flex items-center gap-2 flex-wrap">
              {httpMethod && (
                <span className="font-semibold text-primary px-1.5 py-0.5 rounded bg-primary/10 border border-primary/20 text-label-sm">
                  {httpMethod.toUpperCase()}
                </span>
              )}
              {routeTemplate && (
                <span className="text-text-primary break-all">
                  {routeTemplate}
                </span>
              )}
              {statusCode !== null && statusCode !== undefined && (
                <Badge
                  variant={getStatusBadgeVariant(statusCode)}
                  showDot
                  className="text-label-sm px-1.5 py-0.5"
                >
                  {statusCode}
                </Badge>
              )}
            </div>
          </div>
        )}

        {hasServiceData && (
          <div className="space-y-1">
            <span className="text-[11px] text-text-muted uppercase tracking-wider flex items-center gap-1">
              <Server className="h-3 w-3" />
              Service
            </span>
            <div className="text-text-primary font-medium">
              {service}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
