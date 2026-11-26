"use client";

import { skipToken, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { ClipboardList, Pencil, Plus, Search, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { incidentsQueryKey, listIncidents } from "@/features/incidents/api";
import { useProjectBySlug } from "@/features/projects/hooks";

const startedDate = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

export default function IncidentsPage({
  params,
}: {
  params: { workspaceSlug: string; projectSlug: string };
}) {
  const incidentsHref = `/${params.workspaceSlug}/${params.projectSlug}/incidents`;
  const projectQuery = useProjectBySlug(params.projectSlug);
  const projectId = projectQuery.project?.id;
  const incidents = useQuery({
    queryKey: incidentsQueryKey(projectId),
    queryFn: projectId ? () => listIncidents(projectId) : skipToken,
  });

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const items = incidents.data ?? [];
  const statuses = [...new Set(items.map((incident) => incident.status))].sort();
  const severities = [...new Set(["critical", "high", "medium", "low", ...items.map((incident) => incident.severity)])];
  const searchTerm = search.trim().toLowerCase();
  const filtered = items.filter((incident) =>
    (!status || incident.status === status) &&
    (!severity || incident.severity === severity) &&
    incident.title.toLowerCase().includes(searchTerm),
  );

  const loading = projectQuery.isLoading || incidents.isLoading;
  const error = projectQuery.isError
    ? "Couldn’t load the project."
    : !projectId
      ? "Project not found."
      : incidents.isError
        ? incidents.error.message
        : null;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-headline-md font-semibold tracking-tight text-text-primary">Incidents</h1>
          <p className="mt-0.5 text-body-sm text-text-secondary">Track and review incidents for this project.</p>
        </div>
        <Button size="sm" className="gap-2" asChild>
          <Link href={`${incidentsHref}/new`}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Create incident
          </Link>
        </Button>
      </header>

      <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-2.5 shadow-level-1">
        <Select value={status ? `status:${status}` : "all"} onValueChange={(value) => setStatus(value === "all" ? "" : value.slice(7))}>
          <SelectTrigger aria-label="Incident status" className="h-8 w-36 bg-canvas text-label-md">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {statuses.map((value) => (
              <SelectItem key={value} value={`status:${value}`} className="capitalize">
                {value.replaceAll("_", " ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={severity ? `severity:${severity}` : "all"} onValueChange={(value) => setSeverity(value === "all" ? "" : value.slice(9))}>
          <SelectTrigger aria-label="Incident severity" className="h-8 w-36 bg-canvas text-label-md">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All severities</SelectItem>
            {severities.map((value) => (
              <SelectItem key={value} value={`severity:${value}`} className="capitalize">{value}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="relative w-full sm:ml-auto sm:w-64">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-muted" aria-hidden="true" />
          <Input
            type="search"
            aria-label="Search incidents by title"
            placeholder="Search incidents…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="h-8 bg-canvas pl-8 text-body-sm"
          />
        </div>
      </div>

      <section aria-label="Project incidents" className="overflow-hidden rounded-lg border bg-card shadow-level-1">
        {loading ? (
          <p role="status" className="px-5 py-14 text-center text-sm text-muted-foreground">Loading incidents…</p>
        ) : error ? (
          <div className="space-y-3 px-5 py-14 text-center">
            <p role="alert" className="text-sm text-muted-foreground">{error}</p>
            {incidents.isError && (
              <Button variant="outline" size="sm" onClick={() => void incidents.refetch()}>
                Try again
              </Button>
            )}
          </div>
        ) : !filtered.length ? (
          <div className="flex flex-col items-center gap-3 px-5 py-14 text-center">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-primary-tint text-primary">
              <ClipboardList className="h-5 w-5" aria-hidden="true" />
            </span>
            <p className="text-headline-sm">{items.length ? "No matching incidents" : "No incidents yet"}</p>
            {(searchTerm || status || severity) && (
              <Button variant="secondary" size="sm" onClick={() => {
                setSearch("");
                setStatus("");
                setSeverity("");
              }}>
                Clear filters
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[36rem] text-left text-body-sm">
              <caption className="sr-only">Project incidents</caption>
              <thead className="border-b bg-canvas text-label-sm uppercase text-text-secondary">
                <tr>
                  {["Incident", "Severity", "Status", "Started"].map((column) => (
                    <th key={column} scope="col" className="px-3.5 py-2.5 font-medium">{column}</th>
                  ))}
                  <th scope="col" className="px-3.5 py-2.5 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((incident) => (
                  <tr key={incident.id} className="group relative cursor-pointer hover:bg-canvas focus-within:bg-canvas">
                    <th scope="row" className="min-w-48 px-3.5 py-3 font-medium">
                      <Link
                        href={`${incidentsHref}/${incident.id}`}
                        className="break-words group-hover:text-primary focus-visible:text-primary focus-visible:outline-none after:absolute after:inset-0 focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-ring"
                      >
                        {incident.title}
                      </Link>
                    </th>
                    <td className="px-3.5 py-3">
                      <Badge variant={incident.severity === "critical" ? "error" : incident.severity === "high" ? "warning" : "neutral"}>
                        {incident.severity}
                      </Badge>
                    </td>
                    <td className="px-3.5 py-3">
                      <Badge variant={incident.status === "resolved" ? "success" : "info"}>
                        {incident.status.replaceAll("_", " ")}
                      </Badge>
                    </td>
                    <td className="whitespace-nowrap px-3.5 py-3 text-text-secondary">
                      <time dateTime={incident.startedAt}>{startedDate.format(new Date(incident.startedAt))}</time>
                    </td>
                    <td className="px-3.5 py-3">
                      <div className="relative z-10 ml-auto flex w-fit items-center gap-1">
                        <span title="Incident editing is unavailable">
                          <Button type="button" size="icon" variant="ghost" className="text-text-secondary" disabled aria-label={`Edit ${incident.title}`}>
                            <Pencil className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        </span>
                        <span title="Incident deletion is unavailable">
                          <Button type="button" size="icon" variant="ghost" className="text-text-secondary" disabled aria-label={`Delete ${incident.title}`}>
                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
