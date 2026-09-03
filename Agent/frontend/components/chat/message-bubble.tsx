"use client";

import { Bot } from "lucide-react";

import { MarkdownContent } from "@/components/chat/markdown-content";
import { ProductCardView } from "@/components/chat/product-card";
import { SuggestionChips } from "@/components/chat/suggestion-chips";
import { ToolActivity } from "@/components/chat/tool-activity";
import type { ToolStatus } from "@/lib/queries/use-chat";
import type { ChatMessage, ProductCard } from "@/lib/types";
import { cn } from "@/lib/utils";

function AssistantAvatar() {
  return (
    <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
      <Bot className="size-4" />
    </div>
  );
}

export function MessageBubble({
  message,
  onBuyNow,
  addingProductId,
  onSuggestion,
  suggestionsDisabled,
}: {
  message: ChatMessage;
  onBuyNow: (productId: string, variantId: string) => void;
  addingProductId: string | null;
  onSuggestion?: (text: string) => void;
  suggestionsDisabled?: boolean;
}) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl bg-primary px-4 py-2.5 text-sm whitespace-pre-wrap text-primary-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <AssistantAvatar />
      <div className="flex min-w-0 max-w-[90%] flex-1 flex-col gap-3">
        <MarkdownContent content={message.content} />
        {message.product_cards && message.product_cards.length > 0 && (
          <div className="flex w-full gap-3 overflow-x-auto pb-2">
            {message.product_cards.map((product) => (
              <ProductCardView
                key={product.product_id}
                product={product}
                onBuyNow={onBuyNow}
                isAdding={addingProductId === product.product_id}
              />
            ))}
          </div>
        )}
        {onSuggestion && message.suggested_replies && message.suggested_replies.length > 0 && (
          <SuggestionChips
            suggestions={message.suggested_replies}
            onPick={onSuggestion}
            disabled={suggestionsDisabled}
          />
        )}
      </div>
    </div>
  );
}

/** The in-flight turn: tool activity, streamed text with a typing cursor,
 * cards/suggestions as they arrive — replaced by the persisted MessageBubble
 * once the stream reports `done` and the session query re-fetches. */
export function LiveAssistantBubble({
  status,
  text,
  cards,
  suggestions,
  onSuggestion,
  onBuyNow,
  addingProductId,
}: {
  status: ToolStatus | null;
  text: string;
  cards: ProductCard[];
  suggestions: string[];
  onSuggestion: (text: string) => void;
  onBuyNow: (productId: string, variantId: string) => void;
  addingProductId: string | null;
}) {
  return (
    <div className="flex gap-3">
      <AssistantAvatar />
      <div className="flex min-w-0 max-w-[90%] flex-1 flex-col gap-3">
        {status && <ToolActivity status={status} />}
        {text && (
          <div className="text-sm">
            <MarkdownContent content={text} />
            <span className={cn("ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-pulse bg-foreground/70")} />
          </div>
        )}
        {cards.length > 0 && (
          <div className="flex w-full gap-3 overflow-x-auto pb-2">
            {cards.map((product) => (
              <ProductCardView
                key={product.product_id}
                product={product}
                onBuyNow={onBuyNow}
                isAdding={addingProductId === product.product_id}
              />
            ))}
          </div>
        )}
        <SuggestionChips suggestions={suggestions} onPick={onSuggestion} />
      </div>
    </div>
  );
}
