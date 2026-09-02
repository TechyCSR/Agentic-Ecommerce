"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/lib/use-api";
import type { Store } from "@/lib/types";

export interface StorePayload {
  name: string;
  slug?: string;
  description?: string;
  currency?: string;
  country?: string;
}

export function useStores(options?: { enabled?: boolean }) {
  const api = useApi();

  return useQuery({
    queryKey: ["stores"],
    queryFn: () => api.get<Store[]>("/api/v1/stores"),
    enabled: options?.enabled,
  });
}

export function useCreateStore() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: StorePayload) =>
      api.post<Store>("/api/v1/stores", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stores"] });
    },
  });
}

export function useUpdateStore() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      storeId,
      payload,
    }: {
      storeId: string;
      payload: Partial<StorePayload> & { status?: string };
    }) => api.patch<Store>(`/api/v1/stores/${storeId}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stores"] });
    },
  });
}
