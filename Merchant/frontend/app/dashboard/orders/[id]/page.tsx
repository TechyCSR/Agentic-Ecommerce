"use client";

import { ArrowLeft, Check, Loader2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";

import { OrderStatusBadge, PaymentStatusBadge } from "@/components/orders/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney } from "@/lib/money";
import { useOrder, useUpdateFulfillment } from "@/lib/queries/use-orders";
import { FULFILLMENT_FLOW, type OrderStatus } from "@/lib/types";
import { cn, formatDateTime } from "@/lib/utils";

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: order, isLoading } = useOrder(id);
  const updateFulfillment = useUpdateFulfillment();

  async function setStatus(status: OrderStatus) {
    try {
      await updateFulfillment.mutateAsync({ orderId: id, status });
      toast.success(`Order marked ${status.toLowerCase()}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't update this order");
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!order) {
    return <p className="text-muted-foreground">Order not found.</p>;
  }

  const currentStep = FULFILLMENT_FLOW.indexOf(order.status);
  const payment = order.payments?.[order.payments.length - 1];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <Button
            variant="ghost"
            size="sm"
            className="-ml-2"
            render={<Link href="/dashboard/orders" />}
          >
            <ArrowLeft className="size-4" />
            Orders
          </Button>
          <h1 className="font-mono text-xl font-semibold tracking-tight">{order.id}</h1>
          <p className="text-muted-foreground">
            Placed {formatDateTime(order.placed_at ?? order.created_at)}
            {order.buyer_ref ? ` · buyer ${order.buyer_ref}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <PaymentStatusBadge status={order.payment_status} />
          <OrderStatusBadge status={order.status} />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fulfillment</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {FULFILLMENT_FLOW.map((step, i) => {
              const done = currentStep >= i && currentStep !== -1;
              return (
                <Button
                  key={step}
                  size="sm"
                  variant={done ? "default" : "outline"}
                  disabled={updateFulfillment.isPending || order.status === step}
                  onClick={() => setStatus(step)}
                >
                  {done && <Check className="size-3.5" />}
                  {step}
                </Button>
              );
            })}
          </div>
          <p className="text-xs text-muted-foreground">
            The buyer&apos;s shopping agent reads this back, so updating it here is what
            answers &quot;where is my order?&quot; in their chat.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Items</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead>Qty</TableHead>
                <TableHead>Unit price</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(order.items ?? []).map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.product_name_snapshot}</TableCell>
                  <TableCell>{item.quantity}</TableCell>
                  <TableCell>{formatMoney(item.unit_price_amount, order.currency)}</TableCell>
                  <TableCell className="text-right">
                    {formatMoney(item.total_amount, order.currency)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Separator />
          <div className="flex items-center justify-between p-4">
            <span className="text-sm text-muted-foreground">Total</span>
            <span className="text-lg font-semibold">
              {formatMoney(order.total_amount, order.currency)}
            </span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Payment</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {payment ? (
            <>
              <Row label="Status" value={<PaymentStatusBadge status={payment.status} />} />
              <Row label="Provider" value={payment.provider} />
              <Row
                label="Payment ID"
                value={
                  <span className="font-mono text-xs">
                    {payment.provider_payment_id ?? "—"}
                  </span>
                }
              />
              <Row
                label="Amount"
                value={formatMoney(payment.amount, payment.currency)}
              />
              <Row label="Received" value={formatDateTime(payment.created_at)} />
            </>
          ) : (
            <p className="text-muted-foreground">No payment recorded.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className={cn("flex items-center justify-between gap-4")}>
      <span className="text-muted-foreground">{label}</span>
      <span>{value}</span>
    </div>
  );
}
