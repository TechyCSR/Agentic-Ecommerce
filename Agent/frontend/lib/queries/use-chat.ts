"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import { API_URL, ApiRequestError } from "@/lib/api";
import { parseSSEStream } from "@/lib/sse";
import { useApi } from "@/lib/use-api";
import type {
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

export interface ToolStatus {
  tool: string;
  label: string;
  phase: "running" | "done";
}

export interface StreamState {
  isStreaming: boolean;
  sessionId: string | null;
  status: ToolStatus | null;
  streamedText: string;
  cards: ProductCard[];
  suggestions: string[];
  error: string | null;
}

const IDLE_STREAM_STATE: StreamState = {
  isStreaming: false,
  sessionId: null,
  status: null,
  streamedText: "",
  cards: [],
  suggestions: [],
  error: null,
};

const TOOL_LABELS: Record<string, string> = {
  search_catalog: "Searching the catalog…",
  get_product_details: "Checking product details…",
};

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
      setState({ ...IDLE_STREAM_STATE, isStreaming: true, sessionId });

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
                case "tool_start":
                  return {
                    ...prev,
                    status: {
                      tool: event.tool,
                      label: event.label || TOOL_LABELS[event.tool] || "Working…",
                      phase: "running",
                    },
                  };
                case "tool_end":
                  return { ...prev, status: prev.status ? { ...prev.status, phase: "done" } : null };
                case "token":
                  return { ...prev, status: null, streamedText: prev.streamedText + event.delta };
                case "product_cards":
                  return { ...prev, cards: event.cards };
                case "suggestions":
                  return { ...prev, suggestions: event.items };
                case "done":
                  // Keep isStreaming true (and the live bubble showing its
                  // final text/cards) until the invalidated session query
                  // has actually refetched below — otherwise there's a gap
                  // where neither the live bubble nor the persisted
                  // message is on screen.
                  return { ...prev, status: null };
                case "error":
                  sawError = event.message;
                  return { ...prev, isStreaming: false, status: null, error: event.message };
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

        setState((prev) => ({ ...prev, isStreaming: false }));
        return !sawError;
      } catch (err) {
        if (controller.signal.aborted) {
          setState((prev) => ({ ...prev, isStreaming: false }));
          return false;
        }
        const message = err instanceof Error ? err.message : "Failed to send message";
        setState((prev) => ({ ...prev, isStreaming: false, error: message }));
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
