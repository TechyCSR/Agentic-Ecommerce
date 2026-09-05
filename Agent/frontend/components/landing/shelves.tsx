"use client";

import { useHighlights } from "@/lib/queries/use-highlights";

/** The shelves that are genuinely stocked, straight from the live catalog. */
export function Shelves() {
  const { data } = useHighlights();
  const shelves = data?.categories.filter((c) => c.product_count >= 5).slice(0, 14) ?? [];

  if (shelves.length === 0) return null;

  return (
    <ul className="mt-9 flex flex-wrap gap-2">
      {shelves.map((shelf) => (
        <li
          key={shelf.name}
          className="rounded-lg border border-border/70 px-3 py-1.5 text-sm text-muted-foreground"
        >
          {shelf.name}
          <span className="ml-1.5 tabular-nums text-foreground/50">{shelf.product_count}</span>
        </li>
      ))}
    </ul>
  );
}
