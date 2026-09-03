"use client";

import { Search, Sparkles } from "lucide-react";

import type { ToolStatus } from "@/lib/queries/use-chat";
import { cn } from "@/lib/utils";

const TOOL_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  search_catalog: Search,
  get_product_details: Sparkles,
};

export function ToolActivity({ status }: { status: ToolStatus }) {
  const Icon = TOOL_ICONS[status.tool] || Sparkles;

  return (
    <div className="flex w-fit items-center gap-2 rounded-full border bg-muted/60 px-3 py-1.5 text-xs text-muted-foreground">
      <span className="relative flex size-2">
        <span
          className={cn(
            "absolute inline-flex size-full animate-ping rounded-full bg-primary/60",
            status.phase === "done" && "hidden"
          )}
        />
        <span className="relative inline-flex size-2 rounded-full bg-primary" />
      </span>
      <Icon className="size-3.5" />
      <span>{status.label}</span>
    </div>
  );
}
