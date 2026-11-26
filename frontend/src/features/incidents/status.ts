import type { BadgeProps } from "@/components/ui/badge";

export type IncidentStatus = "open" | "investigating" | "mitigated" | "resolved";

export type StatusTransition = {
  target: IncidentStatus;
  label: string;
  title: string;
};

const transitions: Record<IncidentStatus, StatusTransition> = {
  open: { target: "investigating", label: "Start investigating", title: "Start investigating?" },
  investigating: { target: "mitigated", label: "Mark mitigated", title: "Mark as mitigated?" },
  mitigated: { target: "resolved", label: "Mark resolved", title: "Mark as resolved?" },
  resolved: { target: "open", label: "Reopen", title: "Reopen incident?" },
};

const statusStyles: Record<IncidentStatus, BadgeProps["variant"]> = {
  open: "warning",
  investigating: "info",
  mitigated: "ai",
  resolved: "success",
};

export function getStatusPresentation(status: string): {
  variant: BadgeProps["variant"];
  transition?: StatusTransition;
} {
  if (!Object.prototype.hasOwnProperty.call(transitions, status)) return { variant: "neutral" };
  const knownStatus = status as IncidentStatus;
  return { variant: statusStyles[knownStatus], transition: transitions[knownStatus] };
}
