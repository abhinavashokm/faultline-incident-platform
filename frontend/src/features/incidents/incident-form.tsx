"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Bug, ClipboardList } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { IssuePicker, type SelectedIssue } from "@/features/incidents/issue-picker";

const severities: { value: string; label: string; description: string }[] = [
  { value: "critical", label: "P0 · Critical", description: "Widespread outage or data loss" },
  { value: "high", label: "P1 · High", description: "Core functionality severely degraded" },
  { value: "medium", label: "P2 · Medium", description: "Limited impact or localized errors" },
  { value: "low", label: "P3 · Low", description: "Minor impact or background failure" },
];

export type IncidentFormValues = {
  title: string;
  severity: string;
  description: string;
  relatedIssueIds: string[];
};

type IncidentFormProps = {
  projectId: string;
  initialValues?: {
    title: string;
    severity: string;
    description: string | null;
    relatedIssues: SelectedIssue[];
  };
  cancelHref: string;
  submitLabel: string;
  disabled: boolean;
  error?: string;
  onSubmit: (values: IncidentFormValues) => void;
};

export function IncidentForm({
  projectId, initialValues, cancelHref, submitLabel, disabled, error, onSubmit,
}: IncidentFormProps) {
  const [title, setTitle] = useState(initialValues?.title ?? "");
  const [severity, setSeverity] = useState(initialValues?.severity ?? "medium");
  const [description, setDescription] = useState(initialValues?.description ?? "");
  const [selectedIssues, setSelectedIssues] = useState(initialValues?.relatedIssues ?? []);
  const originalSeverity = initialValues?.severity;
  const severityOptions = originalSeverity && !severities.some(({ value }) => value === originalSeverity)
    ? [...severities, { value: originalSeverity, label: originalSeverity, description: "" }]
    : severities;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || disabled) return;
    onSubmit({
      title: title.trim(),
      severity,
      description,
      relatedIssueIds: selectedIssues.map((issue) => issue.id),
    });
  }

  return (
    <form onSubmit={handleSubmit}>
      <fieldset disabled={disabled} className="min-w-0 space-y-6">
        <section aria-labelledby="incident-overview" className="overflow-hidden rounded-xl border bg-card shadow-level-1">
          <header className="flex items-center gap-3 border-b bg-canvas px-4 py-4 sm:px-6">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary-tint text-primary">
              <ClipboardList className="h-5 w-5" aria-hidden="true" />
            </span>
            <h2 id="incident-overview" className="text-headline-sm">Incident overview</h2>
          </header>
          <div className="space-y-5 p-4 sm:p-6">
            <div className="space-y-2">
              <Label htmlFor="incident-title">Incident title <span className="text-error" aria-hidden="true">*</span></Label>
              <Input
                id="incident-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="e.g. Payment processing failures after deployment"
                maxLength={255}
                required
                className="bg-canvas"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="incident-description">Description <span className="text-muted-foreground">(optional)</span></Label>
              <textarea
                id="incident-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Describe the symptoms, impact, or recent changes."
                rows={4}
                className="block w-full rounded-control border border-border bg-canvas px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>
            <fieldset className="min-w-0">
              <legend className="mb-2 text-sm font-medium">Severity</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {severityOptions.map(({ value, label, description }) => (
                  <label key={value} className="relative flex cursor-pointer">
                    <input
                      type="radio"
                      name="severity"
                      value={value}
                      checked={severity === value}
                      onChange={() => setSeverity(value)}
                      className="peer absolute left-3 top-3.5 h-4 w-4 accent-primary"
                    />
                    <span className="w-full rounded-lg border bg-canvas py-3 pl-9 pr-3 text-sm font-medium hover:border-border-hover peer-checked:border-primary peer-checked:bg-primary-tint peer-focus-visible:ring-2 peer-focus-visible:ring-ring">
                      <span className="block">{label}</span>
                      {description && <span className="mt-1 block text-xs font-normal text-muted-foreground">{description}</span>}
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
        </section>
        <section aria-labelledby="incident-issues" className="overflow-hidden rounded-xl border bg-card shadow-level-1">
          <header className="flex items-start gap-3 border-b bg-canvas px-4 py-4 sm:px-6">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-ai-container text-ai-foreground">
              <Bug className="h-5 w-5" aria-hidden="true" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-2">
                <h2 id="incident-issues" className="text-headline-sm">Link telemetry issues</h2>
                <span className="text-xs text-muted-foreground">Optional</span>
              </div>
              <p className="text-sm text-muted-foreground">Select related issues from this project.</p>
            </div>
            <span aria-live="polite" className="shrink-0 pt-1 text-xs font-medium text-muted-foreground">
              {selectedIssues.length} selected
            </span>
          </header>
          <div className="p-4 sm:p-6">
            <IssuePicker
              projectId={projectId}
              selected={selectedIssues}
              onChange={setSelectedIssues}
            />
          </div>
        </section>
        <footer className="flex flex-wrap items-center justify-end gap-3 rounded-xl border bg-card p-4 shadow-level-1">
          {error && <p role="alert" className="mr-auto text-sm text-error">{error}</p>}
          <Button variant="outline" asChild><Link href={cancelHref}>Cancel</Link></Button>
          <Button type="submit" disabled={!title.trim()}>{submitLabel}</Button>
        </footer>
      </fieldset>
    </form>
  );
}
