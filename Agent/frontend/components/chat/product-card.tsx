"use client";

import { Check, Loader2, ShoppingCart } from "lucide-react";
import { useState } from "react";

import { ProductDetailDialog } from "@/components/chat/product-detail-dialog";
import { ProductImage } from "@/components/chat/product-image";
import { Button } from "@/components/ui/button";
import { formatMoney } from "@/lib/money";
import type { ProductCard as ProductCardType } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ProductCardView({
  product,
  onBuyNow,
  isAdding,
  isSelected,
}: {
  product: ProductCardType;
  onBuyNow: (productId: string, variantId: string) => void;
  isAdding: boolean;
  isSelected?: boolean;
}) {
  const [detailOpen, setDetailOpen] = useState(false);

  const inStockVariants = product.variants.filter((v) => v.availability === "IN_STOCK");
  const defaultVariant = inStockVariants[0] ?? product.variants[0];
  const hasStock = defaultVariant?.availability === "IN_STOCK";

  return (
    <>
      <div
        className={cn(
          "group flex w-[13.5rem] shrink-0 snap-start flex-col overflow-hidden rounded-lg border bg-card transition-colors duration-150",
          "hover:border-foreground/25",
          isSelected && "border-primary/60 ring-1 ring-primary/25"
        )}
      >
        <button
          type="button"
          onClick={() => setDetailOpen(true)}
          className="relative aspect-square w-full overflow-hidden"
          aria-label={`View details for ${product.name}`}
        >
          <ProductImage
            src={product.image_url}
            alt={product.name}
            className="transition-transform duration-200 group-hover:scale-[1.02]"
          />
        </button>

        <div className="flex flex-1 flex-col gap-2 p-3">
          <div className="min-h-9">
            <p className="line-clamp-2 text-sm leading-snug font-medium">{product.name}</p>
          </div>

          <div className="flex items-baseline justify-between gap-2">
            <span className="text-[15px] font-semibold tabular-nums">
              {defaultVariant?.price
                ? formatMoney(defaultVariant.price.amount, defaultVariant.price.currency)
                : "—"}
            </span>
            {product.brand && (
              <span className="truncate text-xs text-muted-foreground">{product.brand}</span>
            )}
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <span
              className={cn(
                "size-1.5 rounded-full",
                hasStock ? "bg-emerald-500" : "bg-muted-foreground/50"
              )}
            />
            <span className={hasStock ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground"}>
              {hasStock ? "In stock" : "Out of stock"}
            </span>
          </div>

          <div className="mt-auto grid grid-cols-2 gap-2 pt-1">
            <Button variant="outline" size="sm" onClick={() => setDetailOpen(true)}>
              View
            </Button>
            <Button
              size="sm"
              disabled={!hasStock || !defaultVariant || isAdding}
              onClick={() => defaultVariant && onBuyNow(product.product_id, defaultVariant.variant_id)}
            >
              {isAdding ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : isSelected ? (
                <Check className="size-3.5" />
              ) : (
                <ShoppingCart className="size-3.5" />
              )}
              {isSelected ? "Added" : "Buy"}
            </Button>
          </div>
        </div>
      </div>

      <ProductDetailDialog
        product={product}
        open={detailOpen}
        onOpenChange={setDetailOpen}
        onBuyNow={onBuyNow}
        isAdding={isAdding}
      />
    </>
  );
}
