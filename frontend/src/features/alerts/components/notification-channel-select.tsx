"use client";

import * as React from "react";
import { Check, ChevronDown, Mail, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { NotificationChannel } from "../types";

interface NotificationChannelSelectProps {
  channels: NotificationChannel[];
  value: string[];
  onChange: (value: string[]) => void;
  disabled?: boolean;
  hasError?: boolean;
}

export function NotificationChannelSelect({
  channels,
  value = [],
  onChange,
  disabled = false,
  hasError = false,
}: NotificationChannelSelectProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const toggleChannel = (channelId: string) => {
    if (disabled) return;
    if (value.includes(channelId)) {
      onChange(value.filter((id) => id !== channelId));
    } else {
      onChange([...value, channelId]);
    }
  };

  const removeChannel = (e: React.MouseEvent, channelId: string) => {
    e.stopPropagation();
    if (disabled) return;
    onChange(value.filter((id) => id !== channelId));
  };

  const selectedChannels = channels.filter((c) => value.includes(c.id));

  return (
    <div className="relative w-full" ref={containerRef}>
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        onClick={() => !disabled && setIsOpen((prev) => !prev)}
        onKeyDown={(e) => {
          if (disabled) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setIsOpen((prev) => !prev);
          }
        }}
        className={cn(
          "flex min-h-[42px] w-full items-center justify-between rounded-lg border bg-surface-container-lowest px-3 py-1.5 text-body-md transition-all cursor-pointer shadow-sm",
          hasError
            ? "border-error focus:ring-2 focus:ring-error/20"
            : "border-outline-variant/60 hover:border-outline focus:border-primary focus:ring-2 focus:ring-primary/20",
          disabled && "cursor-not-allowed opacity-50 bg-surface-dim",
          isOpen && "ring-2 ring-primary/20 border-primary"
        )}
      >
        <div className="flex flex-wrap items-center gap-1.5 flex-1 pr-2">
          {selectedChannels.length === 0 ? (
            <span className="text-text-muted select-none text-body-md">
              Select one or more notification channels...
            </span>
          ) : (
            selectedChannels.map((channel) => (
              <span
                key={channel.id}
                className="inline-flex items-center gap-1.5 rounded-md bg-surface-container-high px-2 py-0.5 text-body-sm font-medium text-on-surface border border-outline-variant/40"
              >
                <Mail className="h-3.5 w-3.5 text-primary shrink-0" />
                <span className="truncate max-w-[160px]">{channel.name}</span>
                <button
                  type="button"
                  onClick={(e) => removeChannel(e, channel.id)}
                  disabled={disabled}
                  className="rounded-full hover:bg-surface-container-highest p-0.5 text-text-secondary hover:text-text-primary transition-colors"
                >
                  <X className="h-3 w-3" />
                  <span className="sr-only">Remove {channel.name}</span>
                </button>
              </span>
            ))
          )}
        </div>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-text-secondary transition-transform duration-200",
            isOpen && "rotate-180"
          )}
        />
      </div>

      {isOpen && (
        <div
          role="listbox"
          aria-multiselectable="true"
          className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-border bg-card p-1 shadow-level-3 animate-in fade-in-50 zoom-in-95"
        >
          {channels.length === 0 ? (
            <div className="py-3 px-4 text-center text-body-sm text-text-muted">
              No enabled notification channels available
            </div>
          ) : (
            channels.map((channel) => {
              const isSelected = value.includes(channel.id);
              return (
                <div
                  key={channel.id}
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => toggleChannel(channel.id)}
                  className={cn(
                    "flex items-center justify-between rounded-md px-3 py-2 text-body-sm cursor-pointer transition-colors select-none",
                    isSelected
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-text-primary hover:bg-canvas"
                  )}
                >
                  <div className="flex items-center gap-2.5 min-w-0 pr-2">
                    <div
                      className={cn(
                        "flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors",
                        isSelected
                          ? "border-primary bg-primary text-on-primary"
                          : "border-outline-variant bg-surface-container-lowest"
                      )}
                    >
                      {isSelected && <Check className="h-3 w-3 stroke-[3]" />}
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="truncate font-medium text-on-surface">
                        {channel.name}
                      </span>
                      <span className="truncate text-body-sm text-text-secondary text-[11px]">
                        {channel.destination}
                      </span>
                    </div>
                  </div>
                  <span className="text-label-sm font-mono uppercase text-text-muted shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-surface-container">
                    {channel.channel_type}
                  </span>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
