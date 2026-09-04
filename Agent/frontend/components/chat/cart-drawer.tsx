"use client";

import { Loader2, Minus, Package, Plus, ShoppingCart, Trash2 } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import { toast } from "sonner";

import { CheckoutDialog } from "@/components/checkout/checkout-dialog";
import { useCreateCheckout } from "@/lib/queries/use-orders";
import type { Order } from "@/lib/types";

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

/** Upper bound on a single cart line. The real ceiling is stock, which only
 *  the server knows; this just stops a typo like "1000000" becoming a request. */
const MAX_QTY_INPUT = 999;

function CartLine({ sessionId, item }: { sessionId: string; item: CartItem }) {
  const updateItem = useUpdateCartItem();
  const removeItem = useRemoveCartItem();
  const [pendingQty, setPendingQty] = useState<number | null>(null);
  // What's in the box while it's being typed in; null means "show the truth".
  const [draftQty, setDraftQty] = useState<string | null>(null);
  const busy = updateItem.isPending || removeItem.isPending;

  const shownQty = draftQty ?? String(pendingQty ?? item.quantity);

  function changeQty(next: number) {
    if (next < 1 || next === item.quantity) {
      setDraftQty(null);
      return;
    }
    setPendingQty(next);
    updateItem.mutate(
      { sessionId, itemId: item.id, quantity: next },
      {
        onSuccess: (updated) => {
          // The server is the authority on stock and trims anything above
          // it, so tell the buyer why they got fewer than they asked for
          // rather than silently showing a different number.
          if (updated.stock_limited) {
            toast.warning(
              `Only ${updated.available_stock} available — quantity set to ${updated.quantity}.`
            );
          }
        },
        onError: (err) => {
          toast.error(err instanceof Error ? err.message : "Failed to update quantity");
        },
        onSettled: () => {
          setPendingQty(null);
          setDraftQty(null);
        },
      }
    );
  }

  /** Commits whatever was typed, ignoring anything that isn't a usable number. */
  function commitDraft() {
    if (draftQty === null) return;
    const parsed = Number.parseInt(draftQty, 10);
    if (!Number.isFinite(parsed) || parsed < 1) {
      // Empty box or nonsense: snap back rather than guessing an intent.
      setDraftQty(null);
      return;
    }
    changeQty(Math.min(parsed, MAX_QTY_INPUT));
  }

  return (
    <div className="flex gap-3 border-b py-3 last:border-b-0">
      <div className="relative size-14 shrink-0 overflow-hidden rounded-md border bg-muted">
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
          <div className="flex items-center rounded-md border">
            <Button
              variant="ghost"
              size="icon-sm"
              className="size-6 rounded-sm"
              disabled={busy || item.quantity <= 1}
              onClick={() => changeQty(item.quantity - 1)}
            >
              <Minus className="size-3" />
            </Button>
            <input
              type="text"
              inputMode="numeric"
              aria-label={`Quantity for ${item.product_name}`}
              className="w-8 bg-transparent text-center text-xs tabular-nums outline-none focus:rounded focus:ring-1 focus:ring-ring disabled:opacity-50"
              value={shownQty}
              disabled={busy}
              onChange={(e) => {
                const next = e.target.value.replace(/[^0-9]/g, "").slice(0, 3);
                setDraftQty(next);
              }}
              onBlur={commitDraft}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  e.currentTarget.blur();
                } else if (e.key === "Escape") {
                  setDraftQty(null);
                  e.currentTarget.blur();
                }
              }}
            />
            <Button
              variant="ghost"
              size="icon-sm"
              className="size-6 rounded-sm"
              disabled={busy || item.quantity >= MAX_QTY_INPUT}
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

  const createCheckout = useCreateCheckout();
  const [checkoutOrder, setCheckoutOrder] = useState<Order | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  async function handleCheckout() {
    try {
      // The backend re-validates every line against the live catalog and
      // returns the authoritative amount — the client never prices anything.
      const order = await createCheckout.mutateAsync(sessionId);
      setSheetOpen(false);
      setCheckoutOrder(order);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't start checkout");
    }
  }

  return (
    <>
    <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
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
            <Button className="w-full" onClick={handleCheckout} disabled={createCheckout.isPending}>
              {createCheckout.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Checking availability…
                </>
              ) : (
                "Proceed to checkout"
              )}
            </Button>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>

    {/* Kept outside the Sheet root: nesting two dialog roots fights over
        focus management when the sheet closes as checkout opens. */}
    {checkoutOrder && (
      <CheckoutDialog
        order={checkoutOrder}
        open={!!checkoutOrder}
        onOpenChange={(open) => !open && setCheckoutOrder(null)}
      />
    )}
    </>
  );
}
