"use client";

import { Check, Copy, Pencil, RefreshCw, Wrench, X } from "lucide-react";
import { useState } from "react";

import { AgentActivity } from "@/components/chat/agent-activity";
import { Button } from "@/components/ui/button";
import type { ActivityStep } from "@/lib/types";
import { cn } from "@/lib/utils";

function timeOf(iso: string) {
  const d = new Date(iso);
  const today = new Date();
  const sameDay = d.toDateString() === today.toDateString();
  return sameDay
    ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
}

/** Timestamp plus hover actions. Actions stay visible on touch devices,
 * where there is no hover to reveal them. */
export function MessageActions({
  createdAt,
  content,
  align = "left",
  onRetry,
  onEdit,
  activity,
}: {
  createdAt: string;
  content: string;
  align?: "left" | "right";
  onRetry?: () => void;
  onEdit?: () => void;
  activity?: ActivityStep[] | null;
}) {
  const [copied, setCopied] = useState(false);
  const [showTrace, setShowTrace] = useState(false);

  const hasTrace = (activity?.length ?? 0) > 0;

  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be blocked (insecure context, permissions) — silently
      // skip rather than throwing an error at someone copying a message.
    }
  }

  return (
    <div className={cn("flex flex-col gap-1.5", align === "right" && "items-end")}>
      <div
        className={cn(
          "flex items-center gap-1 text-[11px] text-muted-foreground",
          align === "right" && "flex-row-reverse"
        )}
      >
        <span>{timeOf(createdAt)}</span>

        <div className="flex items-center opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100 max-sm:opacity-100">
          <Button
            variant="ghost"
            size="icon-sm"
            className="size-6 text-muted-foreground"
            onClick={copy}
            aria-label="Copy message"
            title="Copy"
          >
            {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
          </Button>

          {onEdit && (
            <Button
              variant="ghost"
              size="icon-sm"
              className="size-6 text-muted-foreground"
              onClick={onEdit}
              aria-label="Edit and resend"
              title="Edit & resend"
            >
              <Pencil className="size-3" />
            </Button>
          )}

          {onRetry && (
            <Button
              variant="ghost"
              size="icon-sm"
              className="size-6 text-muted-foreground"
              onClick={onRetry}
              aria-label="Regenerate reply"
              title="Regenerate"
            >
              <RefreshCw className="size-3" />
            </Button>
          )}

          {hasTrace && (
            <Button
              variant="ghost"
              size="icon-sm"
              className={cn("size-6 text-muted-foreground", showTrace && "text-foreground")}
              onClick={() => setShowTrace((v) => !v)}
              aria-label="Show what the agent did"
              title="What the agent did"
            >
              <Wrench className="size-3" />
            </Button>
          )}
        </div>
      </div>

      {hasTrace && showTrace && (
        <div className="animate-in fade-in slide-in-from-top-1 w-full max-w-md rounded-xl border bg-muted/30 p-2 duration-200">
          <div className="mb-1 flex items-center justify-between px-1">
            <span className="text-[11px] font-medium text-muted-foreground">
              What the agent did
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              className="size-5"
              onClick={() => setShowTrace(false)}
              aria-label="Close"
            >
              <X className="size-3" />
            </Button>
          </div>
          <AgentActivity steps={activity ?? []} />
        </div>
      )}
    </div>
  );
}
