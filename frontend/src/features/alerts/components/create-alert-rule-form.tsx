"use client";

import React, { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Bell,
  Check,
  Info,
  Loader2,
  AlertCircle,
  Radio,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { NotificationChannelSelect } from "./notification-channel-select";
import {
  NotificationChannel,
  CreateAlertRuleFormData,
  CreateAlertRulePayload,
  createAlertRuleSchema,
} from "../types";
import { createAlertRule } from "../api/alertRulesApi";

interface CreateAlertRuleFormProps {
  channels: NotificationChannel[];
}

export function CreateAlertRuleForm({ channels }: CreateAlertRuleFormProps) {
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<CreateAlertRuleFormData>({
    resolver: zodResolver(createAlertRuleSchema),
    defaultValues: {
      name: "",
      rule_type: "new_issue",
      channel_ids: [],
      environment: "",
      severity: "warning",
    },
    mode: "onChange",
  });

  const {
    register,
    handleSubmit,
    control,
    watch,
    reset,
    formState: { errors, isValid },
  } = form;

  const watchedName = watch("name");
  const watchedChannelIds = watch("channel_ids");

  // Submit button is disabled until Name is filled and at least one channel is selected
  const isSubmitDisabled =
    isSubmitting ||
    !watchedName ||
    watchedName.trim().length === 0 ||
    !watchedChannelIds ||
    watchedChannelIds.length === 0;

  const onSubmit = async (data: CreateAlertRuleFormData) => {
    setIsSubmitting(true);
    setSubmitError(null);

    // Build payload matching future API contract
    const payload: CreateAlertRulePayload = {
      name: data.name.trim(),
      rule_type: "new_issue",
      conditions: {},
      environment:
        data.environment && data.environment.trim().length > 0
          ? data.environment.trim().toLowerCase()
          : null,
      severity: data.severity,
      channel_ids: data.channel_ids,
    };

    console.log("Submitting alert rule payload:", payload);

    try {
      const response = await createAlertRule(payload);
      console.log("Alert rule created successfully:", response);

      toast({
        title: "Alert rule created",
        description: `Rule "${payload.name}" has been configured successfully.`,
        variant: "success",
      });

      // Reset form on success without redirecting
      reset({
        name: "",
        rule_type: "new_issue",
        channel_ids: [],
        environment: "",
        severity: "warning",
      });
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to create alert rule";
      setSubmitError(errorMessage);
      toast({
        title: "Submission failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
      {submitError && (
        <div className="flex items-center gap-3 rounded-lg border border-error/30 bg-error-container p-4 text-error">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <div className="flex-1 text-body-sm font-medium">{submitError}</div>
        </div>
      )}

      {/* Section 1: Rule Type (Selectable) */}
      <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b pb-4">
          <div>
            <h2 className="text-headline-sm font-semibold text-text-primary">
              Rule Type
            </h2>
            <p className="text-body-sm text-text-secondary mt-0.5">
              Select the telemetry trigger event that will activate this alert rule.
            </p>
          </div>
          <Badge variant="info" showDot={true}>
            Trigger
          </Badge>
        </div>

        <div className="space-y-3">
          <Label htmlFor="rule-type" className="text-label-md font-medium text-text-primary">
            Trigger Event <span className="text-error">*</span>
          </Label>
          <Controller
            name="rule_type"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value}
                onValueChange={field.onChange}
                disabled={isSubmitting}
              >
                <SelectTrigger id="rule-type" className="w-full h-11 bg-surface-container-lowest">
                  <SelectValue placeholder="Select rule type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="new_issue">
                    <div className="flex items-center gap-2 py-0.5">
                      <Sparkles className="h-4 w-4 text-primary shrink-0" />
                      <div className="flex flex-col text-left">
                        <span className="font-medium text-on-surface">New issue detected</span>
                      </div>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            )}
          />

          <div className="flex items-start gap-3 rounded-lg bg-surface-container-low p-3.5 border border-outline-variant/30 mt-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary mt-0.5">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="flex-1 text-body-sm text-text-secondary">
              <span className="font-semibold text-on-surface">New issue detected</span> (
              <code className="text-code-sm font-mono text-[11px] bg-surface-container px-1 py-0.5 rounded">
                new_issue
              </code>
              ): Triggers immediately when a brand new, previously unseen error fingerprint or issue group occurs in this project.
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: General Configuration */}
      <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-6">
        <div>
          <h2 className="text-headline-sm font-semibold text-text-primary">
            Rule Configuration
          </h2>
          <p className="text-body-sm text-text-secondary mt-0.5">
            Define notification targets, severity, and delivery criteria.
          </p>
        </div>

        <div className="space-y-5">
          {/* 1. Name */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="name" className="text-label-md font-medium text-text-primary">
                Rule Name <span className="text-error">*</span>
              </Label>
              <span className="text-[11px] text-text-muted font-mono">
                {watchedName?.length || 0}/150
              </span>
            </div>
            <Input
              id="name"
              placeholder="e.g. Critical Production Issue Alert"
              maxLength={150}
              {...register("name")}
              className={errors.name ? "border-error focus-visible:ring-error" : ""}
            />
            {errors.name ? (
              <p className="text-body-sm text-error mt-1">{errors.name.message}</p>
            ) : (
              <p className="text-body-sm text-text-muted">
                A concise and recognizable name describing what triggers this rule.
              </p>
            )}
          </div>

          {/* 2. Notification Channels */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-label-md font-medium text-text-primary">
                Notification Channels <span className="text-error">*</span>
              </Label>
              <span className="text-[11px] text-text-muted">
                At least 1 required
              </span>
            </div>
            <Controller
              name="channel_ids"
              control={control}
              render={({ field }) => (
                <NotificationChannelSelect
                  channels={channels}
                  value={field.value}
                  onChange={field.onChange}
                  disabled={isSubmitting}
                  hasError={!!errors.channel_ids}
                />
              )}
            />
            {errors.channel_ids ? (
              <p className="text-body-sm text-error mt-1">
                {errors.channel_ids.message}
              </p>
            ) : (
              <p className="text-body-sm text-text-muted">
                Select one or more configured channels where incident notifications will be delivered.
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
            {/* 3. Environment */}
            <div className="space-y-2">
              <Label htmlFor="environment" className="text-label-md font-medium text-text-primary">
                Environment <span className="text-text-muted font-normal text-body-sm">(Optional)</span>
              </Label>
              <Input
                id="environment"
                placeholder="e.g. production"
                {...register("environment")}
                className={errors.environment ? "border-error focus-visible:ring-error" : ""}
              />
              {errors.environment ? (
                <p className="text-body-sm text-error mt-1">
                  {errors.environment.message}
                </p>
              ) : (
                <p className="text-body-sm text-text-muted">
                  Leave blank to apply across all environments. Lowercase only (e.g. <code>production</code>, <code>staging</code>).
                </p>
              )}
            </div>

            {/* 4. Severity */}
            <div className="space-y-2">
              <Label htmlFor="severity" className="text-label-md font-medium text-text-primary">
                Severity <span className="text-text-muted font-normal text-body-sm">(Optional)</span>
              </Label>
              <Controller
                name="severity"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                    disabled={isSubmitting}
                  >
                    <SelectTrigger id="severity" className="w-full">
                      <SelectValue placeholder="Select severity" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="info">
                        <div className="flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full bg-info shrink-0" />
                          <span>Info</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="warning">
                        <div className="flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full bg-warning shrink-0" />
                          <span>Warning</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="critical">
                        <div className="flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full bg-error shrink-0" />
                          <span>Critical</span>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.severity ? (
                <p className="text-body-sm text-error mt-1">{errors.severity.message}</p>
              ) : (
                <p className="text-body-sm text-text-muted">
                  Default: <code>warning</code>. Used to classify alerting urgency.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <Button
          type="button"
          variant="outline"
          disabled={isSubmitting}
          onClick={() =>
            reset({
              name: "",
              channel_ids: [],
              environment: "",
              severity: "warning",
            })
          }
        >
          Reset
        </Button>
        <Button
          type="submit"
          disabled={isSubmitDisabled}
          className="gap-2 min-w-[140px]"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Saving...</span>
            </>
          ) : (
            <>
              <Check className="h-4 w-4" />
              <span>Save Alert Rule</span>
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
