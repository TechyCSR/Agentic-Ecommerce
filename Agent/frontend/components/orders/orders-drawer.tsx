"use client";

import { CheckCircle2, Clock, Package, Receipt, XCircle } from "lucide-react";
import { useState } from "react";

import { ProductImage } from "@/components/chat/product-image";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { formatMoney } from "@/lib/money";
import { useOrders } from "@/lib/queries/use-orders";
import type { Order, PaymentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

function paymentTone(status: PaymentStatus | null) {
  if (status === "PAID") return { icon: CheckCircle2, cls: "text-emerald-600 dark:text-emerald-400" };
  if (status === "FAILED" || status === "CANCELLED") return { icon: XCircle, cls: "text-destructive" };
  return { icon: Clock, cls: "text-muted-foreground" };
}

function OrderRow({ order }: { order: Order }) {
  const { icon: Icon, cls } = paymentTone(order.payment_status);
  const firstImage = order.items[0]?.image_url ?? null;

  return (
    <div className="space-y-2 border-b py-3 last:border-b-0">
      <div className="flex gap-3">
        <div className="relative size-12 shrink-0 overflow-hidden rounded-md">
          <ProductImage src={firstImage} alt={order.items[0]?.product_name ?? "Order"} sizes="48px" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">
            {order.items[0]?.product_name ?? "Order"}
            {order.items.length > 1 && (
              <span className="text-muted-foreground"> +{order.items.length - 1} more</span>
            )}
          </p>
          <p className="font-mono text-[11px] text-muted-foreground">{order.id.slice(0, 8)}</p>
          <p className="text-xs text-muted-foreground">
            {new Date(order.created_at).toLocaleString()}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-sm font-semibold">
            {formatMoney(order.amount_total, order.currency)}
          </p>
          <span className={cn("flex items-center justify-end gap-1 text-xs", cls)}>
            <Icon className="size-3" />
            {order.payment_status ?? "PENDING"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 pl-15">
        <Badge variant={order.status === "CONFIRMED" ? "default" : "outline"} className="text-[10px]">
          {order.status}
        </Badge>
        {order.payment_status === "PAID" && (
          <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <Receipt className="size-3" /> Receipt available
          </span>
        )}
      </div>
    </div>
  );
}

export function OrdersDrawer() {
  const [open, setOpen] = useState(false);
  // Only fetched while the panel is open — the chat page shouldn't pay for
  // an orders round trip on every load.
  const { data: orders, isLoading } = useOrders(undefined, open);

  const confirmed = (orders ?? []).filter((o) => o.status === "CONFIRMED").length;

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button variant="outline" size="sm" className="relative gap-1.5">
            <Package className="size-4" />
            <span className="hidden sm:inline">Orders</span>
            {confirmed > 0 && (
              <Badge className="absolute -top-2 -right-2 flex size-4.5 items-center justify-center rounded-full p-0 text-[10px]">
                {confirmed}
              </Badge>
            )}
          </Button>
        }
      />
      <SheetContent className="flex flex-col p-0">
        <SheetHeader className="border-b">
          <SheetTitle>Your orders</SheetTitle>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-4">
          {isLoading ? (
            <div className="flex h-full items-center justify-center py-16">
              <Package className="size-6 animate-pulse text-muted-foreground" />
            </div>
          ) : (orders ?? []).length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 py-16 text-center text-sm text-muted-foreground">
              <Package className="size-8" />
              <p>No orders yet — anything you buy will show up here.</p>
            </div>
          ) : (
            (orders ?? []).map((order) => <OrderRow key={order.id} order={order} />)
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
