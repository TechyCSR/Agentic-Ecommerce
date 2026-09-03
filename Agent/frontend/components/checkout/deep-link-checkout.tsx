"use client";

import { useEffect, useState } from "react";

import { CheckoutDialog } from "@/components/checkout/checkout-dialog";
import { useOrder } from "@/lib/queries/use-orders";

/**
 * Opens payment directly for `?order=<id>`.
 *
 * Telegram sends buyers here to pay. Without this the link only landed on
 * the chat page and the order was left sitting unpaid, with no obvious way
 * to reach it.
 *
 * Reads `window.location.search` rather than `useSearchParams` so the page
 * can stay statically prerendered (the hook would force a Suspense boundary
 * for a purely client-side concern).
 */
export function DeepLinkCheckout() {
  // Read once during initial state rather than in an effect — the param is
  // known before the first paint, and this project disallows setState inside
  // effects.
  const [checkout, setCheckout] = useState<{ id: string | null; open: boolean }>(() => {
    if (typeof window === "undefined") return { id: null, open: false };
    const id = new URLSearchParams(window.location.search).get("order");
    return { id, open: !!id };
  });

  useEffect(() => {
    if (!checkout.id) return;
    // Drop the param so a refresh (or a back-navigation after paying)
    // doesn't reopen checkout for an order that's already done.
    const url = new URL(window.location.href);
    if (!url.searchParams.has("order")) return;
    url.searchParams.delete("order");
    window.history.replaceState({}, "", url.toString());
  }, [checkout.id]);

  const { data: order } = useOrder(checkout.id ?? undefined);

  if (!order) return null;

  return (
    <CheckoutDialog
      order={order}
      open={checkout.open}
      onOpenChange={(next) =>
        setCheckout((prev) => ({ id: next ? prev.id : null, open: next }))
      }
    />
  );
}
