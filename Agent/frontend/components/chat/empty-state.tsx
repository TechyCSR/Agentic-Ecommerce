"use client";

import { Headphones, Keyboard, Laptop, Sparkles, Watch } from "lucide-react";

const STARTERS: { icon: React.ComponentType<{ className?: string }>; text: string }[] = [
  { icon: Headphones, text: "Find headphones under ₹5,000" },
  { icon: Keyboard, text: "I need a keyboard for programming" },
  { icon: Watch, text: "Show me wireless earbuds" },
  { icon: Laptop, text: "Help me choose a laptop" },
];

export function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center gap-6 px-4 py-10 text-center">
      <div className="animate-in fade-in zoom-in-95 flex size-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg duration-500">
        <Sparkles className="size-7" />
      </div>

      <div className="animate-in fade-in slide-in-from-bottom-2 space-y-1.5 duration-500">
        <h1 className="text-2xl font-semibold tracking-tight">Shopping Agent</h1>
        <p className="text-sm text-muted-foreground">
          Find exactly what you&apos;re looking for — I search the real catalog, compare
          options, and never make up a product.
        </p>
      </div>

      <div className="w-full space-y-2">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          Try asking
        </p>
        <div className="grid gap-2 sm:grid-cols-2">
          {STARTERS.map(({ icon: Icon, text }, i) => (
            <button
              key={text}
              type="button"
              onClick={() => onPick(text)}
              style={{ animationDelay: `${i * 60}ms` }}
              className="animate-in fade-in slide-in-from-bottom-2 group flex items-center gap-2.5 rounded-xl border bg-card/60 px-3.5 py-3 text-left text-sm backdrop-blur-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-foreground/20 hover:bg-card hover:shadow-md"
            >
              <Icon className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-foreground" />
              <span className="leading-snug">{text}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
