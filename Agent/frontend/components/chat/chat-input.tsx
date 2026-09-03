"use client";

import { Send, Square } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function ChatInput({
  onSend,
  disabled,
  isStreaming,
  onStop,
}: {
  onSend: (text: string) => Promise<boolean>;
  disabled: boolean;
  isStreaming?: boolean;
  onStop?: () => void;
}) {
  const [value, setValue] = useState("");

  async function handleSend() {
    const text = value.trim();
    if (!text || disabled) return;
    // Only clear the draft once it's actually been sent — on failure the
    // buyer's text stays put instead of silently vanishing.
    const sent = await onSend(text);
    if (sent) setValue("");
  }

  return (
    <div className="border-t bg-background p-3 md:p-4">
      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-3xl border bg-muted/40 p-1.5 pl-4 shadow-sm focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/30">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Ask for a product, a price range, or compare what you've seen..."
          rows={1}
          className="max-h-32 min-h-9 flex-1 resize-none border-0 bg-transparent px-0 py-1.5 shadow-none focus-visible:ring-0 dark:bg-transparent"
        />
        {isStreaming ? (
          <Button size="icon" className="shrink-0 rounded-full" variant="secondary" onClick={onStop}>
            <Square className="size-3.5 fill-current" />
          </Button>
        ) : (
          <Button size="icon" className="shrink-0 rounded-full" onClick={handleSend} disabled={disabled || !value.trim()}>
            <Send className="size-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
