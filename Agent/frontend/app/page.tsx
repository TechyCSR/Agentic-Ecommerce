"use client";

import { MessageSquarePlus, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { CartDrawer } from "@/components/chat/cart-drawer";
import { ChatInput } from "@/components/chat/chat-input";
import { LiveAssistantBubble, MessageBubble } from "@/components/chat/message-bubble";
import { MobileSessionHeader, SessionSidebar } from "@/components/chat/session-sidebar";
import { SuggestionChips } from "@/components/chat/suggestion-chips";
import { Button } from "@/components/ui/button";
import {
  useAddToCart,
  useCart,
  useCreateSession,
  useSession,
  useSessions,
  useStreamChat,
} from "@/lib/queries/use-chat";

const STARTER_SUGGESTIONS = [
  "Show me trending products",
  "I need a mechanical keyboard under ₹5,000",
  "Search by category",
];

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

  const { data: session, isLoading: sessionLoading } = useSession(activeId ?? undefined);
  const { data: cart } = useCart(activeId ?? undefined);
  const { state: stream, send, stop } = useStreamChat();
  const addToCart = useAddToCart();

  const [addingProductId, setAddingProductId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages, stream.streamedText, stream.status]);

  async function handleNewSession() {
    try {
      const created = await createSession.mutateAsync();
      setActiveId(created.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to start a new chat");
    }
  }

  async function handleSend(text: string): Promise<boolean> {
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
    const ok = await send(sessionId, text);
    if (!ok && stream.error) toast.error(stream.error);
    return ok;
  }

  async function handleBuyNow(productId: string, variantId: string) {
    if (!activeId) return;
    setAddingProductId(productId);
    try {
      await addToCart.mutateAsync({ sessionId: activeId, productId, variantId });
      toast.success("Added to cart");
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

  const lastMessage = session?.messages[session.messages.length - 1];
  const showPersistedSuggestions =
    !stream.isStreaming && lastMessage?.role === "assistant" && (lastMessage.suggested_replies?.length ?? 0) > 0;

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <SessionSidebar {...sidebarProps} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <MobileSessionHeader {...sidebarProps} rightSlot={activeId ? <CartDrawer sessionId={activeId} cart={cart} /> : null} />

        <div className="hidden items-center justify-end border-b px-6 py-2 md:flex">
          {activeId && <CartDrawer sessionId={activeId} cart={cart} />}
        </div>

        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          {!activeId ? (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
              <Sparkles className="size-10 text-primary" />
              <div>
                <h1 className="text-xl font-semibold tracking-tight">
                  What are you shopping for?
                </h1>
                <p className="mt-1 text-muted-foreground">
                  Describe what you need — I&apos;ll search the real catalog for you.
                </p>
              </div>
              <SuggestionChips suggestions={STARTER_SUGGESTIONS} onPick={handleSend} />
              <Button variant="outline" onClick={handleNewSession} disabled={createSession.isPending}>
                <MessageSquarePlus className="size-4" />
                Start a blank chat
              </Button>
            </div>
          ) : sessionLoading && !session ? (
            <div className="flex h-full items-center justify-center">
              <Sparkles className="size-6 animate-pulse text-muted-foreground" />
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-6">
              {(session?.messages ?? []).length === 0 && !stream.isStreaming && (
                <p className="text-center text-sm text-muted-foreground">
                  Try: &quot;I need a mechanical keyboard under ₹5,000&quot;
                </p>
              )}
              {session?.messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  onBuyNow={handleBuyNow}
                  addingProductId={addingProductId}
                  onSuggestion={message.id === lastMessage?.id && showPersistedSuggestions ? handleSend : undefined}
                  suggestionsDisabled={stream.isStreaming}
                />
              ))}
              {stream.isStreaming && stream.sessionId === activeId && (
                <LiveAssistantBubble
                  status={stream.status}
                  text={stream.streamedText}
                  cards={stream.cards}
                  suggestions={stream.suggestions}
                  onSuggestion={handleSend}
                  onBuyNow={handleBuyNow}
                  addingProductId={addingProductId}
                />
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="w-full">
          <ChatInput
            onSend={handleSend}
            disabled={stream.isStreaming}
            isStreaming={stream.isStreaming}
            onStop={stop}
          />
        </div>
      </div>
    </div>
  );
}
