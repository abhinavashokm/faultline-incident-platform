import { Loader2 } from "lucide-react";

export default function DashboardLoading() {
  return (
    <div
      role="status"
      className="flex min-h-[40vh] items-center justify-center gap-2 text-body-sm text-text-secondary"
    >
      <Loader2 aria-hidden="true" className="h-5 w-5 motion-safe:animate-spin" />
      <span>Loading page…</span>
    </div>
  );
}
