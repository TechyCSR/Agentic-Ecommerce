"use client";

import { CreditCard, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PaymentStatusBadge } from "@/components/orders/status-badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney } from "@/lib/money";
import { usePayments } from "@/lib/queries/use-orders";
import { formatDateTime } from "@/lib/utils";

const PAGE_SIZE = 10;

export default function PaymentsPage() {
  const [page, setPage] = useState(0);
  const { data, isLoading } = usePayments({ limit: PAGE_SIZE, offset: page * PAGE_SIZE });

  const payments = data?.data ?? [];
  const total = data?.meta?.total ?? 0;
  const hasMore = data?.meta?.has_more ?? false;

  const captured = payments
    .filter((p) => p.status === "CAPTURED")
    .reduce((sum, p) => sum + p.amount, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Payments</h1>
        <p className="text-muted-foreground">
          Payments received for your orders, verified by the backend before being recorded.
        </p>
      </div>

      {payments.length > 0 && (
        <div className="rounded-md border p-4">
          <p className="text-sm text-muted-foreground">Captured on this page</p>
          <p className="text-2xl font-semibold">
            {formatMoney(captured, payments[0]?.currency ?? "INR")}
          </p>
        </div>
      )}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Payment ID</TableHead>
              <TableHead>Order</TableHead>
              <TableHead>Received</TableHead>
              <TableHead>Amount</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="h-32 text-center">
                  <Loader2 className="mx-auto size-5 animate-spin text-muted-foreground" />
                </TableCell>
              </TableRow>
            ) : payments.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                  <CreditCard className="mx-auto mb-2 size-6" />
                  No payments received yet.
                </TableCell>
              </TableRow>
            ) : (
              payments.map((payment) => (
                <TableRow key={payment.id}>
                  <TableCell className="font-mono text-xs">
                    {payment.provider_payment_id ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`/dashboard/orders/${payment.order_id}`}
                      className="font-mono text-xs hover:underline"
                    >
                      {payment.order_id.slice(0, 8)}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDateTime(payment.created_at)}
                  </TableCell>
                  <TableCell className="font-medium">
                    {formatMoney(payment.amount, payment.currency)}
                  </TableCell>
                  <TableCell>
                    <PaymentStatusBadge status={payment.status} />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {total > 0 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Showing {page * PAGE_SIZE + 1}-
            {Math.min(page * PAGE_SIZE + PAGE_SIZE, total)} of {total}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasMore}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
