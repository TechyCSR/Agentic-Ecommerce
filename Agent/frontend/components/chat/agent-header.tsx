"use client";

import Link from "next/link";

import { Mark } from "@/components/brand/mark";
import { StoreBadge } from "@/components/chat/store-badge";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { useHighlights } from "@/lib/queries/use-highlights";
import { cn } from "@/lib/utils";

export function AgentHeader({
  isWorking,
  rightSlot,
}: {
  isWorking: boolean;
  rightSlot?: React.ReactNode;
}) {
  const { data } = useHighlights();

  return (
    <div className="flex items-center justify-between gap-3 border-b border-border/60 bg-background/70 px-4 py-2 backdrop-blur-xl md:px-6">
      <div className="flex min-w-0 items-center gap-2.5">
        <Link
          href="/"
          aria-label="Agentic Commerce home"
          className="rounded-md focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          <Mark />
        </Link>

        <div className="min-w-0 leading-tight">
          <div className="flex items-center gap-2">
            <Link
              href="/"
              className="font-display truncate text-[13px] font-semibold hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >
              Shopping Agent
            </Link>
            <CatalogSize />
          </div>

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
            <span className="truncate">
              {isWorking
                ? "Working on it"
                : data?.category_count
                  ? `Ready to search ${data.category_count} shelves`
                  : "Ready when you are"}
            </span>
          </p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <StoreBadge compact />
        <ThemeToggle />
        {rightSlot}
      </div>
    </div>
  );
}

/**
 * How much is actually on the shelves, beside the name it belongs to.
 *
 * Live rather than a fixed figure, and hidden until it arrives — a "0
 * products" flash on every load would say the opposite of what this is for.
 */
function CatalogSize() {
  const { data } = useHighlights();
  if (!data || data.product_count === 0) return null;

  return (
    <span
      className="hidden shrink-0 items-center gap-1.5 rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs text-muted-foreground sm:inline-flex"
      title={`${data.category_count} categories from ${data.brand_count} brands, updated live`}
    >
      <span className="text-sm font-semibold tabular-nums text-foreground">
        {data.product_count.toLocaleString("en-IN")}
      </span>
      products
    </span>
  );
}
