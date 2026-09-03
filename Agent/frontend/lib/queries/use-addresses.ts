"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/lib/use-api";
import type { Address, AddressPayload } from "@/lib/types";

export function useAddresses(enabled = true) {
  const api = useApi();

  return useQuery({
    queryKey: ["addresses"],
    queryFn: () => api.get<Address[]>("/api/v1/addresses"),
    enabled,
  });
}

export function useCreateAddress() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: AddressPayload) => api.post<Address>("/api/v1/addresses", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["addresses"] }),
  });
}

export function useSetDefaultAddress() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (addressId: string) =>
      api.post<Address>(`/api/v1/addresses/${addressId}/default`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["addresses"] }),
  });
}

export function useDeleteAddress() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (addressId: string) => api.delete(`/api/v1/addresses/${addressId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["addresses"] }),
  });
}
