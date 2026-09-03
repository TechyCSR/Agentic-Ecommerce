"use client";

import { useUser } from "@clerk/nextjs";
import { AlertCircle, CheckCircle2, Loader2, Lock, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { ProductImage } from "@/components/chat/product-image";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { formatMoney } from "@/lib/money";
import {
  useAuthorizePayment,
  useRecordPaymentFailure,
  useVerifyPayment,
} from "@/lib/queries/use-orders";
import { openRazorpayCheckout } from "@/lib/razorpay";
import type { Order } from "@/lib/types";

type Stage = "summary" | "authorizing" | "awaiting_payment" | "verifying" | "paid" | "failed";

export function CheckoutDialog({
  order,
  open,
  onOpenChange,
}: {
  order: Order;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { user } = useUser();
  const [stage, setStage] = useState<Stage>("summary");
  const [failureReason, setFailureReason] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState<Order | null>(null);
  const [paymentId, setPaymentId] = useState<string | null>(null);

  const authorize = useAuthorizePayment();
  const verify = useVerifyPayment();
  const recordFailure = useRecordPaymentFailure();

  const isRetry = stage === "failed";

  /** Runs only from a click on the Pay button — never automatically. */
  async function handlePay() {
    setFailureReason(null);
    setStage("authorizing");

    try {
      const auth = await authorize.mutateAsync({ orderId: order.id, retry: isRetry });
      setStage("awaiting_payment");

      await openRazorpayCheckout({
        keyId: auth.key_id,
        providerOrderId: auth.provider_order_id,
        amount: auth.amount,
        currency: auth.currency,
        description: order.items.map((i) => i.product_name).join(", ").slice(0, 80),
        prefill: {
          name: user?.fullName ?? undefined,
          email: user?.primaryEmailAddress?.emailAddress,
        },
        onSuccess: async (response) => {
          // The browser's "success" is only a claim — the backend verifies
          // the signature before anything is treated as paid.
          setStage("verifying");
          try {
            const result = await verify.mutateAsync({
              orderId: order.id,
              razorpayOrderId: response.razorpay_order_id,
              razorpayPaymentId: response.razorpay_payment_id,
              razorpaySignature: response.razorpay_signature,
            });
            setConfirmed(result.order);
            setPaymentId(result.payment.provider_payment_id);
            setStage("paid");
          } catch (err) {
            setFailureReason(
              err instanceof Error ? err.message : "We couldn't verify this payment."
            );
            setStage("failed");
          }
        },
        onDismiss: () => {
          setStage((current) => {
            // Ignore a dismiss that arrives after a successful verification.
            if (current === "verifying" || current === "paid") return current;
            recordFailure.mutate({
              orderId: order.id,
              razorpayOrderId: auth.provider_order_id,
              cancelled: true,
              reason: "Checkout closed before payment",
            });
            setFailureReason("You closed the payment window before completing payment.");
            return "failed";
          });
        },
        onFailure: (reason) => {
          recordFailure.mutate({
            orderId: order.id,
            razorpayOrderId: auth.provider_order_id,
            cancelled: false,
            reason,
          });
          setFailureReason(reason);
          setStage("failed");
        },
      });
    } catch (err) {
      setFailureReason(err instanceof Error ? err.message : "We couldn't start the payment.");
      setStage("failed");
    }
  }

  const busy = stage === "authorizing" || stage === "awaiting_payment" || stage === "verifying";

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        // Don't let the dialog close mid-payment and lose the result.
        if (!next && busy) return;
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-md">
        {stage === "paid" && confirmed ? (
          <div className="space-y-4">
            <DialogTitle className="sr-only">Payment successful</DialogTitle>
            <div className="flex flex-col items-center gap-2 pt-2 text-center">
              <div className="animate-in zoom-in-50 flex size-12 items-center justify-center rounded-full bg-emerald-500/10 duration-300">
                <CheckCircle2 className="size-7 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="font-semibold">Payment successfully verified</p>
                <p className="text-sm text-muted-foreground">Your order has been confirmed.</p>
              </div>
            </div>

            <Separator />

            <dl className="space-y-2 text-sm">
              <Row label="Order ID" value={<span className="font-mono text-xs">{confirmed.id}</span>} />
              <Row
                label="Amount paid"
                value={<span className="font-semibold">{formatMoney(confirmed.amount_total, confirmed.currency)}</span>}
              />
              <Row
                label="Payment status"
                value={<StatusPill tone="success">{confirmed.payment_status ?? "PAID"}</StatusPill>}
              />
              <Row
                label="Order status"
                value={<StatusPill tone="success">{confirmed.status}</StatusPill>}
              />
              {paymentId && (
                <Row label="Payment ID" value={<span className="font-mono text-xs">{paymentId}</span>} />
              )}
              {confirmed.confirmed_at && (
                <Row label="Payment time" value={new Date(confirmed.confirmed_at).toLocaleString()} />
              )}
            </dl>

            <Separator />

            <div className="space-y-2">
              {confirmed.items.map((item) => (
                <div key={`${item.product_id}-${item.variant_id}`} className="flex justify-between gap-3 text-sm">
                  <span className="truncate">
                    {item.product_name}
                    <span className="text-muted-foreground"> × {item.quantity}</span>
                  </span>
                  <span className="shrink-0">
                    {formatMoney(item.line_total.amount, item.line_total.currency)}
                  </span>
                </div>
              ))}
            </div>

            <Button className="w-full" onClick={() => onOpenChange(false)}>
              Done
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <DialogTitle>Order summary</DialogTitle>

            <div className="space-y-3">
              {order.items.map((item) => (
                <div key={`${item.product_id}-${item.variant_id}`} className="flex gap-3">
                  <div className="relative size-14 shrink-0 overflow-hidden rounded-md">
                    <ProductImage src={item.image_url} alt={item.product_name} sizes="56px" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{item.product_name}</p>
                    {item.variant_name && (
                      <p className="truncate text-xs text-muted-foreground">{item.variant_name}</p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Quantity: {item.quantity} ·{" "}
                      {formatMoney(item.unit_price.amount, item.unit_price.currency)} each
                    </p>
                  </div>
                  <span className="shrink-0 text-sm font-medium">
                    {formatMoney(item.line_total.amount, item.line_total.currency)}
                  </span>
                </div>
              ))}
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Total</span>
              <span className="text-lg font-semibold">
                {formatMoney(order.amount_total, order.currency)}
              </span>
            </div>

            {stage === "failed" && failureReason && (
              <div className="flex gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm">
                <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
                <div>
                  <p className="font-medium">Your payment was not completed.</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{failureReason}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    No successful payment was recorded.
                  </p>
                </div>
              </div>
            )}

            <Button className="w-full" onClick={handlePay} disabled={busy}>
              {busy ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  {stage === "verifying" ? "Verifying payment…" : "Opening secure checkout…"}
                </>
              ) : (
                <>
                  <Lock className="size-4" />
                  {isRetry ? "Try payment again" : `Pay ${formatMoney(order.amount_total, order.currency)}`}
                </>
              )}
            </Button>

            <p className="flex items-center justify-center gap-1.5 text-center text-[11px] text-muted-foreground">
              <ShieldCheck className="size-3.5" />
              Razorpay Test Mode · every payment is verified on our server
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="truncate text-right">{value}</dd>
    </div>
  );
}

function StatusPill({ children, tone }: { children: React.ReactNode; tone: "success" }) {
  return (
    <span
      className={
        tone === "success"
          ? "rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-400"
          : ""
      }
    >
      {children}
    </span>
  );
}
