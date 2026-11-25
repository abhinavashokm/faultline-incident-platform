import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";

const columns = ["Incident", "Severity", "Status", "Assignee", "Started"];

export default function IncidentsPage({
  params,
}: {
  params: { workspaceSlug: string; projectSlug: string };
}) {
  const createHref = `/${params.workspaceSlug}/${params.projectSlug}/incidents/new`;
  return (
    <div className="flex-1 space-y-6 p-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Incidents
        </h1>
        <Button className="gap-2" asChild>
          <Link href={createHref}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Create incident
          </Link>
        </Button>
      </header>

      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <caption className="sr-only">Project incidents</caption>
          <thead className="border-b bg-muted/40 text-muted-foreground">
            <tr>
              {columns.map((column) => (
                <th key={column} scope="col" className="px-4 py-3 font-medium">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={columns.length} className="px-4 py-16 text-center text-muted-foreground">
                No incidents yet.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
