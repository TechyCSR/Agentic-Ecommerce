"use client";

export function SuggestionChips({
  suggestions,
  onPick,
  disabled,
}: {
  suggestions: string[];
  onPick: (text: string) => void;
  disabled?: boolean;
}) {
  if (suggestions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {suggestions.map((s) => (
        <button
          key={s}
          type="button"
          disabled={disabled}
          onClick={() => onPick(s)}
          className="rounded-md border bg-background px-2.5 py-1 text-xs text-muted-foreground transition-colors duration-100 hover:border-foreground/25 hover:text-foreground disabled:pointer-events-none disabled:opacity-50"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
