"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/lib/use-api";
import type {
  ChatMessage,
  ChatSession,
  ChatSessionDetail,
  Selection,
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

export function useSendMessage() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, text }: { sessionId: string; text: string }) =>
      api.post<ChatMessage>(`/api/v1/chat/sessions/${sessionId}/messages`, { text }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["chat-session", variables.sessionId] });
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}

export function useSelection(sessionId: string | undefined) {
  const api = useApi();

  return useQuery({
    queryKey: ["chat-selection", sessionId],
    queryFn: () => api.get<Selection | null>(`/api/v1/chat/sessions/${sessionId}/selection`),
    enabled: !!sessionId,
  });
}

export function useSelectProduct() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sessionId,
      productId,
      variantId,
    }: {
      sessionId: string;
      productId: string;
      variantId: string;
    }) =>
      api.post<Selection>(`/api/v1/chat/sessions/${sessionId}/select`, {
        product_id: productId,
        variant_id: variantId,
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["chat-selection", variables.sessionId] });
    },
  });
}
