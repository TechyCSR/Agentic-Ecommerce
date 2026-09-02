"use client";

import { CheckCircle2 } from "lucide-react";

import { formatMoney } from "@/lib/money";
import type { Selection } from "@/lib/types";

export function SelectionBanner({ selection }: { selection: Selection }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b bg-primary/5 px-4 py-2.5 text-sm">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="size-4 text-primary" />
        <span>
          Ready for checkout: <strong>{selection.product_name}</strong> — {selection.variant_name}
        </span>
      </div>
      <span className="font-semibold">
        {formatMoney(selection.price.amount, selection.price.currency)}
      </span>
    </div>
  );
}
