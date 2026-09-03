"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { AgentHeader } from "@/components/chat/agent-header";
import { CartDrawer } from "@/components/chat/cart-drawer";
import { AddressDrawer } from "@/components/addresses/address-drawer";
import { OrdersDrawer } from "@/components/orders/orders-drawer";
import { ProfileSync } from "@/components/profile-sync";
import { DeepLinkCheckout } from "@/components/checkout/deep-link-checkout";
import { ChatInput } from "@/components/chat/chat-input";
import { EmptyState } from "@/components/chat/empty-state";
import {
  ErrorBubble,
  LiveAssistantBubble,
  MessageBubble,
  UserMessage,
} from "@/components/chat/message-bubble";
import { MobileSessionHeader, SessionSidebar } from "@/components/chat/session-sidebar";
import {
  useAddToCart,
  useCart,
  useCreateSession,
  useSession,
  useTruncateSession,
  useSessions,
  useStreamChat,
} from "@/lib/queries/use-chat";

export default function ChatPage() {
  const { data: sessions, isLoading: sessionsLoading } = useSessions();
  const createSession = useCreateSession();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [hasAutoSelected, setHasAutoSelected] = useState(false);

  // Default to the most recent session once the list loads, without
  // clobbering a session the user has since picked or created.
  if (!hasAutoSelected && sessions && sessions.length > 0) {
    setHasAutoSelected(true);
    setActiveId(sessions[0].id);
  }

  const { data: session } = useSession(activeId ?? undefined);
  const { data: cart } = useCart(activeId ?? undefined);
  const { state: stream, send, stop } = useStreamChat();
  const truncate = useTruncateSession();
  const addToCart = useAddToCart();

  const [addingProductId, setAddingProductId] = useState<string | null>(null);
  const [draft, setDraft] = useState<{ text: string; nonce: number; fromId: string } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages, stream.streamedText, stream.activity, stream.pendingUserText]);

  // Cards already in the cart get an "Added" state instead of a second lookup.
  const selectedProductIds = useMemo(
    () => new Set((cart?.items ?? []).map((i) => i.product_id)),
    [cart]
  );

  async function handleNewSession() {
    try {
      const created = await createSession.mutateAsync();
      setActiveId(created.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to start a new chat");
    }
  }

  /** Rewinds the conversation to just before `fromId`, so an edited or
   * regenerated turn replaces what followed instead of appending to it. */
  async function rewindTo(fromId: string): Promise<boolean> {
    if (!activeId) return false;
    try {
      await truncate.mutateAsync({ sessionId: activeId, messageId: fromId });
      return true;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't rewind the chat");
      return false;
    }
  }

  async function handleSend(text: string, rewindFromId?: string): Promise<boolean> {
    if (rewindFromId && !(await rewindTo(rewindFromId))) return false;
    // Resolve the session id locally rather than relying on `activeId`
    // state (setActiveId doesn't take effect until the next render, so
    // reading `activeId` right after creating a session here would still
    // see the old, unset value).
    let sessionId = activeId;
    if (!sessionId) {
      try {
        const created = await createSession.mutateAsync();
        setActiveId(created.id);
        sessionId = created.id;
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Failed to start a new chat");
        return false;
      }
    }
    return send(sessionId, text);
  }

  async function handleBuyNow(productId: string, variantId: string) {
    if (!activeId) return;
    setAddingProductId(productId);
    try {
      await addToCart.mutateAsync({ sessionId: activeId, productId, variantId });
      toast.success("Product selected — ready for checkout");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add this product");
    } finally {
      setAddingProductId(null);
    }
  }

  const sidebarProps = {
    sessions: sessions ?? [],
    activeId,
    onSelect: setActiveId,
    onNew: handleNewSession,
    isLoading: sessionsLoading,
    isCreating: createSession.isPending,
  };

  const messages = session?.messages ?? [];
  const lastMessage = messages[messages.length - 1];
  const showPersistedSuggestions =
    !stream.isStreaming &&
    lastMessage?.role === "assistant" &&
    (lastMessage.suggested_replies?.length ?? 0) > 0;

  const cartSlot = (
    <div className="flex items-center gap-2">
      <AddressDrawer />
      <OrdersDrawer />
      {activeId ? <CartDrawer sessionId={activeId} cart={cart} /> : null}
    </div>
  );
  const isThisSession = stream.sessionId === activeId;
  const showEmptyState = !activeId || (messages.length === 0 && !stream.isStreaming && !stream.error);

  return (
    <div className="flex h-dvh w-full overflow-hidden">
      <ProfileSync />
      <DeepLinkCheckout />
      <SessionSidebar {...sidebarProps} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <MobileSessionHeader {...sidebarProps} rightSlot={cartSlot} />
        <div className="hidden md:block">
          <AgentHeader isWorking={stream.isStreaming} rightSlot={cartSlot} />
        </div>

        <div className="flex-1 overflow-y-auto">
          {showEmptyState ? (
            <EmptyState onPick={handleSend} />
          ) : (
            <div className="mx-auto max-w-3xl space-y-6 px-4 py-6 md:px-6">
              {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  onBuyNow={handleBuyNow}
                  addingProductId={addingProductId}
                  selectedProductIds={selectedProductIds}
                  onSuggestion={
                    message.id === lastMessage?.id && showPersistedSuggestions ? handleSend : undefined
                  }
                  suggestionsDisabled={stream.isStreaming}
                  onEdit={
                    message.role === "user"
                      ? () =>
                          setDraft({
                            text: message.content,
                            nonce: Date.now(),
                            fromId: message.id,
                          })
                      : undefined
                  }
                  onRetry={
                    // Replace this reply: drop it and the question that
                    // produced it, then ask again.
                    message.role === "assistant"
                      ? () => {
                          const asked = [...messages]
                            .slice(0, messages.indexOf(message))
                            .reverse()
                            .find((m) => m.role === "user");
                          if (asked) handleSend(asked.content, asked.id);
                        }
                      : undefined
                  }
                />
              ))}

              {/* Optimistic echo — only while the server hasn't persisted it yet. */}
              {isThisSession && stream.pendingUserText && (
                <UserMessage content={stream.pendingUserText} />
              )}

              {isThisSession && stream.isStreaming && (
                <LiveAssistantBubble
                  activity={stream.activity}
                  text={stream.streamedText}
                  cards={stream.cards}
                  suggestions={stream.suggestions}
                  onSuggestion={handleSend}
                  onBuyNow={handleBuyNow}
                  addingProductId={addingProductId}
                  selectedProductIds={selectedProductIds}
                  pendingCheckout={stream.pendingCheckout}
                />
              )}

              {isThisSession && !stream.isStreaming && stream.error && (
                <ErrorBubble
                  message={stream.error}
                  isRetrying={stream.isStreaming}
                  onRetry={() => stream.failedText && handleSend(stream.failedText)}
                />
              )}

              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <ChatInput
          onSend={handleSend}
          isStreaming={stream.isStreaming}
          onStop={stop}
          draft={draft}
        />
      </div>
    </div>
  );
}
