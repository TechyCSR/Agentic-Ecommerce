"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/lib/use-api";
import type { Order, PaymentAuthorization, PaymentRecord, Receipt } from "@/lib/types";

export function useOrders(sessionId?: string, enabled = true) {
  const api = useApi();

  return useQuery({
    queryKey: ["orders", sessionId ?? "all"],
    queryFn: () =>
      api.get<Order[]>(`/api/v1/orders${sessionId ? `?session_id=${sessionId}` : ""}`),
    enabled,
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

/** Validates the cart against the live catalog and returns a backend-priced order. */
export function useCreateCheckout() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) =>
      api.post<Order>(`/api/v1/chat/sessions/${sessionId}/checkout`),
    onSuccess: (_order, sessionId) => {
      queryClient.invalidateQueries({ queryKey: ["orders", sessionId] });
    },
  });
}

/** The explicit "Pay ₹X" step — nothing is charged before this. */
export function useAuthorizePayment() {
  const api = useApi();

  return useMutation({
    mutationFn: ({ orderId, retry }: { orderId: string; retry?: boolean }) =>
      api.post<PaymentAuthorization>(`/api/v1/orders/${orderId}/authorize`, { retry: !!retry }),
  });
}

/** Backend-side signature verification — the only thing that can mark a payment PAID. */
export function useVerifyPayment() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      orderId,
      razorpayOrderId,
      razorpayPaymentId,
      razorpaySignature,
    }: {
      orderId: string;
      razorpayOrderId: string;
      razorpayPaymentId: string;
      razorpaySignature: string;
    }) =>
      api.post<{ order: Order; payment: PaymentRecord }>(`/api/v1/orders/${orderId}/verify`, {
        razorpay_order_id: razorpayOrderId,
        razorpay_payment_id: razorpayPaymentId,
        razorpay_signature: razorpaySignature,
      }),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["order", variables.orderId] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      // The cart is consumed by a confirmed order, so refresh it too.
      queryClient.invalidateQueries({ queryKey: ["chat-cart"] });
      // The backend posts an "order confirmed" message into the session on
      // verification. Without refetching it, that message wouldn't appear
      // until the buyer reloaded or sent another message.
      if (data?.order?.session_id) {
        queryClient.invalidateQueries({
          queryKey: ["chat-session", data.order.session_id],
        });
      }
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}

export function useRecordPaymentFailure() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      orderId,
      razorpayOrderId,
      cancelled,
      reason,
    }: {
      orderId: string;
      razorpayOrderId?: string | null;
      cancelled: boolean;
      reason?: string;
    }) =>
      api.post<{ order: Order; payment: PaymentRecord | null }>(
        `/api/v1/orders/${orderId}/failed`,
        { razorpay_order_id: razorpayOrderId, cancelled, reason }
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["order", variables.orderId] });
    },
  });
}

export function useReceipt(orderId: string | undefined, enabled: boolean) {
  const api = useApi();

  return useQuery({
    queryKey: ["receipt", orderId],
    queryFn: () => api.get<Receipt>(`/api/v1/orders/${orderId}/receipt`),
    enabled: !!orderId && enabled,
  });
}
