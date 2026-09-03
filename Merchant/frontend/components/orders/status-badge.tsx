"use client";

import { Badge } from "@/components/ui/badge";
import type { OrderStatus, PaymentStatus } from "@/lib/types";

type Variant = "default" | "secondary" | "destructive" | "outline";

const orderVariant: Record<OrderStatus, Variant> = {
  DRAFT: "outline",
  PENDING_AUTHORIZATION: "secondary",
  AUTHORIZED: "secondary",
  PAYMENT_PENDING: "secondary",
  PAID: "default",
  PAYMENT_FAILED: "destructive",
  CANCELLED: "destructive",
  CONFIRMED: "default",
  PACKED: "secondary",
  SHIPPED: "secondary",
  DELIVERED: "default",
};

const paymentVariant: Record<PaymentStatus, Variant> = {
  CREATED: "outline",
  PENDING: "secondary",
  AUTHORIZED: "secondary",
  CAPTURED: "default",
  FAILED: "destructive",
  CANCELLED: "destructive",
  REFUNDED: "outline",
};

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return <Badge variant={orderVariant[status] ?? "outline"}>{status.replace(/_/g, " ")}</Badge>;
}

export function PaymentStatusBadge({ status }: { status: PaymentStatus | null }) {
  if (!status) return <span className="text-muted-foreground">—</span>;
  return <Badge variant={paymentVariant[status] ?? "outline"}>{status}</Badge>;
}
