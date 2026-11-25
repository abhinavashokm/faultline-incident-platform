"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Radio,
  Plus,
  Mail,
  MessageSquare,
  Webhook,
  X,
  ChevronRight,
  Loader2,
  AlertCircle,
  AlertTriangle,
  Pencil,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { useProjectBySlug } from "@/features/projects/hooks";
import {
  listChannels,
  testChannel,
  createChannel,
  createWebhookChannel,
  updateChannel,
  deleteChannel,
  type UpdateWebhookChannelPayload,
} from "@/features/alerts/api/alertRulesApi";
import { WebhookChannelForm } from "@/features/alerts/components/webhook-channel-form";
import { WebhookSigningSecretDialog } from "@/features/alerts/components/webhook-signing-secret-dialog";
import { ApiError } from "@/lib/api-client";

import type { NotificationChannel } from "@/features/alerts/types";

const webhookFormId = "create-webhook-channel";

export default function NotificationChannelsPage() {
  const params = useParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const workspaceSlug = (params?.workspaceSlug as string) || "";
  const projectSlug = (params?.projectSlug as string) || "";

  const { project, isLoading: isProjectLoading } = useProjectBySlug(projectSlug);
  const projectId = project?.id;

  const [editingChannel, setEditingChannel] = useState<NotificationChannel | null>(null);
  const [channelToDelete, setChannelToDelete] = useState<NotificationChannel | null>(null);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const channelDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (!isModalOpen) return;

    const dialog = channelDialogRef.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, [isModalOpen]);
  const [channelType, setChannelType] = useState<"email" | "webhook">("email");
  const [channelName, setChannelName] = useState("");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [recipients, setRecipients] = useState<string[]>([]);
  const [formValidationError, setFormValidationError] = useState<string | null>(null);
  const [isWebhookSubmitting, setIsWebhookSubmitting] = useState(false);
  const webhookInFlight = useRef(false);
  const [webhookConfirmation, setWebhookConfirmation] = useState<{
    projectId: string;
    secret: string;
  } | null>(null);

  // Fetch channels list query
  const {
    data: channels = [],
    isLoading: isChannelsLoading,
    isError: isChannelsError,
    error: channelsError,
    refetch,
  } = useQuery({
    queryKey: ["notification-channels", projectId],
    queryFn: () => listChannels(projectId!),
    enabled: Boolean(projectId),
  });

  const testChannelMutation = useMutation({
    mutationFn: ({ projectId, channelId }: { projectId: string; channelId: string }) =>
      testChannel(projectId, channelId),
    onSuccess: () => toast({ title: "Test notification sent", variant: "success" }),
    onError: (err: unknown) =>
      toast({
        title: "Test delivery failed",
        description: err instanceof Error ? err.message : "Could not send the test notification",
        variant: "destructive",
      }),
  });

  const deleteChannelMutation = useMutation({
    mutationFn: ({ projectId, channelId }: { projectId: string; channelId: string }) =>
      deleteChannel(projectId, channelId),
    onSuccess: (_, target) => {
      void queryClient.invalidateQueries({ queryKey: ["notification-channels", target.projectId] });
      void queryClient.invalidateQueries({ queryKey: ["alert-rules", target.projectId] });
      setChannelToDelete(null);
      toast({ title: "Channel deleted", variant: "success" });
    },
    onError: (err: unknown) => toast({
      title: "Channel deletion failed",
      description: err instanceof Error ? err.message : "Could not delete the channel",
      variant: "destructive",
    }),
  });

  const saveEmailChannelMutation = useMutation({
    mutationFn: (newChannel: {
      name: string;
      channel_type: "email";
      destination: string;
      enabled: boolean;
    }) => {
      if (!projectId) {
        throw new Error("Project ID is missing");
      }
      return editingChannel
        ? updateChannel(projectId, editingChannel.id, newChannel)
        : createChannel(projectId, newChannel);
    },
    onSuccess: (created) => {
      queryClient.invalidateQueries({
        queryKey: ["notification-channels", projectId],
      });
      toast({
        title: editingChannel ? "Channel updated" : "Channel created",
        description: `Notification channel "${created.name}" has been configured successfully.`,
        variant: "success",
      });
      handleCloseModal();
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 422) {
        setFormValidationError(err.message || "Invalid channel payload");
      } else {
        const message = err instanceof Error ? err.message : "Failed to save channel";
        toast({
          title: "Channel save failed",
          description: message,
          variant: "destructive",
        });
      }
    },
  });

  const handleAddRecipient = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && recipientEmail.trim()) {
      e.preventDefault();
      const email = recipientEmail.trim();
      if (!recipients.includes(email)) {
        setRecipients([...recipients, email]);
      }
      setRecipientEmail("");
    }
  };

  const handleRemoveRecipient = (emailToRemove: string) => {
    setRecipients(recipients.filter((email) => email !== emailToRemove));
  };

  const resetEmailFields = () => {
    setRecipientEmail("");
    setRecipients([]);
    setFormValidationError(null);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingChannel(null);
    setEmailEnabled(true);
    setChannelName("");
    setChannelType("email");
    resetEmailFields();
  };

  const handleEditChannel = (channel: NotificationChannel) => {
    resetEmailFields();
    const type = channel.channelType ?? channel.channel_type;
    if (type !== "email" && type !== "webhook") return;
    setEditingChannel(channel);
    setChannelType(type);
    setChannelName(channel.name);
    setEmailEnabled(channel.enabled);
    if (type === "email") setRecipientEmail(channel.destination);
    setIsModalOpen(true);
  };

  const handleSelectChannelType = (type: "email" | "webhook") => {
    if (type === channelType) return;
    resetEmailFields();
    setChannelType(type);
  };

  const handleSaveWebhook = async (payload: UpdateWebhookChannelPayload) => {
    if (!projectId || webhookInFlight.current) return;
    webhookInFlight.current = true;
    setIsWebhookSubmitting(true);
    try {
      if (editingChannel) {
        await updateChannel(projectId, editingChannel.id, payload);
        toast({ title: "Channel updated", variant: "success" });
      } else {
        const { signingSecret } = await createWebhookChannel(projectId, {
          ...payload,
          auth: payload.auth ?? null,
        });
        setWebhookConfirmation({ projectId, secret: signingSecret });
      }
      handleCloseModal();
      void queryClient.invalidateQueries({ queryKey: ["notification-channels", projectId] });
    } catch (err) {
      toast({
        title: "Channel save failed",
        description: err instanceof Error ? err.message : "Failed to save channel",
        variant: "destructive",
      });
    } finally {
      webhookInFlight.current = false;
      setIsWebhookSubmitting(false);
    }
  };

  const handleSaveChannel = async () => {
    setFormValidationError(null);
    const trimmedName = channelName.trim();
    if (!trimmedName) {
      setFormValidationError("Channel name is required.");
      return;
    }

    const allEmails = [...recipients];
    if (recipientEmail.trim() && !allEmails.includes(recipientEmail.trim())) {
      allEmails.push(recipientEmail.trim());
    }

    if (allEmails.length === 0) {
      setFormValidationError("At least one recipient email address is required.");
      return;
    }

    const destination = allEmails[0]; // primary email destination
    saveEmailChannelMutation.mutate({
      name: trimmedName,
      channel_type: "email",
      destination,
      enabled: emailEnabled,
    });
  };

  const isLoading = isProjectLoading || isChannelsLoading;
  const isSubmitting = saveEmailChannelMutation.isPending || isWebhookSubmitting;
  const activeCount = channels.filter((c) => c.enabled).length;

  return (
    <div className="mx-auto w-full max-w-7xl flex-1 space-y-6 px-4 py-6 sm:px-6">
      {/* Breadcrumb & Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Link
              href={`/${workspaceSlug}/${projectSlug}/alerts`}
              className="hover:text-foreground transition-colors"
            >
              Alerts
            </Link>
            <ChevronRight className="h-3 w-3" />
            <span className="font-medium text-foreground">Channels</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Notification Channels
          </h1>
          <p className="text-sm text-muted-foreground max-w-2xl">
            Manage where this project sends email and webhook alerts.
          </p>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <Button
            onClick={() => setIsModalOpen(true)}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            Add Channel
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-20" />
          </div>
          <div className="space-y-3">
            <Skeleton className="h-12 w-full rounded-lg" />
            <Skeleton className="h-12 w-full rounded-lg" />
          </div>
        </div>
      ) : isChannelsError && channels.length === 0 ? (
        <div className="flex min-h-[280px] flex-col items-center justify-center rounded-xl border border-dashed border-error/40 p-8 text-center bg-error-container/10">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-error/10 text-error mb-4">
            <AlertTriangle className="h-7 w-7" />
          </div>
          <h2 className="text-lg font-semibold text-foreground mb-1">
            Failed to load notification channels
          </h2>
          <p className="text-sm text-muted-foreground max-w-md mb-6">
            {channelsError instanceof Error ? channelsError.message : "Network error"}
          </p>
          <Button variant="outline" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      ) : channels.length === 0 ? (
        /* Empty State */
        <div className="flex min-h-[280px] flex-col items-center justify-center rounded-xl border border-dashed p-8 text-center bg-card/40">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary mb-4">
            <Radio className="h-8 w-8" />
          </div>
          <h2 className="text-lg font-semibold text-foreground mb-1">
            No notification channels configured
          </h2>
          <p className="text-sm text-muted-foreground max-w-md mb-6">
            Add an email address or webhook to receive alerts.
          </p>
          <Button
            onClick={() => setIsModalOpen(true)}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            Add Channel
          </Button>
        </div>
      ) : (
        /* Channels Table */
        <section aria-label="Notification channels" className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border px-4 py-3">
            <span className="text-sm font-medium text-foreground">
              {channels.length} {channels.length === 1 ? "channel" : "channels"}
            </span>
            <span className="text-xs text-muted-foreground">{activeCount} enabled</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-left">
              <thead>
                <tr className="border-b border-border bg-muted/30 text-xs text-muted-foreground">
                  <th scope="col" className="px-4 py-3 font-medium">Channel</th>
                  <th scope="col" className="px-4 py-3 font-medium">Destination</th>
                  <th scope="col" className="px-4 py-3 font-medium">Status</th>
                  <th scope="col" className="px-4 py-3 font-medium">Created</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-sm">
                {channels.map((channel) => {
                  const channelType = channel.channelType ?? channel.channel_type;
                  const isWebhook = channelType === "webhook";
                  const destination = isWebhook ? new URL(channel.destination).host : channel.destination;
                  const createdAt = channel.createdAt || channel.created_at;
                  return (
                    <tr key={channel.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-4 px-4 font-medium text-foreground">
                        <div className="flex items-center gap-2.5">
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                            {isWebhook ? <Webhook className="h-4 w-4" /> : <Mail className="h-4 w-4" />}
                          </div>
                          <div>
                            <div className="break-words font-medium text-foreground">{channel.name}</div>
                            <div className="text-xs font-normal text-muted-foreground">
                              {isWebhook ? "Webhook" : "Email"}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-muted-foreground">
                        <span className="block max-w-56 truncate" title={destination}>{destination}</span>
                      </td>
                      <td className="py-4 px-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                            channel.enabled
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              channel.enabled ? "bg-emerald-500" : "bg-muted-foreground"
                            }`}
                          />
                          {channel.enabled ? "Enabled" : "Disabled"}
                        </span>
                      </td>
                      <td className="py-4 px-4 whitespace-nowrap text-xs text-muted-foreground">
                        {createdAt
                          ? new Date(createdAt).toLocaleDateString(undefined, {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            })
                          : "—"}
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="mr-1 min-w-24 gap-2"
                            aria-busy={
                              testChannelMutation.isPending &&
                              testChannelMutation.variables.channelId === channel.id
                            }
                            aria-label={`Test ${channel.name}`}
                            disabled={!projectId || testChannelMutation.isPending}
                            onClick={() => {
                              if (projectId) testChannelMutation.mutate({ projectId, channelId: channel.id });
                            }}
                          >
                            {testChannelMutation.isPending &&
                            testChannelMutation.variables.channelId === channel.id ? (
                              <>
                                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                                Sending…
                              </>
                            ) : (
                              "Test"
                            )}
                          </Button>
                          <Button
                            type="button"
                            size="icon"
                            variant="ghost"
                            className="text-text-secondary"
                            aria-label={`Edit ${channel.name}`}
                            title="Edit channel"
                            onClick={() => handleEditChannel(channel)}
                          >
                            <Pencil className="h-4 w-4" aria-hidden="true" />
                          </Button>
                          <Button
                            type="button"
                            size="icon"
                            variant="ghost"
                            className="text-text-secondary hover:bg-destructive-container hover:text-error-foreground"
                            aria-label={`Delete ${channel.name}`}
                            title="Delete channel"
                            onClick={() => setChannelToDelete(channel)}
                          >
                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Add Notification Channel Modal */}
      {isModalOpen && (
        <dialog
          ref={channelDialogRef}
          aria-labelledby="add-channel-title"
          aria-busy={isSubmitting}
          onCancel={(event) => {
            event.preventDefault();
            if (!isSubmitting) handleCloseModal();
          }}
          className="fixed inset-auto left-1/2 top-1/2 m-0 -translate-x-1/2 -translate-y-1/2 max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-2xl overflow-hidden rounded-2xl border border-border bg-card text-card-foreground shadow-2xl backdrop:bg-black/50"
        >
          <div className="flex max-h-[calc(100dvh-2rem-2px)] flex-col">
            {/* Modal Header */}
            <div className="shrink-0 px-6 py-5 border-b border-border flex items-center justify-between bg-card">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                  <Radio className="h-5 w-5" />
                </div>
                <div>
                  <h3 id="add-channel-title" className="text-lg font-semibold text-foreground">
                    {editingChannel ? "Edit Notification Channel" : "Add Notification Channel"}
                  </h3>
                </div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={handleCloseModal}
                disabled={isSubmitting}
                autoFocus
                aria-label="Close notification channel dialog"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>

            {/* Modal Body */}
            <div className="min-h-0 p-6 space-y-6 overflow-y-auto">
              {formValidationError && (
                <div className="flex items-center gap-2.5 rounded-lg border border-error/30 bg-error-container p-3.5 text-error text-body-sm font-medium">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{formValidationError}</span>
                </div>
              )}

              {!editingChannel && (
                <div className="space-y-2">
                  <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                    Channel Type
                  </Label>
                  <div className="grid grid-cols-3 gap-3">
                    {/* Email Option - Default & Active */}
                    <button
                      type="button"
                      onClick={() => handleSelectChannelType("email")}
                      aria-pressed={channelType === "email"}
                      disabled={isSubmitting}
                      className={`p-3.5 rounded-xl text-left border transition-all flex flex-col gap-2 ${
                        channelType === "email"
                          ? "border-primary bg-primary/5 shadow-sm"
                          : "border-border bg-card hover:bg-muted/50"
                      }`}
                    >
                      <div className="flex items-center justify-between w-full">
                        <Mail className="h-5 w-5 text-primary" />
                        {channelType === "email" && <span className="w-2 h-2 rounded-full bg-primary" />}
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-foreground">Email</div>
                        <div className="text-xs text-muted-foreground">Managed relay</div>
                      </div>
                    </button>

                    {/* Slack Option - Disabled */}
                    <button
                      type="button"
                      disabled
                      aria-disabled="true"
                      className="p-3.5 rounded-xl text-left border border-border bg-muted/40 opacity-60 cursor-not-allowed flex flex-col gap-2"
                    >
                      <div className="flex items-center justify-between w-full">
                        <MessageSquare className="h-5 w-5 text-muted-foreground" />
                        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                          Soon
                        </span>
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-muted-foreground">Slack</div>
                        <div className="text-xs text-muted-foreground">Incoming Webhook</div>
                      </div>
                    </button>

                    {/* Webhook Option */}
                    <button
                      type="button"
                      onClick={() => handleSelectChannelType("webhook")}
                      aria-pressed={channelType === "webhook"}
                      disabled={isSubmitting}
                      className={`p-3.5 rounded-xl text-left border transition-all flex flex-col gap-2 ${
                        channelType === "webhook"
                          ? "border-primary bg-primary/5 shadow-sm"
                          : "border-border bg-card hover:bg-muted/50"
                      }`}
                    >
                      <div className="flex items-center justify-between w-full">
                        <Webhook className="h-5 w-5 text-primary" />
                        {channelType === "webhook" && <span className="w-2 h-2 rounded-full bg-primary" />}
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-foreground">Webhook</div>
                        <div className="text-xs text-muted-foreground">Signed HTTP POST</div>
                      </div>
                    </button>
                  </div>
                </div>

              )}
              {/* Email Form Panel */}
              {channelType === "email" && (
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="channelName">Channel Name</Label>
                    <Input
                      id="channelName"
                      placeholder="e.g. Platform SRE Leads"
                      value={channelName}
                      onChange={(e) => setChannelName(e.target.value)}
                      disabled={saveEmailChannelMutation.isPending}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="recipientEmail">Recipient Email Addresses</Label>
                    <div className="p-2.5 rounded-lg border border-input bg-background space-y-2">
                      {recipients.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {recipients.map((email) => (
                            <span
                              key={email}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-muted text-xs font-mono text-foreground"
                            >
                              {email}
                              <button
                                type="button"
                                onClick={() => handleRemoveRecipient(email)}
                                className="text-muted-foreground hover:text-destructive transition-colors"
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </span>
                          ))}
                        </div>
                      )}
                      <input
                        id="recipientEmail"
                        type="email"
                        placeholder={editingChannel ? "Recipient email address" : "Add email address and press enter..."}
                        value={recipientEmail}
                        onChange={(e) => setRecipientEmail(e.target.value)}
                        onKeyDown={editingChannel ? undefined : handleAddRecipient}
                        disabled={saveEmailChannelMutation.isPending}
                        className="w-full bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground"
                      />
                    </div>
                    {editingChannel && (
                      <Label className="mt-3 flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={emailEnabled}
                          disabled={isSubmitting}
                          onChange={(event) => setEmailEnabled(event.target.checked)}
                        />
                        Enabled
                      </Label>
                    )}
                  </div>
                </div>
              )}
              {channelType === "webhook" && (
                <WebhookChannelForm
                  formId={webhookFormId}
                  editingChannel={editingChannel ?? undefined}
                  channelName={channelName}
                  onChannelNameChange={setChannelName}
                  onSave={handleSaveWebhook}
                />
              )}
            </div>

            {/* Modal Footer */}
            <div className="shrink-0 px-6 py-4 bg-muted/30 border-t border-border flex items-center justify-end gap-3">
              <Button
                variant="outline"
                type="button"
                disabled={isSubmitting}
                onClick={handleCloseModal}
              >
                Cancel
              </Button>
              <Button
                type={channelType === "webhook" ? "submit" : "button"}
                form={channelType === "webhook" ? webhookFormId : undefined}
                disabled={isSubmitting || (channelType === "webhook" && !projectId)}
                onClick={channelType === "email" ? handleSaveChannel : undefined}
                className="min-w-32 gap-2"
                aria-busy={isSubmitting}
              >
                {isSubmitting && (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                )}
                {isSubmitting ? "Saving…" : "Save channel"}
              </Button>
            </div>
          </div>
        </dialog>
      )}
      {channelToDelete && (
        <ConfirmationDialog
          title="Delete notification channel?"
          confirmLabel="Delete channel"
          pending={deleteChannelMutation.isPending}
          onCancel={() => setChannelToDelete(null)}
          onConfirm={() => {
            if (projectId) deleteChannelMutation.mutate({ projectId, channelId: channelToDelete.id });
          }}
        >
          Deleting <strong>{channelToDelete.name}</strong> also removes its alert rule
          associations, queued deliveries, and delivery history.
        </ConfirmationDialog>
      )}
      {webhookConfirmation && webhookConfirmation.projectId === projectId && (
        <WebhookSigningSecretDialog
          secret={webhookConfirmation.secret}
          onClose={() => setWebhookConfirmation(null)}
        />
      )}
    </div>
  );
}
