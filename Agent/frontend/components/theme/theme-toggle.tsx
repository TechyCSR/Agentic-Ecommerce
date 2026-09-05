"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { cn } from "@/lib/utils";

/**
 * Light/dark switch.
 *
 * Both icons are always rendered and CSS picks which one shows, keyed off
 * the `dark` class next-themes puts on the document. The usual approach —
 * a `mounted` flag set in an effect — exists to dodge a hydration mismatch,
 * but the server genuinely doesn't know the answer, so letting CSS decide
 * after the class lands is both correct and free of an effect.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <button
      type="button"
      aria-label="Toggle light or dark theme"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      className={cn(
        "relative grid size-9 place-items-center rounded-lg border border-border/70 text-muted-foreground",
        "transition-colors duration-150 hover:text-foreground",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        className
      )}
    >
      <Moon className="size-4 dark:hidden" />
      <Sun className="hidden size-4 dark:block" />
    </button>
  );
}
