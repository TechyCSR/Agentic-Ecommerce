"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/lib/use-api";
import type { Merchant } from "@/lib/types";

export interface MerchantPayload {
  business_name: string;
  legal_name?: string;
  description?: string;
  email?: string;
  phone?: string;
  website_url?: string;
}

export function useCreateMerchant() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: MerchantPayload) =>
      api.post<Merchant>("/api/v1/merchants", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["current-user"] });
    },
  });
}

export function useUpdateMerchant() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: Partial<MerchantPayload> & { status?: string }) =>
      api.patch<Merchant>("/api/v1/merchants/me", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["current-user"] });
    },
  });
}
