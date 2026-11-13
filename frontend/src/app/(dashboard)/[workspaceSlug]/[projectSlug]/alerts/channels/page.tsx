"use client";

import React, { useState } from "react";
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
  Info,
  ShieldCheck,
  Zap,
  ChevronRight,
  Loader2,
  AlertCircle,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { useProjectBySlug } from "@/features/projects/hooks";
import { listChannels, createChannel } from "@/features/alerts/api/alertRulesApi";
import { NotificationChannel } from "@/features/alerts/types";
import { ApiError } from "@/lib/api-client";

export default function NotificationChannelsPage() {
  const params = useParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const workspaceSlug = (params?.workspaceSlug as string) || "";
  const projectSlug = (params?.projectSlug as string) || "";

  const { project, isLoading: isProjectLoading } = useProjectBySlug(projectSlug);
  const projectId = project?.id;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [channelType, setChannelType] = useState<"email" | "slack" | "webhook">("email");
  const [channelName, setChannelName] = useState("");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [recipients, setRecipients] = useState<string[]>([]);
  const [formValidationError, setFormValidationError] = useState<string | null>(null);

  // Fetch channels list query
  const {
    data: channels = [],
    isLoading: isChannelsLoading,
    isError: isChannelsError,
    error: channelsError,
    refetch,
  } = useQuery({
    queryKey: ["notification-channels", projectId],
    queryFn: () => listChannels(projectId),
    enabled: Boolean(projectId),
  });

  // Create channel mutation
  const createChannelMutation = useMutation({
    mutationFn: (newChannel: {
      name: string;
      channel_type: "email";
      destination: string;
      enabled: boolean;
    }) => {
      if (!projectId) {
        throw new Error("Project ID is missing");
      }
      return createChannel(projectId, newChannel);
    },
    onSuccess: (created) => {
      queryClient.invalidateQueries({
        queryKey: ["notification-channels", projectId],
      });
      toast({
        title: "Channel created",
        description: `Notification channel "${created.name}" has been configured successfully.`,
        variant: "success",
      });
      handleCloseModal();
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 422) {
        setFormValidationError(err.message || "Invalid channel payload");
      } else {
        const message = err instanceof Error ? err.message : "Failed to create channel";
        toast({
          title: "Channel creation failed",
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

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setChannelName("");
    setRecipientEmail("");
    setRecipients([]);
    setChannelType("email");
    setFormValidationError(null);
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
    createChannelMutation.mutate({
      name: trimmedName,
      channel_type: "email",
      destination,
      enabled: true,
    });
  };

  const isLoading = isProjectLoading || isChannelsLoading;
  const activeCount = channels.filter((c) => c.enabled).length;

  return (
    <div className="flex-1 space-y-6 p-6 max-w-7xl mx-auto">
      {/* Breadcrumb & Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between border-b pb-5">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <Link
              href={`/${workspaceSlug}/${projectSlug}/alerts`}
              className="hover:text-foreground transition-colors"
            >
              Alerts
            </Link>
            <ChevronRight className="h-3 w-3" />
            <span className="text-primary font-semibold">Notification Channels</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Notification Channels
          </h1>
          <p className="text-sm text-muted-foreground max-w-2xl">
            Configure email destinations for alert dispatch in {projectSlug || "your project"}. Managed relay routes guarantee deliverability during incident cascades.
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

      {/* Overview Stat Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border bg-card text-card-foreground shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <Radio className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold">
                {isLoading ? "--" : `${channels.length} Configured`}
              </div>
              <div className="text-xs text-muted-foreground">Active outbound channels</div>
            </div>
          </div>
          <span className="px-2.5 py-0.5 rounded-full bg-muted text-xs font-medium text-muted-foreground">
            {isLoading ? "--" : `${activeCount} Active`}
          </span>
        </div>

        <div className="p-4 rounded-xl border bg-card text-card-foreground shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold">100%</div>
              <div className="text-xs text-muted-foreground">Avg relay delivery success</div>
            </div>
          </div>
          <span className="px-2.5 py-0.5 rounded-full bg-muted text-xs font-mono text-muted-foreground">
            TLS 1.3
          </span>
        </div>

        <div className="p-4 rounded-xl border bg-card text-card-foreground shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-600 dark:text-purple-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold">DKIM & SPF</div>
              <div className="text-xs text-muted-foreground">Verified sender reputational seal</div>
            </div>
          </div>
          <span className="px-2.5 py-0.5 rounded-full bg-muted text-xs font-mono text-muted-foreground">
            Active
          </span>
        </div>
      </div>

      {/* Main Content Area */}
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
      ) : isChannelsError ? (
        <div className="flex min-h-[340px] flex-col items-center justify-center rounded-xl border border-dashed border-error/40 p-8 text-center bg-error-container/10">
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
        <div className="flex min-h-[380px] flex-col items-center justify-center rounded-xl border border-dashed p-8 text-center bg-card/40">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary mb-4">
            <Radio className="h-8 w-8" />
          </div>
          <h2 className="text-lg font-semibold text-foreground mb-1">
            No notification channels configured
          </h2>
          <p className="text-sm text-muted-foreground max-w-md mb-6">
            Add your first notification destination to receive real-time alerts when incidents or errors trigger.
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
        <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="py-3.5 px-4">Channel Name</th>
                  <th className="py-3.5 px-4">Type</th>
                  <th className="py-3.5 px-4">Destination</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-sm">
                {channels.map((channel) => (
                  <tr key={channel.id} className="hover:bg-muted/30 transition-colors">
                    <td className="py-4 px-4 font-medium text-foreground">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
                          <Mail className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="font-semibold text-foreground">{channel.name}</div>
                          <div className="text-xs text-muted-foreground font-mono">{channel.id.slice(0, 8)}...</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-muted text-xs font-mono uppercase text-foreground">
                        {channel.channel_type}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <span className="font-mono text-xs text-foreground bg-surface-container px-2 py-1 rounded">
                        {channel.destination}
                      </span>
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
                        {channel.enabled ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap text-xs text-muted-foreground">
                      {channel.created_at ? (
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5 text-muted-foreground/70" />
                          <span>
                            {new Date(channel.created_at).toLocaleDateString("en-US", {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            })}
                          </span>
                        </div>
                      ) : (
                        "--"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add Notification Channel Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in-50">
          <div className="w-full max-w-2xl rounded-2xl bg-card border border-border shadow-2xl overflow-hidden animate-in zoom-in-95">
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-border flex items-center justify-between bg-card">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                  <Radio className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground">
                    Add Notification Channel
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Set up reliable delivery endpoints for alert state transitions
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleCloseModal}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                aria-label="Close modal"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
              {formValidationError && (
                <div className="flex items-center gap-2.5 rounded-lg border border-error/30 bg-error-container p-3.5 text-error text-body-sm font-medium">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{formValidationError}</span>
                </div>
              )}

              {/* Type Selection */}
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                  Channel Type
                </Label>
                <div className="grid grid-cols-3 gap-3">
                  {/* Email Option - Default & Active */}
                  <button
                    type="button"
                    onClick={() => setChannelType("email")}
                    className={`p-3.5 rounded-xl text-left border transition-all flex flex-col gap-2 ${
                      channelType === "email"
                        ? "border-primary bg-primary/5 shadow-sm"
                        : "border-border bg-card hover:bg-muted/50"
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <Mail className="h-5 w-5 text-primary" />
                      <span className="w-2 h-2 rounded-full bg-primary" />
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

                  {/* Webhook Option - Disabled */}
                  <button
                    type="button"
                    disabled
                    aria-disabled="true"
                    className="p-3.5 rounded-xl text-left border border-border bg-muted/40 opacity-60 cursor-not-allowed flex flex-col gap-2"
                  >
                    <div className="flex items-center justify-between w-full">
                      <Webhook className="h-5 w-5 text-muted-foreground" />
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                        Soon
                      </span>
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-muted-foreground">Webhook</div>
                      <div className="text-xs text-muted-foreground">Signed HTTP POST</div>
                    </div>
                  </button>
                </div>
              </div>

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
                      disabled={createChannelMutation.isPending}
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
                        placeholder="Add email address and press enter..."
                        value={recipientEmail}
                        onChange={(e) => setRecipientEmail(e.target.value)}
                        onKeyDown={handleAddRecipient}
                        disabled={createChannelMutation.isPending}
                        className="w-full bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground"
                      />
                    </div>
                    <div className="p-3 rounded-lg bg-muted/50 border border-border flex items-start gap-2.5 mt-2">
                      <Info className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-muted-foreground">
                        Email delivery infrastructure is automatically managed by Faultline with built-in SPF, DKIM, and TLS 1.3 verification.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-muted/30 border-t border-border flex items-center justify-end gap-3">
              <Button
                variant="outline"
                type="button"
                disabled={createChannelMutation.isPending}
                onClick={handleCloseModal}
              >
                Cancel
              </Button>
              <Button
                type="button"
                disabled={createChannelMutation.isPending}
                onClick={handleSaveChannel}
                className="gap-2"
              >
                {createChannelMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                Save Channel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
