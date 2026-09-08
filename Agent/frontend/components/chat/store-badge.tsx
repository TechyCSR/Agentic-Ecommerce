"use client";

import { Store } from "lucide-react";

import { useHighlights } from "@/lib/queries/use-highlights";
import { cn } from "@/lib/utils";

const MERCHANT_URL =
  process.env.NEXT_PUBLIC_MERCHANT_URL || "https://merchant.techycsr.dev";

/**
 * Who is actually selling this, and whether their store is answering.
 *
 * The dot is not decorative: the catalog this agent shows comes from the
 * merchant service over its API, so if that service is unreachable the
 * agent has nothing real to sell. `useHighlights` is the same call the rest
 * of the app leans on, so a green dot means the catalog genuinely answered.
 */
export function StoreBadge({
  storeName,
  merchantName,
  className,
  /** Icon and status only — for the navbar, where there is no room for a
   *  name and the store is the same one for every product anyway. */
  compact = false,
}: {
  storeName?: string | null;
  merchantName?: string | null;
  className?: string;
  compact?: boolean;
}) {
  const { data, isPending, isError } = useHighlights();
  const name = storeName || merchantName || (compact ? "Merchant store" : null);
  if (!name) return null;

  const live = Boolean(data && data.product_count > 0);
  const unknown = isPending && !isError;

  return (
    <a
      href={MERCHANT_URL}
      target="_blank"
      rel="noopener noreferrer"
      title={
        unknown
          ? `${name} — checking the store`
          : live
            ? `${name} is live. Opens the merchant storefront in a new tab.`
            : `${name} isn't answering right now.`
      }
      className={cn(
        "group/store inline-flex max-w-full items-center rounded-md border border-border text-foreground/85",
        "transition-colors duration-150 hover:border-foreground/40 hover:bg-muted hover:text-foreground",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        compact
          ? "size-9 justify-center"
          : "gap-1.5 bg-muted/40 px-2 py-1 text-xs font-medium",
        className
      )}
      onClick={(e) => e.stopPropagation()}
    >
      <span className="relative flex size-4 shrink-0 items-center justify-center">
        <Store className="size-3.5" />
        <span
          aria-hidden="true"
          className={cn(
            "absolute -top-1 -right-1 size-2 rounded-full ring-2 ring-card",
            unknown ? "bg-muted-foreground/40" : live ? "bg-emerald-500" : "bg-destructive"
          )}
        />
      </span>
      {!compact && <span className="truncate">{name}</span>}
      <span className="sr-only">
        {unknown ? "Store status unknown" : live ? "Store is live" : "Store is not responding"}
      </span>
    </a>
  );
}
