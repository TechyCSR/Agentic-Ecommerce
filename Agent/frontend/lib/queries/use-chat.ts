"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import { API_URL, ApiRequestError } from "@/lib/api";
import { parseSSEStream } from "@/lib/sse";
import { useApi } from "@/lib/use-api";
import type {
  ActivityStep,
  PreparedCheckout,
  Cart,
  CartItem,
  ChatSession,
  ChatSessionDetail,
  ProductCard,
  StreamEvent,
} from "@/lib/types";

export function useSessions() {
  const api = useApi();

  return useQuery({
    queryKey: ["chat-sessions"],
    queryFn: () => api.get<ChatSession[]>("/api/v1/chat/sessions"),
  });
}

export function useSession(sessionId: string | undefined) {
  const api = useApi();

  return useQuery({
    queryKey: ["chat-session", sessionId],
    queryFn: () => api.get<ChatSessionDetail>(`/api/v1/chat/sessions/${sessionId}`),
    enabled: !!sessionId,
  });
}

export function useCreateSession() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.post<ChatSession>("/api/v1/chat/sessions"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}

export function useRenameSession() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, title }: { sessionId: string; title: string }) =>
      api.patch<ChatSession>(`/api/v1/chat/sessions/${sessionId}`, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}

export function useDeleteSession() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) => api.delete(`/api/v1/chat/sessions/${sessionId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}

/** Drops a message and everything after it, so an edited or regenerated
 * turn replaces the old one instead of stacking on top of it. */
export function useTruncateSession() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, messageId }: { sessionId: string; messageId: string }) =>
      api.post<{ removed: number }>(`/api/v1/chat/sessions/${sessionId}/truncate`, {
        message_id: messageId,
      }),
    onSuccess: (_d, variables) => {
      queryClient.invalidateQueries({ queryKey: ["chat-session", variables.sessionId] });
    },
  });
}

export interface StreamState {
  isStreaming: boolean;
  sessionId: string | null;
  /** Optimistic echo of what the buyer just sent, shown before the server round-trip. */
  pendingUserText: string | null;
  activity: ActivityStep[];
  streamedText: string;
  cards: ProductCard[];
  suggestions: string[];
  /** Set when the agent prepared an order — the UI shows a Pay button. */
  pendingCheckout: PreparedCheckout | null;
  error: string | null;
  /** The message that failed, so the UI can offer a one-click retry. */
  failedText: string | null;
}

const IDLE_STREAM_STATE: StreamState = {
  isStreaming: false,
  sessionId: null,
  pendingUserText: null,
  activity: [],
  streamedText: "",
  cards: [],
  suggestions: [],
  pendingCheckout: null,
  error: null,
  failedText: null,
};

const TOOL_LABELS: Record<string, string> = {
  search_catalog: "Searching product catalog",
  get_product_details: "Retrieving product details",
};

const TOOL_DONE_LABELS: Record<string, string> = {
  search_catalog: "Searched product catalog",
  get_product_details: "Retrieved product details",
};

/** Marks every still-running step as finished — the agent has moved on. */
function settleActivity(activity: ActivityStep[]): ActivityStep[] {
  return activity.map((step) => (step.status === "running" ? { ...step, status: "done" } : step));
}

/**
 * Drives one streamed turn over SSE. Not a react-query mutation — the UI
 * needs progressive updates (tool status, token-by-token text) that a
 * single request/response mutation can't express. On `done` it invalidates
 * the session query so the persisted message (source of truth) takes over
 * from the locally-accumulated stream state.
 */
export function useStreamChat() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const [state, setState] = useState<StreamState>(IDLE_STREAM_STATE);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (sessionId: string, text: string): Promise<boolean> => {
      const controller = new AbortController();
      abortRef.current = controller;
      // The buyer's own message renders immediately from this, so the chat
      // reacts on the very next frame instead of after the round-trip.
      setState({ ...IDLE_STREAM_STATE, isStreaming: true, sessionId, pendingUserText: text });

      try {
        const token = await getToken();
        const res = await fetch(`${API_URL}/api/v1/chat/sessions/${sessionId}/messages`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ text }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new ApiRequestError(
            body?.error?.message || "Failed to send message",
            body?.error?.code || "UNKNOWN_ERROR",
            res.status
          );
        }

        let sawError: string | null = null;

        await parseSSEStream<StreamEvent>(
          res,
          (event) => {
            setState((prev) => {
              switch (event.type) {
                case "thinking":
                  return {
                    ...prev,
                    activity: [
                      ...prev.activity,
                      {
                        id: `thinking-${prev.activity.length}`,
                        kind: "thinking",
                        label: "Understanding your request",
                        status: "running",
                      },
                    ],
                  };
                case "tool_start":
                  return {
                    ...prev,
                    activity: [
                      ...settleActivity(prev.activity),
                      {
                        id: `${event.tool}-${prev.activity.length}`,
                        kind: "tool",
                        tool: event.tool,
                        label: event.label || TOOL_LABELS[event.tool] || "Working",
                        status: "running",
                      },
                    ],
                  };
                case "tool_end": {
                  const activity = [...prev.activity];
                  // Attach the result to the matching running step rather
                  // than assuming it's the last one — a round can start
                  // several tool calls before any of them finish.
                  const idx = activity.findLastIndex(
                    (s) => s.tool === event.tool && s.status === "running"
                  );
                  if (idx !== -1) {
                    const count = event.result_count;
                    activity[idx] = {
                      ...activity[idx],
                      status: event.error ? "error" : "done",
                      label: TOOL_DONE_LABELS[event.tool] || activity[idx].label,
                      args: event.args,
                      resultCount: count,
                      detail: event.error
                        ? "Catalog unavailable"
                        : event.tool === "search_catalog"
                          ? `Found ${count ?? 0} product${count === 1 ? "" : "s"}`
                          : event.product_name || undefined,
                    };
                  }
                  return { ...prev, activity };
                }
                case "token":
                  return {
                    ...prev,
                    activity: settleActivity(prev.activity),
                    streamedText: prev.streamedText + event.delta,
                  };
                case "retract":
                  // Text streamed before a tool call isn't grounded in any
                  // result yet, so it never stands as the answer.
                  return { ...prev, streamedText: "" };
                case "product_cards":
                  return { ...prev, cards: event.cards };
                case "checkout_ready":
                  return { ...prev, pendingCheckout: event.order };
                case "suggestions":
                  return { ...prev, suggestions: event.items };
                case "done":
                  // Keep isStreaming true (and the live bubble showing its
                  // final text/cards) until the invalidated session query
                  // has actually refetched below — otherwise there's a gap
                  // where neither the live bubble nor the persisted
                  // message is on screen.
                  return { ...prev, activity: settleActivity(prev.activity) };
                case "error":
                  sawError = event.message;
                  return {
                    ...prev,
                    isStreaming: false,
                    activity: settleActivity(prev.activity),
                    error: event.message,
                    failedText: text,
                  };
                default:
                  return prev;
              }
            });
          },
          controller.signal
        );

        // Awaited so the persisted message is already in the query cache
        // by the time we flip isStreaming off — page.tsx swaps the live
        // bubble for the real MessageBubble with no gap between them.
        await queryClient.invalidateQueries({ queryKey: ["chat-session", sessionId] });
        queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
        // The agent can change the cart, addresses and orders through its own
        // tools, so the panels that show them must refresh — otherwise the
        // cart badge stays stale after "add it to my cart".
        queryClient.invalidateQueries({ queryKey: ["chat-cart"] });
        queryClient.invalidateQueries({ queryKey: ["orders"] });
        queryClient.invalidateQueries({ queryKey: ["addresses"] });

        // pendingUserText clears only here: the refetched session now
        // contains the real persisted user message, so dropping the
        // optimistic echo can't leave a gap where neither is shown.
        setState((prev) => ({ ...prev, isStreaming: false, pendingUserText: null }));
        return !sawError;
      } catch (err) {
        if (controller.signal.aborted) {
          setState((prev) => ({ ...prev, isStreaming: false, pendingUserText: null }));
          return false;
        }
        const message = err instanceof Error ? err.message : "Failed to send message";
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          activity: settleActivity(prev.activity),
          error: message,
          failedText: text,
        }));
        return false;
      }
    },
    [getToken, queryClient]
  );

  const stop = useCallback(() => {
    // Client-side only: stops rendering further events. The backend turn
    // already in flight keeps running to completion server-side (no
    // cancellation endpoint exists) — a known, scoped-out limitation.
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => setState(IDLE_STREAM_STATE), []);

  return { state, send, stop, reset };
}

export function useCart(sessionId: string | undefined) {
  const api = useApi();

  return useQuery({
    queryKey: ["chat-cart", sessionId],
    queryFn: () => api.get<Cart>(`/api/v1/chat/sessions/${sessionId}/selection`),
    enabled: !!sessionId,
  });
}

export function useAddToCart() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sessionId,
      productId,
      variantId,
      quantity = 1,
    }: {
      sessionId: string;
      productId: string;
      variantId: string;
      quantity?: number;
    }) =>
      api.post<CartItem>(`/api/v1/chat/sessions/${sessionId}/select`, {
        product_id: productId,
        variant_id: variantId,
        quantity,
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["chat-cart", variables.sessionId] });
    },
  });
}

export function useUpdateCartItem() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sessionId,
      itemId,
      quantity,
    }: {
      sessionId: string;
      itemId: string;
      quantity: number;
    }) =>
      api.patch<CartItem>(`/api/v1/chat/sessions/${sessionId}/select/${itemId}`, { quantity }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["chat-cart", variables.sessionId] });
    },
  });
}

export function useRemoveCartItem() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, itemId }: { sessionId: string; itemId: string }) =>
      api.delete(`/api/v1/chat/sessions/${sessionId}/select/${itemId}`),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["chat-cart", variables.sessionId] });
    },
  });
}
