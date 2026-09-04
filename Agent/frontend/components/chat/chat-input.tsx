"use client";

import { ArrowUp, Square } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function ChatInput({
  onSend,
  isStreaming,
  onStop,
}: {
  onSend: (text: string) => Promise<boolean>;
  isStreaming?: boolean;
  onStop?: () => void;
}) {
  // Editing a past message happens in place, in the conversation — the
  // composer only ever holds a brand-new question.
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  async function handleSend() {
    const text = value.trim();
    // Only the empty case blocks sending — the composer stays live while the
    // agent works so the buyer can keep typing their next question.
    if (!text) return;
    setValue("");
    const sent = await onSend(text);
    // Restore the draft rather than silently losing it if the send failed.
    if (!sent) setValue((current) => current || text);
  }

  return (
    <div className="bg-gradient-to-t from-background via-background to-transparent px-3 pb-3 md:px-6 md:pb-4">
      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-[1.75rem] border bg-card/80 p-1.5 pl-4 shadow-lg backdrop-blur-md transition-all duration-200 focus-within:border-foreground/25 focus-within:shadow-xl">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Ask for a product, a price range, or compare what you've seen…"
          rows={1}
          className="max-h-40 min-h-9 flex-1 resize-none border-0 bg-transparent px-0 py-2 shadow-none focus-visible:ring-0 dark:bg-transparent"
        />
        {isStreaming ? (
          <Button
            size="icon"
            variant="secondary"
            className="size-9 shrink-0 rounded-full"
            onClick={onStop}
            aria-label="Stop generating"
          >
            <Square className="size-3.5 fill-current" />
          </Button>
        ) : (
          <Button
            size="icon"
            className="size-9 shrink-0 rounded-full transition-transform active:scale-95"
            onClick={handleSend}
            disabled={!value.trim()}
            aria-label="Send message"
          >
            <ArrowUp className="size-4" />
          </Button>
        )}
      </div>
      <p className="mt-2 text-center text-[11px] text-muted-foreground">
        Product details come from the live catalog — the agent never invents one.
      </p>
    </div>
  );
}
