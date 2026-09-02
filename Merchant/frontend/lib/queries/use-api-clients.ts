"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/lib/use-api";
import type { ApiClient, ApiClientWithKey } from "@/lib/types";

export interface ApiClientPayload {
  name: string;
  client_type?: string;
  scopes?: string[];
}

export function useApiClients() {
  const api = useApi();

  return useQuery({
    queryKey: ["api-clients"],
    queryFn: () => api.get<ApiClient[]>("/api/v1/api-clients"),
  });
}

export function useCreateApiClient() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ApiClientPayload) =>
      api.post<ApiClientWithKey>("/api/v1/api-clients", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-clients"] });
    },
  });
}

export function useRevokeApiClient() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (clientId: string) =>
      api.post<ApiClient>(`/api/v1/api-clients/${clientId}/revoke`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-clients"] });
    },
  });
}
