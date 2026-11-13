"use client";

import React, { useState } from "react";
import {
  Bell,
  Trash2,
  AlertTriangle,
  Loader2,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertRule } from "../types";

interface AlertRulesListProps {
  rules: AlertRule[];
  onDeleteRule?: (id: string) => Promise<void>;
  onToggleRule?: (id: string) => void;
}

export function AlertRulesList({
  rules,
  onDeleteRule,
  onToggleRule,
}: AlertRulesListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [ruleToDelete, setRuleToDelete] = useState<AlertRule | null>(null);

  const confirmDelete = async () => {
    if (!ruleToDelete || !onDeleteRule) return;
    setDeletingId(ruleToDelete.id);
    try {
      await onDeleteRule(ruleToDelete.id);
    } finally {
      setDeletingId(null);
      setRuleToDelete(null);
    }
  };

  const getSeverityBadgeVariant = (severity: AlertRule["severity"]) => {
    switch (severity) {
      case "critical":
        return "error";
      case "warning":
        return "warning";
      case "info":
      default:
        return "info";
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <>
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <th className="py-3.5 px-4">Name</th>
                <th className="py-3.5 px-4">Rule Type</th>
                <th className="py-3.5 px-4">Environment</th>
                <th className="py-3.5 px-4">Channels</th>
                <th className="py-3.5 px-4">Severity</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Created</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border text-sm">
              {rules.map((rule) => {
                const isDeleting = deletingId === rule.id;
                return (
                  <tr
                    key={rule.id}
                    className="hover:bg-muted/30 transition-colors group"
                  >
                    {/* Name */}
                    <td className="py-4 px-4 font-medium text-foreground">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
                          <Bell className="h-4 w-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold text-foreground truncate max-w-[200px]">
                            {rule.name}
                          </div>
                          <div className="text-xs text-muted-foreground font-mono truncate max-w-[140px]">
                            {rule.id.slice(0, 8)}...
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Rule Type */}
                    <td className="py-4 px-4 whitespace-nowrap">
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-container text-xs font-medium text-foreground border border-outline-variant/30">
                        <span>New issue detected</span>
                      </div>
                    </td>

                    {/* Environment */}
                    <td className="py-4 px-4 whitespace-nowrap">
                      {rule.environment ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded font-mono text-xs bg-muted text-foreground border border-border">
                          {rule.environment}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground italic">
                          All environments
                        </span>
                      )}
                    </td>

                    {/* Channels */}
                    <td className="py-4 px-4">
                      <div className="flex flex-wrap gap-1.5 max-w-[240px]">
                        {rule.channels.length === 0 ? (
                          <span className="text-xs text-muted-foreground">None</span>
                        ) : (
                          rule.channels.map((channel) => (
                            <span
                              key={channel.id}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-muted text-[11px] font-medium text-foreground border border-border/50"
                            >
                              <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                              <span className="truncate max-w-[120px]">
                                {channel.name}
                              </span>
                            </span>
                          ))
                        )}
                      </div>
                    </td>

                    {/* Severity */}
                    <td className="py-4 px-4 whitespace-nowrap">
                      <Badge
                        variant={getSeverityBadgeVariant(rule.severity)}
                        showDot={true}
                      >
                        {rule.severity}
                      </Badge>
                    </td>

                    {/* Enabled / Status */}
                    <td className="py-4 px-4 whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => onToggleRule && onToggleRule(rule.id)}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                          rule.enabled
                            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20"
                            : "bg-muted text-muted-foreground hover:bg-muted/80"
                        }`}
                        title="Click to toggle status"
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            rule.enabled ? "bg-emerald-500" : "bg-muted-foreground"
                          }`}
                        />
                        {rule.enabled ? "Active" : "Disabled"}
                      </button>
                    </td>

                    {/* Created Date */}
                    <td className="py-4 px-4 whitespace-nowrap text-xs text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5 text-muted-foreground/70" />
                        <span>{formatDate(rule.created_at)}</span>
                      </div>
                    </td>

                    {/* Row Actions */}
                    <td className="py-4 px-4 whitespace-nowrap text-right">
                      {onDeleteRule && (
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={isDeleting}
                          onClick={() => setRuleToDelete(rule)}
                          className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 h-8 w-8 p-0"
                          title="Delete alert rule"
                        >
                          {isDeleting ? (
                            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                          <span className="sr-only">Delete</span>
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {ruleToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in-50">
          <div className="w-full max-w-md rounded-2xl bg-card border border-border shadow-2xl overflow-hidden p-6 space-y-4 animate-in zoom-in-95">
            <div className="flex items-center gap-3 text-destructive">
              <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-foreground">
                  Delete Alert Rule
                </h3>
                <p className="text-xs text-muted-foreground">
                  This action cannot be undone.
                </p>
              </div>
            </div>

            <p className="text-sm text-muted-foreground">
              Are you sure you want to delete the alert rule{" "}
              <strong className="text-foreground">
                "{ruleToDelete.name}"
              </strong>
              ? Notifications configured for this rule will no longer trigger.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2 border-t border-border">
              <Button
                variant="outline"
                type="button"
                disabled={deletingId === ruleToDelete.id}
                onClick={() => setRuleToDelete(null)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                type="button"
                disabled={deletingId === ruleToDelete.id}
                onClick={confirmDelete}
                className="gap-2"
              >
                {deletingId === ruleToDelete.id && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                Delete Rule
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
