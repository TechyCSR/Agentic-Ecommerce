"use client";

import { RefreshCw, Sparkles } from "lucide-react";

import { AgentActivity } from "@/components/chat/agent-activity";
import { MarkdownContent } from "@/components/chat/markdown-content";
import { ProductGallery } from "@/components/chat/product-gallery";
import { SuggestionChips } from "@/components/chat/suggestion-chips";
import { Button } from "@/components/ui/button";
import type { ActivityStep, ChatMessage, ProductCard } from "@/lib/types";
import { cn } from "@/lib/utils";

function AssistantAvatar() {
  return (
    <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
      <Sparkles className="size-3.5" />
    </div>
  );
}

export function UserMessage({ content }: { content: string }) {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 flex justify-end duration-300">
      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm whitespace-pre-wrap text-primary-foreground shadow-sm">
        {content}
      </div>
    </div>
  );
}

export function MessageBubble({
  message,
  onBuyNow,
  addingProductId,
  selectedProductIds,
  onSuggestion,
  suggestionsDisabled,
}: {
  message: ChatMessage;
  onBuyNow: (productId: string, variantId: string) => void;
  addingProductId: string | null;
  selectedProductIds?: Set<string>;
  onSuggestion?: (text: string) => void;
  suggestionsDisabled?: boolean;
}) {
  if (message.role === "user") return <UserMessage content={message.content} />;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 flex gap-3 duration-300">
      <AssistantAvatar />
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <MarkdownContent content={message.content} />
        {message.product_cards && message.product_cards.length > 0 && (
          <ProductGallery
            products={message.product_cards}
            onBuyNow={onBuyNow}
            addingProductId={addingProductId}
            selectedProductIds={selectedProductIds}
          />
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

/** The in-flight turn: live activity timeline, streamed text, then cards and
 * suggestions — replaced by the persisted MessageBubble once the stream
 * reports `done` and the session query has refetched. */
export function LiveAssistantBubble({
  activity,
  text,
  cards,
  suggestions,
  onSuggestion,
  onBuyNow,
  addingProductId,
  selectedProductIds,
}: {
  activity: ActivityStep[];
  text: string;
  cards: ProductCard[];
  suggestions: string[];
  onSuggestion: (text: string) => void;
  onBuyNow: (productId: string, variantId: string) => void;
  addingProductId: string | null;
  selectedProductIds?: Set<string>;
}) {
  return (
    <div className="animate-in fade-in flex gap-3 duration-300">
      <AssistantAvatar />
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <AgentActivity steps={activity} />
        {text && (
          <div>
            <MarkdownContent content={text} />
            <span className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-pulse rounded-sm bg-foreground/70" />
          </div>
        )}
        {cards.length > 0 && (
          <ProductGallery
            products={cards}
            onBuyNow={onBuyNow}
            addingProductId={addingProductId}
            selectedProductIds={selectedProductIds}
          />
        )}
        <SuggestionChips suggestions={suggestions} onPick={onSuggestion} />
      </div>
    </div>
  );
}

/** A failed turn, kept inside the conversation so nothing is lost. */
export function ErrorBubble({
  message,
  onRetry,
  isRetrying,
}: {
  message: string;
  onRetry: () => void;
  isRetrying: boolean;
}) {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 flex gap-3 duration-300">
      <AssistantAvatar />
      <div className="flex min-w-0 flex-1 flex-col items-start gap-2">
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-3.5 py-2.5 text-sm">
          <p>I couldn&apos;t complete that right now.</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{message}</p>
        </div>
        <Button variant="outline" size="sm" onClick={onRetry} disabled={isRetrying}>
          <RefreshCw className={cn("size-3.5", isRetrying && "animate-spin")} />
          Try again
        </Button>
      </div>
    </div>
  );
}
