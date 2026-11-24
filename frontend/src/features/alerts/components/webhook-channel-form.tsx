"use client";

import { forwardRef, useState, type ComponentProps } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, Info } from "lucide-react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CreateWebhookChannelPayload } from "../api/alertRulesApi";

const reservedHeaders = /^(?:host$|content-length$|content-type$|authorization$|connection$|transfer-encoding$|x-faultline-)/i;

const webhookSchema = z.object({
  name: z.string().trim().min(1, "Channel name is required.").max(150, "Use 150 characters or fewer."),
  url: z.string().trim().min(1, "Webhook URL is required.").url("Enter a valid URL.").pipe(
    z.string().refine((value) => {
      const url = new URL(value);
      return url.protocol === "https:" && !url.username && !url.password && !value.includes("#");
    }, "Use an HTTPS URL without embedded credentials or a fragment."),
  ),
  enabled: z.boolean(),
  auth: z.discriminatedUnion("type", [
    z.object({ type: z.literal("none") }),
    z.object({
      type: z.literal("bearer"),
      value: z.string().refine((value) => value.trim().length > 0 && /^[ -~]+$/.test(value), "Enter a token using printable ASCII characters."),
    }),
    z.object({
      type: z.literal("header"),
      name: z.string()
        .min(1, "Header name is required.")
        .regex(/^[A-Za-z0-9-]+$/, "Use only letters, digits, and hyphens.")
        .refine((value) => !reservedHeaders.test(value), "This header name is reserved."),
      value: z.string().refine((value) => value.trim().length > 0 && /^[ -~]+$/.test(value), "Enter a header value using printable ASCII characters."),
    }),
  ]),
});

type WebhookFormData = z.infer<typeof webhookSchema>;

const SecretInput = forwardRef<HTMLInputElement, ComponentProps<typeof Input>>(
  function SecretInput({ id, disabled, ...props }, ref) {
    const [visible, setVisible] = useState(false);
    return (
      <div className="relative">
        <Input
          {...props}
          ref={ref}
          id={id}
          disabled={disabled}
          type={visible ? "text" : "password"}
          autoComplete="off"
          spellCheck={false}
          className="pr-10"
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          disabled={disabled}
          aria-label={visible ? "Hide value" : "Show value"}
          aria-controls={id}
          className="absolute right-0 top-0 h-9 w-9"
          onClick={() => setVisible(!visible)}
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </Button>
      </div>
    );
  },
);

function FieldError({ id, message }: { id: string; message?: string }) {
  return message ? <p id={id} role="alert" className="text-xs text-error">{message}</p> : null;
}

type WebhookChannelFormProps = {
  formId: string;
  channelName: string;
  onChannelNameChange: (name: string) => void;
  onSave: (payload: CreateWebhookChannelPayload) => Promise<void>;
};

export function WebhookChannelForm({
  formId,
  channelName,
  onChannelNameChange,
  onSave,
}: WebhookChannelFormProps) {
  const {
    control,
    register,
    watch,
    resetField,
    setValue,
    handleSubmit,
    getFieldState,
    formState,
  } = useForm<WebhookFormData>({
    resolver: zodResolver(webhookSchema),
    mode: "onBlur",
    defaultValues: { name: channelName, url: "", auth: { type: "none" }, enabled: true },
  });
  const { errors, isSubmitting } = formState;
  const authType = watch("auth.type");
  const headerNameError = getFieldState("auth.name", formState).error;
  const authValueError = getFieldState("auth.value", formState).error;

  return (
    <form
      id={formId}
      noValidate
      onSubmit={handleSubmit(({ name, url, enabled, auth }) => onSave({
        name,
        channel_type: "webhook",
        destination: url,
        enabled,
        auth: auth.type === "none" ? null : auth,
      }))}
    >
      <fieldset disabled={isSubmitting} className="min-w-0 space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="webhook-name">Channel Name</Label>
          <Input
            id="webhook-name"
            placeholder="e.g. Platform SRE Leads"
            required
            aria-invalid={!!errors.name}
            aria-describedby={errors.name ? "webhook-name-error" : undefined}
            {...register("name", { onChange: (event) => onChannelNameChange(event.target.value) })}
          />
          <FieldError id="webhook-name-error" message={errors.name?.message} />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="webhook-url">Webhook URL</Label>
          <Input
            id="webhook-url"
            type="url"
            placeholder="https://example.com/webhook"
            required
            aria-invalid={!!errors.url}
            aria-describedby={errors.url ? "webhook-url-help webhook-url-error" : "webhook-url-help"}
            {...register("url")}
          />
          <p id="webhook-url-help" className="text-xs text-muted-foreground">
            Faultline sends a signed POST request to this URL.
          </p>
          <FieldError id="webhook-url-error" message={errors.url?.message} />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="webhook-auth">Authentication</Label>
          <Controller
            control={control}
            name="auth.type"
            render={({ field }) => (
              <Select
                value={field.value}
                disabled={isSubmitting}
                onValueChange={(type: WebhookFormData["auth"]["type"]) => {
                  if (type === field.value) return;
                  resetField("auth.name", { defaultValue: "" });
                  resetField("auth.value", { defaultValue: "" });
                  setValue("auth.type", type, { shouldDirty: true });
                }}
              >
                <SelectTrigger id="webhook-auth" ref={field.ref} onBlur={field.onBlur}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  <SelectItem value="bearer">Bearer token</SelectItem>
                  <SelectItem value="header">Custom header</SelectItem>
                </SelectContent>
              </Select>
            )}
          />
        </div>

        {authType === "header" && (
          <div className="space-y-1.5">
            <Label htmlFor="webhook-header-name">Header name</Label>
            <Input
              id="webhook-header-name"
              required
              aria-invalid={!!headerNameError}
              aria-describedby={headerNameError ? "webhook-header-name-error" : undefined}
              {...register("auth.name")}
            />
            <FieldError id="webhook-header-name-error" message={headerNameError?.message} />
          </div>
        )}
        {authType !== "none" && (
          <div key={authType} className="space-y-1.5">
            <Label htmlFor="webhook-auth-value">{authType === "bearer" ? "Token" : "Header value"}</Label>
            <SecretInput
              id="webhook-auth-value"
              required
              disabled={isSubmitting}
              aria-invalid={!!authValueError}
              aria-describedby={authValueError ? "webhook-auth-value-error" : undefined}
              {...register("auth.value")}
            />
            <FieldError id="webhook-auth-value-error" message={authValueError?.message} />
          </div>
        )}

        <Label className="flex w-fit cursor-pointer items-center gap-2.5">
          <span className="relative inline-flex">
            <input type="checkbox" role="switch" className="peer sr-only" {...register("enabled")} />
            <span aria-hidden="true" className="h-5 w-9 rounded-full bg-muted-foreground/50 transition-colors peer-checked:bg-primary peer-focus-visible:ring-2 peer-focus-visible:ring-primary peer-disabled:opacity-50" />
            <span aria-hidden="true" className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white transition-transform peer-checked:translate-x-4" />
          </span>
          Enabled
        </Label>

        <div className="p-3 rounded-lg bg-muted/50 border border-border flex items-start gap-2.5">
          <Info className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            Requests are signed with HMAC-SHA256. A signing secret is generated after you save and shown only once.
          </p>
        </div>
      </fieldset>
    </form>
  );
}
