"use client";

import Link from "next/link";

import { Mark } from "@/components/brand/mark";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { cn } from "@/lib/utils";

export function AgentHeader({
  isWorking,
  rightSlot,
}: {
  isWorking: boolean;
  rightSlot?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border/60 bg-background/70 px-4 py-2 backdrop-blur-xl md:px-6">
      <Link
        href="/"
        className="flex items-center gap-2.5 rounded-md focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
      >
        <Mark />
        <div className="leading-tight">
          <p className="font-display text-[13px] font-semibold">Shopping Agent</p>
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
            {isWorking ? "Working" : "Ready — ask for anything on the shelves"}
          </p>
        </div>
      </Link>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        {rightSlot}
      </div>
    </div>
  );
}
