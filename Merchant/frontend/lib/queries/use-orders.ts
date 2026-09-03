"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/lib/use-api";
import type {
  ApiSuccess,
  Order,
  OrderStats,
  OrderStatus,
  PaymentWithOrder,
} from "@/lib/types";

export interface OrderFilters {
  status?: string;
  limit?: number;
  offset?: number;
}

function buildQuery(filters: OrderFilters) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.limit) params.set("limit", String(filters.limit));
  if (filters.offset) params.set("offset", String(filters.offset));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function useOrders(filters: OrderFilters) {
  const api = useApi();

  return useQuery({
    queryKey: ["orders", filters],
    queryFn: () =>
      api.getWithMeta<Order[]>(`/api/v1/orders${buildQuery(filters)}`) as Promise<
        ApiSuccess<Order[]>
      >,
  });
}

export function useOrder(orderId: string | undefined) {
  const api = useApi();

  return useQuery({
    queryKey: ["order", orderId],
    queryFn: () => api.get<Order>(`/api/v1/orders/${orderId}`),
    enabled: !!orderId,
  });
}

export function useOrderStats() {
  const api = useApi();

  return useQuery({
    queryKey: ["order-stats"],
    queryFn: () => api.get<OrderStats>("/api/v1/orders/stats"),
  });
}

export function useUpdateFulfillment() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ orderId, status }: { orderId: string; status: OrderStatus }) =>
      api.patch<Order>(`/api/v1/orders/${orderId}/fulfillment`, { status }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["order", variables.orderId] });
      queryClient.invalidateQueries({ queryKey: ["order-stats"] });
    },
  });
}

export interface PaymentFilters {
  limit?: number;
  offset?: number;
}

export function usePayments(filters: PaymentFilters) {
  const api = useApi();

  return useQuery({
    queryKey: ["payments", filters],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters.limit) params.set("limit", String(filters.limit));
      if (filters.offset) params.set("offset", String(filters.offset));
      const qs = params.toString();
      return api.getWithMeta<PaymentWithOrder[]>(
        `/api/v1/payments${qs ? `?${qs}` : ""}`
      ) as Promise<ApiSuccess<PaymentWithOrder[]>>;
    },
  });
}
