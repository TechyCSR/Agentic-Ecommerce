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
}: {
  storeName?: string | null;
  merchantName?: string | null;
  className?: string;
}) {
  const { data, isPending, isError } = useHighlights();
  const name = storeName || merchantName;
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
        "group/store inline-flex max-w-full items-center gap-1.5 rounded-md border border-border/70 px-1.5 py-0.5",
        "text-[11px] text-muted-foreground transition-colors duration-150",
        "hover:border-foreground/25 hover:text-foreground",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        className
      )}
      onClick={(e) => e.stopPropagation()}
    >
      <span className="relative flex size-3.5 shrink-0 items-center justify-center">
        <Store className="size-3" />
        <span
          aria-hidden="true"
          className={cn(
            "absolute -top-0.5 -right-0.5 size-1.5 rounded-full ring-2 ring-card",
            unknown ? "bg-muted-foreground/40" : live ? "bg-emerald-500" : "bg-destructive"
          )}
        />
      </span>
      <span className="truncate">{name}</span>
      <span className="sr-only">
        {unknown ? "Store status unknown" : live ? "Store is live" : "Store is not responding"}
      </span>
    </a>
  );
}
