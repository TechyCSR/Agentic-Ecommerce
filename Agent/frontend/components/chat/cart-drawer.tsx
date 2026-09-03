"use client";

import { Minus, Package, Plus, ShoppingCart, Trash2 } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { useRemoveCartItem, useUpdateCartItem } from "@/lib/queries/use-chat";
import { formatMoney } from "@/lib/money";
import type { Cart, CartItem } from "@/lib/types";

function CartLine({ sessionId, item }: { sessionId: string; item: CartItem }) {
  const updateItem = useUpdateCartItem();
  const removeItem = useRemoveCartItem();
  const [pendingQty, setPendingQty] = useState<number | null>(null);
  const busy = updateItem.isPending || removeItem.isPending;

  function changeQty(next: number) {
    if (next < 1) return;
    setPendingQty(next);
    updateItem.mutate(
      { sessionId, itemId: item.id, quantity: next },
      {
        onError: (err) => {
          toast.error(err instanceof Error ? err.message : "Failed to update quantity");
        },
        onSettled: () => setPendingQty(null),
      }
    );
  }

  return (
    <div className="flex gap-3 border-b py-3 last:border-b-0">
      <div className="relative size-14 shrink-0 overflow-hidden rounded-md bg-muted">
        {item.image_url ? (
          <Image src={item.image_url} alt={item.product_name} fill unoptimized className="object-cover" />
        ) : (
          <div className="flex size-full items-center justify-center">
            <Package className="size-5 text-muted-foreground" />
          </div>
        )}
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{item.product_name}</p>
            <p className="truncate text-xs text-muted-foreground">{item.variant_name}</p>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            disabled={busy}
            onClick={() =>
              removeItem.mutate(
                { sessionId, itemId: item.id },
                { onError: (err) => toast.error(err instanceof Error ? err.message : "Failed to remove item") }
              )
            }
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 rounded-full border">
            <Button
              variant="ghost"
              size="icon-sm"
              className="size-6 rounded-full"
              disabled={busy || item.quantity <= 1}
              onClick={() => changeQty(item.quantity - 1)}
            >
              <Minus className="size-3" />
            </Button>
            <span className="w-5 text-center text-xs tabular-nums">
              {pendingQty ?? item.quantity}
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              className="size-6 rounded-full"
              disabled={busy}
              onClick={() => changeQty(item.quantity + 1)}
            >
              <Plus className="size-3" />
            </Button>
          </div>
          <span className="text-sm font-semibold">
            {formatMoney(item.line_total.amount, item.line_total.currency)}
          </span>
        </div>
      </div>
    </div>
  );
}

export function CartDrawer({ sessionId, cart }: { sessionId: string; cart: Cart | undefined }) {
  const items = cart?.items ?? [];
  const count = items.reduce((sum, i) => sum + i.quantity, 0);

  return (
    <Sheet>
      <SheetTrigger
        render={
          <Button variant="outline" size="sm" className="relative gap-1.5">
            <ShoppingCart className="size-4" />
            <span className="hidden sm:inline">Cart</span>
            {count > 0 && (
              <Badge className="absolute -top-2 -right-2 flex size-4.5 items-center justify-center rounded-full p-0 text-[10px]">
                {count}
              </Badge>
            )}
          </Button>
        }
      />
      <SheetContent className="flex flex-col p-0">
        <SheetHeader className="border-b">
          <SheetTitle>Your cart</SheetTitle>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-4">
          {items.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 py-16 text-center text-sm text-muted-foreground">
              <ShoppingCart className="size-8" />
              <p>Nothing here yet — add a product from the chat.</p>
            </div>
          ) : (
            items.map((item) => <CartLine key={item.id} sessionId={sessionId} item={item} />)
          )}
        </div>

        {items.length > 0 && (
          <SheetFooter className="border-t">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Subtotal</span>
              <span className="text-base font-semibold">
                {cart ? formatMoney(cart.total.amount, cart.total.currency) : "—"}
              </span>
            </div>
            <Button
              className="w-full"
              onClick={() => toast.success("Checkout isn't available yet — this confirms your picks for now.")}
            >
              Ready for checkout
            </Button>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>
  );
}
