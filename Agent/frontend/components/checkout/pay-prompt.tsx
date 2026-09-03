"use client";

import { Clock, Lock, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { CheckoutDialog } from "@/components/checkout/checkout-dialog";
import { Button } from "@/components/ui/button";
import { formatMoney } from "@/lib/money";
import { useOrder } from "@/lib/queries/use-orders";
import type { PreparedCheckout } from "@/lib/types";

/**
 * The hand-off point between agent and buyer.
 *
 * The agent can price an order but cannot pay for one — this is where the
 * buyer takes over. Nothing is authorized until they press this button, and
 * the amount shown is the backend's own total, not anything the model wrote.
 */
export function PayPrompt({ checkout }: { checkout: PreparedCheckout }) {
  const [open, setOpen] = useState(false);
  // Dismissing only hides the card — the order stays payable from Orders,
  // so choosing 'later' never quietly abandons it.
  const [dismissed, setDismissed] = useState(false);
  const { data: order } = useOrder(open ? checkout.order_id : undefined);

  const paid = order?.payment_status === "PAID";

  if (dismissed && !paid) {
    return (
      <button
        type="button"
        onClick={() => setDismissed(false)}
        className="w-fit rounded-full border bg-card/60 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <Clock className="mr-1 inline size-3" />
        Saved for later — {formatMoney(checkout.amount, checkout.currency)} · pay now
      </button>
    );
  }

  return (
    <>
      <div className="rounded-xl border bg-card/60 p-4 backdrop-blur-sm">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-sm font-medium">
              {paid ? "Payment complete" : "Ready when you are"}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {checkout.items.length} item{checkout.items.length === 1 ? "" : "s"} ·{" "}
              <span className="font-semibold text-foreground">
                {formatMoney(checkout.amount, checkout.currency)}
              </span>
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {!paid && (
              <Button variant="ghost" size="sm" onClick={() => setDismissed(true)}>
                <Clock className="size-3.5" />
                Later
              </Button>
            )}
            <Button size="sm" disabled={paid} onClick={() => setOpen(true)}>
              <Lock className="size-3.5" />
              {paid ? "Paid" : `Pay ${formatMoney(checkout.amount, checkout.currency)}`}
            </Button>
          </div>
        </div>
        <p className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <ShieldCheck className="size-3" />
          Only you can authorize this payment — the agent never charges you.
        </p>
      </div>

      {order && (
        <CheckoutDialog order={order} open={open} onOpenChange={setOpen} />
      )}
    </>
  );
}
