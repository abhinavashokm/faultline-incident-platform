"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Pencil } from "lucide-react";
import { useForm } from "react-hook-form";
import * as Dialog from "@radix-ui/react-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { toast } from "@/components/ui/use-toast";
import { AuthErrorAlert } from "@/features/auth/components/auth-error-alert";
import { useUpdateProject } from "../hooks";
import { editProjectSchema, type EditProjectFormData } from "../schemas";
import type { Project, ProjectUpdate } from "../types";

export function ProjectEditDialog({ project }: { project: Project }) {
  const [open, setOpen] = useState(false);
  const update = useUpdateProject(project.id);
  const defaults = { name: project.name, description: project.description ?? "" };
  const form = useForm<EditProjectFormData>({
    resolver: zodResolver(editProjectSchema),
    defaultValues: defaults,
  });

  const { dirtyFields, isDirty } = form.formState;

  function handleOpenChange(nextOpen: boolean) {
    if (update.isPending) return;
    if (nextOpen) {
      form.reset(defaults);
      update.reset();
    }
    setOpen(nextOpen);
  }

  function handleSubmit(values: EditProjectFormData) {
    if (update.isPending) return;

    const changes: ProjectUpdate = {};
    if (dirtyFields.name) {
      changes.name = values.name;
    }
    if (dirtyFields.description) {
      changes.description = values.description.trim() || null;
    }
    if (Object.keys(changes).length === 0) return;

    update.mutate(changes, {
      onSuccess: () => {
        setOpen(false);
        toast({ title: "Project updated", variant: "success" });
      },
    });
  }

  return (
    <Dialog.Root open={open} onOpenChange={handleOpenChange}>
      <Dialog.Trigger asChild>
        <Button type="button" size="icon" variant="ghost" aria-label={`Edit ${project.name}`} title="Edit project">
          <Pencil aria-hidden="true" className="h-4 w-4" />
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border border-border bg-card shadow-level-3">
          <div className="border-b border-border px-6 py-4">
            <Dialog.Title className="text-headline-sm font-semibold">Edit project</Dialog.Title>
            <Dialog.Description className="mt-1 break-words font-mono text-label-sm text-text-muted">
              {project.slug}
            </Dialog.Description>
          </div>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4 p-6">
              <AuthErrorAlert error={update.error?.message} />
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Project name</FormLabel>
                    <FormControl>
                      <Input {...field} autoComplete="off" maxLength={150} disabled={update.isPending} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <textarea
                        {...field}
                        className="block w-full rounded-md border border-border bg-card px-3 py-2 text-body-sm text-text-primary disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                        rows={4}
                        disabled={update.isPending}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="flex justify-end gap-2 border-t border-border pt-4">
                <Dialog.Close asChild>
                  <Button type="button" variant="secondary" disabled={update.isPending}>Cancel</Button>
                </Dialog.Close>
                <Button type="submit" disabled={!isDirty || update.isPending}>
                  {update.isPending && <Loader2 aria-hidden="true" className="mr-2 h-4 w-4 animate-spin" />}
                  {update.isPending ? "Saving…" : "Save changes"}
                </Button>
              </div>
            </form>
          </Form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
