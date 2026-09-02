"use client";

import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { majorToSmallestUnit, smallestUnitToMajor } from "@/lib/money";

export interface VariantDraft {
  sku: string;
  name: string;
  priceMajor: string;
  compareAtPriceMajor: string;
  stock_quantity: string;
}

export function emptyVariantDraft(): VariantDraft {
  return { sku: "", name: "", priceMajor: "", compareAtPriceMajor: "", stock_quantity: "0" };
}

interface VariantDraftListProps {
  variants: VariantDraft[];
  onChange: (variants: VariantDraft[]) => void;
  currency: string;
}

export function variantDraftsToPayload(variants: VariantDraft[], currency: string) {
  return variants
    .filter((v) => v.sku && v.name)
    .map((v) => ({
      sku: v.sku,
      name: v.name,
      price: majorToSmallestUnit(parseFloat(v.priceMajor || "0")),
      currency,
      compare_at_price: v.compareAtPriceMajor
        ? majorToSmallestUnit(parseFloat(v.compareAtPriceMajor))
        : null,
      stock_quantity: parseInt(v.stock_quantity || "0", 10),
    }));
}

export function VariantDraftList({ variants, onChange, currency }: VariantDraftListProps) {
  function update(index: number, patch: Partial<VariantDraft>) {
    onChange(variants.map((v, i) => (i === index ? { ...v, ...patch } : v)));
  }

  function remove(index: number) {
    onChange(variants.filter((_, i) => i !== index));
  }

  function add() {
    onChange([...variants, emptyVariantDraft()]);
  }

  return (
    <div className="space-y-4">
      {variants.map((variant, index) => (
        <div key={index} className="rounded-md border p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Variant name</Label>
              <Input
                placeholder="Black / Red Switch"
                value={variant.name}
                onChange={(e) => update(index, { name: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>SKU</Label>
              <Input
                placeholder="K8-BLACK-RED"
                value={variant.sku}
                onChange={(e) => update(index, { sku: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Price ({currency})</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                placeholder="4799.00"
                value={variant.priceMajor}
                onChange={(e) => update(index, { priceMajor: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Compare-at price ({currency})</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                placeholder="5999.00"
                value={variant.compareAtPriceMajor}
                onChange={(e) =>
                  update(index, { compareAtPriceMajor: e.target.value })
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>Stock quantity</Label>
              <Input
                type="number"
                min="0"
                value={variant.stock_quantity}
                onChange={(e) => update(index, { stock_quantity: e.target.value })}
              />
            </div>
          </div>
          <div className="mt-3 flex justify-end">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => remove(index)}
            >
              <Trash2 className="size-4" /> Remove variant
            </Button>
          </div>
        </div>
      ))}
      <Button type="button" variant="outline" onClick={add}>
        <Plus className="size-4" /> Add variant
      </Button>
    </div>
  );
}

export { smallestUnitToMajor };
