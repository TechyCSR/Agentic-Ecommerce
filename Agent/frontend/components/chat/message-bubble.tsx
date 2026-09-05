"use client";

import { Check, RefreshCw, Sparkles, X } from "lucide-react";
import { useRef, useState } from "react";

import { AgentActivity } from "@/components/chat/agent-activity";
import { MarkdownContent } from "@/components/chat/markdown-content";
import { ProductGallery } from "@/components/chat/product-gallery";
import { SuggestionChips } from "@/components/chat/suggestion-chips";
import { MessageActions } from "@/components/chat/message-actions";
import { PayPrompt } from "@/components/checkout/pay-prompt";
import { Button } from "@/components/ui/button";
import type { ActivityStep, ChatMessage, PreparedCheckout, ProductCard } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Filler the suggestion builder falls back to when it has nothing useful.
 * On its own it's just clutter — and tapping it returns the same thing. */
const GENERIC_SUGGESTIONS = new Set([
  "search something else",
  "show more options",
  "refine my search",
]);

function usefulSuggestions(suggestions: string[] | null | undefined): string[] {
  const kept = (suggestions ?? []).filter(
    (s) => !GENERIC_SUGGESTIONS.has(s.trim().toLowerCase())
  );
  return kept.length >= 2 ? kept : [];
}

function AssistantAvatar() {
  return (
    <div className="flex size-6 shrink-0 items-center justify-center rounded-md bg-[linear-gradient(135deg,var(--agent-1),var(--agent-2))] text-white">
      <Sparkles className="size-3" />
    </div>
  );
}

export function UserMessage({
  content,
  createdAt,
  onEdit,
  isEditing,
  onSaveEdit,
  onCancelEdit,
}: {
  content: string;
  createdAt?: string;
  onEdit?: () => void;
  isEditing?: boolean;
  onSaveEdit?: (text: string) => void;
  onCancelEdit?: () => void;
}) {
  if (isEditing && onSaveEdit && onCancelEdit) {
    return <UserMessageEditor content={content} onSave={onSaveEdit} onCancel={onCancelEdit} />;
  }

  return (
    <div className="group animate-in fade-in slide-in-from-bottom-1 flex flex-col items-end gap-1 duration-200">
      <div className="max-w-[85%] rounded-lg rounded-br-sm bg-primary px-3.5 py-2 text-sm whitespace-pre-wrap text-primary-foreground">
        {content}
      </div>
      {createdAt && (
        <MessageActions
          createdAt={createdAt}
          content={content}
          align="right"
          onEdit={onEdit}
        />
      )}
    </div>
  );
}

/**
 * Edits a question where it sits, rather than sending the buyer back to the
 * composer at the bottom of the page. The message keeps its place in the
 * conversation, so it stays obvious which turn is being rewritten.
 */
function UserMessageEditor({
  content,
  onSave,
  onCancel,
}: {
  content: string;
  onSave: (text: string) => void;
  onCancel: () => void;
}) {
  const [value, setValue] = useState(content);
  const ref = useRef<HTMLTextAreaElement>(null);
  const unchanged = value.trim() === content.trim();

  function submit() {
    const text = value.trim();
    if (!text || unchanged) return onCancel();
    onSave(text);
  }

  /** Grows with the text so a long question isn't edited through a slot. */
  function fit(el: HTMLTextAreaElement | null) {
    if (!el) return;
    ref.current = el;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }

  return (
    <div className="animate-in fade-in flex flex-col items-end gap-2 duration-200">
      <div className="w-full max-w-[85%] rounded-lg rounded-br-sm border border-primary/40 bg-primary/[0.06] p-2">
        <textarea
          ref={fit}
          autoFocus
          value={value}
          rows={1}
          aria-label="Edit your message"
          className="max-h-60 w-full resize-none bg-transparent px-2 py-1 text-sm outline-none"
          onChange={(e) => {
            setValue(e.target.value);
            fit(e.currentTarget);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            } else if (e.key === "Escape") {
              e.preventDefault();
              onCancel();
            }
          }}
        />
        <div className="flex items-center justify-between gap-2 px-1 pt-1">
          <span className="text-[11px] text-muted-foreground">
            Everything after this is replaced
          </span>
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" onClick={onCancel}>
              <X className="size-3.5" />
              Cancel
            </Button>
            <Button size="sm" disabled={!value.trim() || unchanged} onClick={submit}>
              <Check className="size-3.5" />
              Send
            </Button>
          </div>
        </div>
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
  onRetry,
  onEdit,
  isEditing,
  onSaveEdit,
  onCancelEdit,
}: {
  message: ChatMessage;
  onBuyNow: (productId: string, variantId: string) => void;
  addingProductId: string | null;
  selectedProductIds?: Set<string>;
  onSuggestion?: (text: string) => void;
  suggestionsDisabled?: boolean;
  onRetry?: () => void;
  onEdit?: () => void;
  isEditing?: boolean;
  onSaveEdit?: (text: string) => void;
  onCancelEdit?: () => void;
}) {
  if (message.role === "user") {
    return (
      <UserMessage
        content={message.content}
        createdAt={message.created_at}
        onEdit={onEdit}
        isEditing={isEditing}
        onSaveEdit={onSaveEdit}
        onCancelEdit={onCancelEdit}
      />
    );
  }

  return (
    <div className="group animate-in fade-in slide-in-from-bottom-1 flex gap-3 duration-200">
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
        {message.prepared_checkout && <PayPrompt checkout={message.prepared_checkout} />}
        {onSuggestion && usefulSuggestions(message.suggested_replies).length > 0 && (
          <SuggestionChips
            suggestions={usefulSuggestions(message.suggested_replies)}
            onPick={onSuggestion}
            disabled={suggestionsDisabled}
          />
        )}
        <MessageActions
          createdAt={message.created_at}
          content={message.content}
          onRetry={onRetry}
          activity={message.tool_activity}
        />
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
  pendingCheckout,
}: {
  activity: ActivityStep[];
  text: string;
  cards: ProductCard[];
  suggestions: string[];
  pendingCheckout?: PreparedCheckout | null;
  onSuggestion: (text: string) => void;
  onBuyNow: (productId: string, variantId: string) => void;
  addingProductId: string | null;
  selectedProductIds?: Set<string>;
}) {
  return (
    <div className="animate-in fade-in flex gap-3 duration-200">
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
        {pendingCheckout && <PayPrompt checkout={pendingCheckout} />}
        <SuggestionChips suggestions={usefulSuggestions(suggestions)} onPick={onSuggestion} />
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
    <div className="animate-in fade-in slide-in-from-bottom-1 flex gap-3 duration-200">
      <AssistantAvatar />
      <div className="flex min-w-0 flex-1 flex-col items-start gap-2">
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3.5 py-2.5 text-sm">
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
