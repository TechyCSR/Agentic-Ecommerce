"use client";

import { CheckCircle2, Clock, Lock, PackageCheck, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { CheckoutDialog } from "@/components/checkout/checkout-dialog";
import { Button } from "@/components/ui/button";
import { formatMoney } from "@/lib/money";
import { useOrder } from "@/lib/queries/use-orders";
import type { Order, PreparedCheckout } from "@/lib/types";

/**
 * Counts down the merchant's stock hold.
 *
 * The tick belongs in an effect — it is driven by wall time, not by a prop.
 * A new deadline is handled during render instead, so re-pricing an order
 * doesn't cost a frame showing the old clock.
 */
function useHoldSecondsLeft(reservedUntil: string | null | undefined) {
  const [secondsLeft, setSecondsLeft] = useState(() => remaining(reservedUntil));
  const [trackedUntil, setTrackedUntil] = useState(reservedUntil);

  if (trackedUntil !== reservedUntil) {
    setTrackedUntil(reservedUntil);
    setSecondsLeft(remaining(reservedUntil));
  }

  useEffect(() => {
    if (!reservedUntil) return;
    const id = setInterval(() => setSecondsLeft(remaining(reservedUntil)), 1000);
    return () => clearInterval(id);
  }, [reservedUntil]);

  return secondsLeft;
}

function remaining(reservedUntil: string | null | undefined) {
  if (!reservedUntil) return null;
  const ms = new Date(reservedUntil).getTime() - Date.now();
  return Number.isNaN(ms) ? null : Math.max(0, Math.floor(ms / 1000));
}

function formatCountdown(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

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
  // Fetched whether or not the dialog is open. Gating this on `open` meant
  // that closing the dialog after paying disabled the query, `order` went
  // undefined, and the card fell back to offering "Pay" for something
  // already paid for.
  const { data: order } = useOrder(checkout.order_id);
  const holdSeconds = useHoldSecondsLeft(checkout.stock_reserved_until);

  const paid = order?.payment_status === "PAID";

  if (paid) return <PaidCard checkout={checkout} order={order} />;

  if (dismissed) {
    return (
      <button
        type="button"
        onClick={() => setDismissed(false)}
        className="w-fit rounded-md border bg-card px-2.5 py-1 text-xs text-muted-foreground transition-colors duration-100 hover:border-foreground/25 hover:text-foreground"
      >
        <Clock className="mr-1 inline size-3" />
        Saved for later — {formatMoney(checkout.amount, checkout.currency)} · pay now
      </button>
    );
  }

  return (
    <>
      {/* The warm accent is reserved for the point where a person has to
          act; it appears nowhere else in the chat. */}
      <div
        className="rounded-xl border bg-card p-3.5"
        style={{ borderColor: "color-mix(in oklch, var(--human), transparent 62%)" }}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-sm font-medium">Ready when you are</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {checkout.items.length} item{checkout.items.length === 1 ? "" : "s"} ·{" "}
              <span className="font-semibold text-foreground">
                {formatMoney(checkout.amount, checkout.currency)}
              </span>
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setDismissed(true)}>
              <Clock className="size-3.5" />
              Later
            </Button>
            <Button size="sm" onClick={() => setOpen(true)}>
              <Lock className="size-3.5" />
              Pay {formatMoney(checkout.amount, checkout.currency)}
            </Button>
          </div>
        </div>
        {holdSeconds !== null && (
          <p className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <PackageCheck className="size-3 shrink-0" />
            {holdSeconds > 0 ? (
              <>
                Your items are held for{" "}
                <span className="font-medium tabular-nums text-foreground">
                  {formatCountdown(holdSeconds)}
                </span>
              </>
            ) : (
              // The hold is re-taken on the Pay path, so this is a heads-up
              // rather than a dead end.
              <>Hold expired — stock is re-checked when you pay</>
            )}
          </p>
        )}
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

/**
 * What the card becomes once the money has actually moved.
 *
 * Settled state, not a disabled button: nothing here can be clicked back
 * into a payment, and the amount shown is the order's own total rather than
 * whatever the card was created with.
 */
function PaidCard({ checkout, order }: { checkout: PreparedCheckout; order?: Order }) {
  const total = order
    ? formatMoney(order.amount_total, order.currency)
    : formatMoney(checkout.amount, checkout.currency);
  const paidAt = order?.confirmed_at ? new Date(order.confirmed_at) : null;

  return (
    <div
      className="rounded-xl border bg-card p-3.5"
      style={{ borderColor: "color-mix(in oklch, var(--agent-2), transparent 62%)" }}
    >
      <div className="flex items-start gap-2.5">
        <CheckCircle2
          className="mt-0.5 size-4 shrink-0"
          style={{ color: "var(--agent-2)" }}
        />
        <div className="min-w-0">
          <p className="text-sm font-medium">Paid — {total}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {checkout.items.length} item{checkout.items.length === 1 ? "" : "s"}
            {order?.status ? ` · ${order.status.toLowerCase()}` : ""}
            {paidAt
              ? ` · ${paidAt.toLocaleString(undefined, {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}`
              : ""}
          </p>
        </div>
      </div>
    </div>
  );
}
