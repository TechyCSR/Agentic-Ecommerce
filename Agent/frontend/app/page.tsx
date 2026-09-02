"use client";

import { Loader2, MessageSquarePlus, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ChatInput } from "@/components/chat/chat-input";
import { MessageBubble } from "@/components/chat/message-bubble";
import { SelectionBanner } from "@/components/chat/selection-banner";
import { MobileSessionHeader, SessionSidebar } from "@/components/chat/session-sidebar";
import { Button } from "@/components/ui/button";
import {
  useCreateSession,
  useSelectProduct,
  useSelection,
  useSendMessage,
  useSession,
  useSessions,
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

  const { data: session, isLoading: sessionLoading } = useSession(activeId ?? undefined);
  const { data: selection } = useSelection(activeId ?? undefined);
  const sendMessage = useSendMessage();
  const selectProduct = useSelectProduct();

  const [selectingProductId, setSelectingProductId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages, sendMessage.isPending]);

  async function handleNewSession() {
    try {
      const created = await createSession.mutateAsync();
      setActiveId(created.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to start a new chat");
    }
  }

  async function handleSend(text: string): Promise<boolean> {
    try {
      // Resolve the session id locally rather than relying on `activeId`
      // state (setActiveId doesn't take effect until the next render, so
      // reading `activeId` right after creating a session here would still
      // see the old, unset value).
      let sessionId = activeId;
      if (!sessionId) {
        const created = await createSession.mutateAsync();
        setActiveId(created.id);
        sessionId = created.id;
      }
      await sendMessage.mutateAsync({ sessionId, text });
      return true;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to send message");
      return false;
    }
  }

  async function handleBuyNow(productId: string, variantId: string) {
    if (!activeId) return;
    setSelectingProductId(productId);
    try {
      await selectProduct.mutateAsync({ sessionId: activeId, productId, variantId });
      toast.success("Added to checkout — ready when you are.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to select this product");
    } finally {
      setSelectingProductId(null);
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

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <SessionSidebar {...sidebarProps} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <MobileSessionHeader {...sidebarProps} />
        {selection && <SelectionBanner selection={selection} />}

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
              <Button onClick={handleNewSession} disabled={createSession.isPending}>
                {createSession.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <MessageSquarePlus className="size-4" />
                )}
                Start chatting
              </Button>
            </div>
          ) : sessionLoading ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="size-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-6">
              {(session?.messages ?? []).length === 0 && (
                <p className="text-center text-sm text-muted-foreground">
                  Try: &quot;I need a mechanical keyboard under ₹5,000&quot;
                </p>
              )}
              {session?.messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  onBuyNow={handleBuyNow}
                  selectingProductId={selectingProductId}
                />
              ))}
              {sendMessage.isPending && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-3.5 animate-spin" /> Thinking...
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="mx-auto w-full max-w-3xl">
          <ChatInput onSend={handleSend} disabled={sendMessage.isPending} />
        </div>
      </div>
    </div>
  );
}
