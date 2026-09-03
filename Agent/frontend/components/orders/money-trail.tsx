"use client";

import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Receipt,
  ShieldCheck,
  ShoppingBag,
  Store,
} from "lucide-react";

import { formatMoney } from "@/lib/money";
import type { AuditEntry } from "@/lib/types";
import { cn, formatDateTime } from "@/lib/utils";

/** Plain-English labels — the trail is for the buyer, not for a log reader. */
const LABELS: Record<string, string> = {
  CHECKOUT_STARTED: "Checkout started",
  PRODUCT_VALIDATED: "Product checked against the catalog",
  PRICE_VALIDATED: "Price confirmed from the merchant",
  ORDER_CREATED: "Order created",
  CHECKOUT_REJECTED: "Checkout blocked",
  USER_PAYMENT_AUTHORIZED: "You authorized the payment",
  RAZORPAY_ORDER_CREATED: "Payment created with Razorpay",
  PAYMENT_ATTEMPTED: "Payment attempted",
  PAYMENT_VERIFIED: "Payment verified by our server",
  PAYMENT_FAILED: "Payment failed",
  PAYMENT_CANCELLED: "Payment cancelled",
  PAYMENT_RETRY_REQUESTED: "Retry requested",
  PAYMENT_WEBHOOK_RECEIVED: "Razorpay confirmed the payment",
  ORDER_CONFIRMED: "Order confirmed",
  RECEIPT_GENERATED: "Receipt issued",
  MERCHANT_SYNC_SUCCEEDED: "Sent to the merchant",
  MERCHANT_SYNC_FAILED: "Merchant notification failed",
};

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  USER_PAYMENT_AUTHORIZED: ShieldCheck,
  PAYMENT_VERIFIED: CheckCircle2,
  ORDER_CONFIRMED: CheckCircle2,
  PAYMENT_FAILED: AlertCircle,
  PAYMENT_CANCELLED: AlertCircle,
  CHECKOUT_REJECTED: AlertCircle,
  MERCHANT_SYNC_FAILED: AlertCircle,
  RECEIPT_GENERATED: Receipt,
  MERCHANT_SYNC_SUCCEEDED: Store,
  ORDER_CREATED: ShoppingBag,
};

const NEGATIVE = new Set([
  "PAYMENT_FAILED",
  "PAYMENT_CANCELLED",
  "CHECKOUT_REJECTED",
  "MERCHANT_SYNC_FAILED",
]);

export function MoneyTrail({ entries }: { entries: AuditEntry[] }) {
  if (entries.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        No money actions recorded yet.
      </p>
    );
  }

  return (
    <ol className="space-y-3">
      {entries.map((entry) => {
        const Icon = ICONS[entry.action] ?? FileText;
        const bad = NEGATIVE.has(entry.action);
        return (
          <li key={entry.id} className="flex gap-3">
            <div
              className={cn(
                "mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full",
                bad ? "bg-destructive/10 text-destructive" : "bg-muted text-muted-foreground"
              )}
            >
              <Icon className="size-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm">
                {LABELS[entry.action] ?? entry.action}
                {typeof entry.amount === "number" && (
                  <span className="ml-1.5 font-medium">
                    {formatMoney(entry.amount, entry.currency ?? "INR")}
                  </span>
                )}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatDateTime(entry.created_at)}
                {entry.order_id && (
                  <span className="ml-1.5 font-mono">· {entry.order_id.slice(0, 8)}</span>
                )}
              </p>
              {entry.reason && (
                <p className="mt-0.5 text-xs text-destructive">{entry.reason}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
