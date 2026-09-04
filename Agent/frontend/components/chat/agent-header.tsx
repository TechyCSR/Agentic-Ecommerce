"use client";

import { Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";

export function AgentHeader({
  isWorking,
  rightSlot,
}: {
  isWorking: boolean;
  rightSlot?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b bg-background px-4 py-2 md:px-6">
      <div className="flex items-center gap-2.5">
        <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Sparkles className="size-3.5" />
        </div>
        <div className="leading-tight">
          <p className="text-[13px] font-semibold">Shopping Agent</p>
          <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="relative flex size-1.5">
              {isWorking && (
                <span className="absolute inline-flex size-1.5 animate-ping rounded-full bg-amber-500" />
              )}
              <span
                className={cn(
                  "relative inline-flex size-1.5 rounded-full",
                  isWorking ? "bg-amber-500" : "bg-emerald-500"
                )}
              />
            </span>
            {isWorking ? "Working" : "Online · Ready to help you find the right product"}
          </p>
        </div>
      </div>
      {rightSlot}
    </div>
  );
}
