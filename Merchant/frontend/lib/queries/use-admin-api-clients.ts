"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { ApiClientInstance } from "@/lib/api";
import type { ApiClient, ApiClientWithKey } from "@/lib/types";

export interface AdminApiClientPayload {
  name: string;
  client_type?: string;
  scopes?: string[];
}

export function useAdminApiClients(api: ApiClientInstance) {
  return useQuery({
    queryKey: ["admin-api-clients"],
    queryFn: () => api.get<ApiClient[]>("/api/v1/admin/api-clients"),
  });
}

export function useCreateAdminApiClient(api: ApiClientInstance) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: AdminApiClientPayload) =>
      api.post<ApiClientWithKey>("/api/v1/admin/api-clients", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-api-clients"] });
    },
  });
}

export function useRevokeAdminApiClient(api: ApiClientInstance) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (clientId: string) =>
      api.post<ApiClient>(`/api/v1/admin/api-clients/${clientId}/revoke`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-api-clients"] });
    },
  });
}
