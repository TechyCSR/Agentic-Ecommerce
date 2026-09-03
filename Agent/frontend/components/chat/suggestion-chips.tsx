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
          className="rounded-full border bg-background px-3 py-1.5 text-xs text-foreground transition-colors hover:bg-muted disabled:pointer-events-none disabled:opacity-50"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
