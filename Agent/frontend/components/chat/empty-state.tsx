"use client";

import { Mark } from "@/components/brand/mark";
import { useHighlights } from "@/lib/queries/use-highlights";

/**
 * The chat's opening screen.
 *
 * Openers are built from the shelves that are actually stocked right now,
 * so the agent never opens by offering something it would then fail to
 * find. The fallbacks below only appear if the catalog can't be reached.
 */
const FALLBACK_STARTERS = [
  "What do you sell?",
  "Show me something under ₹2,000",
  "Find a gift for someone",
];

function openersFor(categories: string[]): string[] {
  if (categories.length === 0) return FALLBACK_STARTERS;

  // Vary the phrasing: a column of "Browse X" reads as a menu, not a
  // conversation, and the point is that plain sentences work.
  const shapes = [
    (c: string) => `Show me ${c.toLowerCase()}`,
    (c: string) => `What ${c.toLowerCase()} do you have?`,
    (c: string) => `Best ${c.toLowerCase()} under ₹5,000`,
    (c: string) => `Compare two ${c.toLowerCase()}`,
  ];
  return categories
    .slice(0, 4)
    .map((c, i) => shapes[i % shapes.length](c))
    .concat("What do you sell?")
    .slice(0, 5);
}

export function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  const { data } = useHighlights();
  const openers = openersFor(data?.starter_categories ?? []);

  return (
    <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center gap-8 px-5 py-12 text-center">
      <div className="flex flex-col items-center gap-5">
        <Mark className="size-12 rounded-2xl" />
        <div className="space-y-2">
          <h1 className="font-display text-3xl font-semibold text-balance">
            What are you looking for?
          </h1>
          <p className="mx-auto max-w-[44ch] text-[15px] leading-relaxed text-muted-foreground">
            Describe it the way you would to a person. Everything shown comes from the
            live catalog, and only you can authorize a payment.
          </p>
        </div>
      </div>

      <div className="flex w-full flex-wrap justify-center gap-2">
        {openers.map((text) => (
          <button
            key={text}
            type="button"
            onClick={() => onPick(text)}
            className="glass rounded-xl px-3.5 py-2 text-sm transition-colors duration-150 hover:border-[color-mix(in_oklch,var(--agent-1),transparent_55%)] focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}
