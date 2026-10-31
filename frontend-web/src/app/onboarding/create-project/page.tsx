"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Terminal,
  Code2,
  Cpu,
  Coffee,
  Boxes,
  Radio,
  ArrowRight,
  Loader2,
  CheckCircle2,
  Info,
} from "lucide-react";

import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  createProjectSchema,
  CreateProjectFormData,
} from "@/features/projects/schemas";
import { useCreateProject } from "@/features/projects/hooks";
import { PlatformId } from "@/features/projects/types";

interface PlatformOption {
  id: PlatformId;
  name: string;
  tagline: string;
  badge?: string;
  icon: React.ReactNode;
}

const PLATFORMS: PlatformOption[] = [
  {
    id: "python",
    name: "Python",
    tagline: "FastAPI, Django, Flask ASGI",
    badge: "Auto-instrument",
    icon: <Terminal className="h-5 w-5 text-primary" />,
  },
  {
    id: "javascript",
    name: "JavaScript / Web",
    tagline: "Next.js, React, Browser DOM",
    badge: "App Router",
    icon: <Code2 className="h-5 w-5 text-warning" />,
  },
  {
    id: "node",
    name: "Node.js",
    tagline: "Express, NestJS, Worker Threads",
    badge: "v18+ LTS",
    icon: <Cpu className="h-5 w-5 text-success" />,
  },
  {
    id: "java",
    name: "Java",
    tagline: "Spring Boot, Micronaut, Quarkus",
    badge: "JVM 17+",
    icon: <Coffee className="h-5 w-5 text-error" />,
  },
  {
    id: "go",
    name: "Go",
    tagline: "Standard Net/HTTP, Gin, Fiber",
    badge: "Low latency",
    icon: <Boxes className="h-5 w-5 text-info" />,
  },
  {
    id: "other",
    name: "Other / OpenTelemetry",
    tagline: "Custom telemetry & OTLP daemon",
    badge: "OTel OTLP",
    icon: <Radio className="h-5 w-5 text-ai" />,
  },
];

export default function CreateProjectPage() {
  const router = useRouter();
  const [selectedPlatform, setSelectedPlatform] = useState<PlatformId>("python");

  const form = useForm<CreateProjectFormData>({
    resolver: zodResolver(createProjectSchema),
    defaultValues: {
      name: "",
      slug: "",
      platform: "python",
      environment: "production",
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

  const handleSelectPlatform = (id: PlatformId) => {
    setSelectedPlatform(id);
    form.setValue("platform", id, { shouldValidate: true });
  };

  function onSubmit(values: CreateProjectFormData) {
    createProject(values, {
      onSuccess: (project) => {
        router.push(
          `/onboarding/install-sdk?projectId=${project.id}&platform=${project.platform}&name=${encodeURIComponent(
            project.name
          )}`
        );
      },
    });
  }

  return (
    <div className="min-h-screen bg-canvas flex flex-col justify-between">
      {/* Top Header */}
      <header className="border-b border-border bg-card px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <Logo size={26} />

          {/* Stepper */}
          <div className="hidden sm:flex items-center gap-3 text-label-sm">
            <div className="flex items-center gap-1.5 text-success">
              <CheckCircle2 className="h-4 w-4" />
              <span>Workspace configured</span>
            </div>
            <span className="text-border">•</span>
            <div className="flex items-center gap-1.5 font-medium text-text-primary">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[11px] font-mono text-primary-foreground">
                1
              </span>
              <span>Create Project</span>
            </div>
            <span className="text-border">•</span>
            <div className="flex items-center gap-1.5 text-text-muted">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-border text-[11px] font-mono text-text-secondary">
                2
              </span>
              <span>Install SDK</span>
            </div>
          </div>

          <div className="text-label-sm text-text-secondary font-mono">
            Acme Cloud
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-8 sm:py-12">
        <div className="bg-card rounded-lg border border-border p-6 sm:p-8 shadow-level-1">
          <div className="mb-6">
            <h1 className="text-headline-md font-semibold text-text-primary">
              Create your project
            </h1>
            <p className="text-body-sm text-text-secondary mt-1">
              Choose the application runtime you want to monitor. You can configure the SDK in the next step.
            </p>
          </div>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              {/* Project Name & Slug */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Project name *</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="e.g. Payments API, Auth Service"
                          value={field.value}
                          onChange={handleNameChange}
                          disabled={isPending}
                        />
                      </FormControl>
                      <p className="text-[11px] text-text-muted flex items-center gap-1">
                        <Info className="h-3 w-3" />
                        Identifies this service in issues & incidents.
                      </p>
                      <FormMessage />
                    </FormItem>
                  )}
                />

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

              {/* Platform Picker */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <FormLabel>Select Platform *</FormLabel>
                  <span className="text-label-sm text-text-muted">
                    SDK auto-tuning &amp; symbolication
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {PLATFORMS.map((p) => {
                    const isSelected = selectedPlatform === p.id;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => handleSelectPlatform(p.id)}
                        disabled={isPending}
                        className={`text-left p-3.5 rounded-lg border transition-all relative flex flex-col justify-between h-28 ${
                          isSelected
                            ? "border-primary bg-primary-tint/60 shadow-level-1 ring-2 ring-primary-subdued"
                            : "border-border bg-card hover:bg-canvas hover:border-border-hover"
                        }`}
                      >
                        <div className="flex items-start justify-between w-full">
                          <div className="p-1.5 rounded-md bg-card border border-border shadow-level-1">
                            {p.icon}
                          </div>
                          {p.badge && (
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-card border border-border text-text-secondary">
                              {p.badge}
                            </span>
                          )}
                        </div>

                        <div>
                          <div className="text-body-sm font-semibold text-text-primary">
                            {p.name}
                          </div>
                          <div className="text-[11px] text-text-secondary truncate mt-0.5">
                            {p.tagline}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Environment (Optional) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                <FormField
                  control={form.control}
                  name="environment"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Default Environment</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        defaultValue={field.value}
                        disabled={isPending}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select environment" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="production">production</SelectItem>
                          <SelectItem value="staging">staging</SelectItem>
                          <SelectItem value="development">development</SelectItem>
                          <SelectItem value="canary">canary</SelectItem>
                        </SelectContent>
                      </Select>
                      <p className="text-[11px] text-text-muted">
                        Events without an environment tag default to this value.
                      </p>
                      <FormMessage />
                    </FormItem>
                  )}
                />
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
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card py-3 px-6 text-center text-label-sm text-text-muted">
        Faultline Project Onboarding • High Precision Telemetry
      </footer>
    </div>
  );
}

