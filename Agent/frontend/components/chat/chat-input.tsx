"use client";

import { Loader2, Send } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => Promise<boolean>;
  disabled: boolean;
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
    <div className="flex items-end gap-2 border-t bg-background p-4">
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
        className="max-h-32 min-h-10 flex-1 resize-none"
      />
      <Button size="icon" onClick={handleSend} disabled={disabled || !value.trim()}>
        {disabled ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
      </Button>
    </div>
  );
}
