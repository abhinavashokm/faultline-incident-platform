"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Terminal, ArrowRight, Loader2, Info } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AuthErrorAlert } from "@/features/auth/components/auth-error-alert";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  createProjectSchema,
  CreateProjectFormData,
} from "@/features/projects/schemas";
import { useCreateProject, useListProjects } from "@/features/projects/hooks";
import { PLATFORM_REGISTRY } from "@/features/projects/platform-registry";

interface ProjectCreateFormProps {
  workspaceSlug: string;
}

export function ProjectCreateForm({ workspaceSlug }: ProjectCreateFormProps) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);

  const { data: projects, isLoading: isProjectsLoading } = useListProjects();
  const isFirstProject = !isProjectsLoading && Array.isArray(projects) && projects.length === 0;

  const activePlatform = PLATFORM_REGISTRY.fastapi;

  const form = useForm<CreateProjectFormData>({
    resolver: zodResolver(createProjectSchema),
    defaultValues: {
      name: "",
      slug: "",
      description: "",
      environment: "production",
      platform: activePlatform.value,
    },
    mode: "onChange",
  });

  const { mutate: createProject, isPending } = useCreateProject();

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    form.setValue("name", val);
    const slug = val
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
    form.setValue("slug", slug, { shouldValidate: true });
  };

  function onSubmit(values: CreateProjectFormData) {
    setFormError(null);

    createProject(values, {
      onSuccess: (newProject) => {
        router.push(`/${workspaceSlug}/projects/${newProject.slug}/setup`);
      },
      onError: (err: any) => {
        const errorMsg =
          err.message || "Failed to create project. Please try again.";

        if (err.status === 409 || /slug.*already exists/i.test(errorMsg)) {
          form.setError("slug", {
            type: "manual",
            message: "A project with this slug already exists in this workspace",
          });
          setFormError(
            "A project with this slug already exists in this workspace. Please choose a different slug."
          );
        } else {
          setFormError(errorMsg);
        }
      },
    });
  }

  return (
    <div className="bg-card rounded-lg border border-border p-6 sm:p-8 shadow-level-1">
      <div className="mb-6">
        <h1 className="text-headline-md font-semibold text-text-primary">
          {isFirstProject ? "Create your first project" : "Create your project"}
        </h1>
        <p className="text-body-sm text-text-secondary mt-1">
          Give your service a name and description. You can set up the SDK in the next step.
        </p>
      </div>

      <AuthErrorAlert error={formError} className="mb-6" />

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Project Name */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Project Name *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Payments API"
                      disabled={isPending}
                      {...field}
                      onChange={(e) => {
                        field.onChange(e);
                        handleNameChange(e);
                      }}
                    />
                  </FormControl>
                  <p className="text-[11px] text-text-muted">
                    Human-readable identifier for this service in issues &amp; incidents.
                  </p>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Slug */}
            <FormField
              control={form.control}
              name="slug"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center justify-between">
                    <FormLabel>Slug *</FormLabel>
                    <span className="font-mono text-[11px] text-text-muted">URL-safe</span>
                  </div>
                  <FormControl>
                    <Input
                      placeholder="payments-api"
                      disabled={isPending}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Description (Optional) */}
          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-center justify-between">
                  <FormLabel>Description</FormLabel>
                  <span className="text-[11px] text-text-muted">Optional</span>
                </div>
                <FormControl>
                  <Input
                    placeholder="e.g. Core service handling payment workflows and webhooks"
                    disabled={isPending}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Supported Platform */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <FormLabel>Runtime Platform</FormLabel>
              <span className="text-label-sm text-text-muted">
                Python SDK
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-4 rounded-lg border border-primary bg-primary-tint/60 shadow-level-1 ring-2 ring-primary-subdued relative flex flex-col justify-between h-28 select-none">
                <div className="flex items-start justify-between w-full">
                  <div className="p-1.5 rounded-md bg-card border border-border shadow-level-1">
                    <Terminal className="h-5 w-5 text-primary" />
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-card border border-border text-primary font-semibold">
                    {activePlatform.badge || "Supported"}
                  </span>
                </div>

                <div>
                  <div className="text-body-sm font-semibold text-text-primary">
                    {activePlatform.label}
                  </div>
                  <div className="text-[11px] text-text-secondary truncate mt-0.5">
                    {activePlatform.subtitle}
                  </div>
                </div>
              </div>
            </div>

            <p className="text-label-sm text-text-muted flex items-center gap-1.5 pt-1">
              <Info className="h-3.5 w-3.5" />
              <span>More frameworks and SDKs coming soon.</span>
            </p>
          </div>

          {/* Submit CTA */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <Button
              type="submit"
              className="gap-2 h-10 px-6"
              disabled={isPending}
            >
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Provisioning project...</span>
                </>
              ) : (
                <>
                  <span>Create project</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
