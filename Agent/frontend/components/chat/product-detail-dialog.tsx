"use client";

import { Check, Loader2, ShoppingCart, Store } from "lucide-react";
import { useState } from "react";

import { ProductImage } from "@/components/chat/product-image";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { formatMoney } from "@/lib/money";
import type { ProductCard as ProductCardType } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ProductDetailDialog({
  product,
  open,
  onOpenChange,
  onBuyNow,
  isAdding,
}: {
  product: ProductCardType;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onBuyNow: (productId: string, variantId: string) => void;
  isAdding: boolean;
}) {
  const images = product.images?.length ? product.images : product.image_url ? [product.image_url] : [];
  const [activeImage, setActiveImage] = useState(0);

  const inStockVariants = product.variants.filter((v) => v.availability === "IN_STOCK");
  const [variantId, setVariantId] = useState(
    (inStockVariants[0] ?? product.variants[0])?.variant_id
  );
  const selectedVariant =
    product.variants.find((v) => v.variant_id === variantId) ?? product.variants[0];
  const hasStock = selectedVariant?.availability === "IN_STOCK";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] gap-0 overflow-y-auto p-0 sm:max-w-lg">
        <DialogTitle className="sr-only">{product.name}</DialogTitle>

        {/* overflow-hidden + rounded top: without it the square image paints
            over DialogContent's rounded corners and looks like it's escaping
            the dialog. */}
        <div className="relative aspect-square w-full overflow-hidden rounded-t-xl sm:aspect-[4/3]">
          <ProductImage
            src={images[activeImage]}
            alt={product.name}
            sizes="(max-width: 640px) 100vw, 512px"
            priority
          />
        </div>

        {images.length > 1 && (
          <div className="flex gap-2 overflow-x-auto px-4 pt-3">
            {images.map((src, i) => (
              <button
                key={src}
                type="button"
                onClick={() => setActiveImage(i)}
                aria-label={`Image ${i + 1}`}
                className={cn(
                  "relative size-14 shrink-0 overflow-hidden rounded-md border transition-all",
                  i === activeImage ? "border-primary ring-1 ring-primary/40" : "opacity-70 hover:opacity-100"
                )}
              >
                <ProductImage src={src} alt={`${product.name} image ${i + 1}`} sizes="56px" />
              </button>
            ))}
          </div>
        )}

        <div className="space-y-4 p-4">
          <div className="space-y-1">
            <h2 className="text-base leading-snug font-semibold">{product.name}</h2>
            <p className="text-xs text-muted-foreground">
              {product.brand && <span>{product.brand} · </span>}
              {product.category}
            </p>
            {product.store_name && (
              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                <Store className="size-3" /> {product.store_name}
              </p>
            )}
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xl font-semibold">
              {selectedVariant?.price
                ? formatMoney(selectedVariant.price.amount, selectedVariant.price.currency)
                : "—"}
            </span>
            <Badge variant={hasStock ? "default" : "outline"}>
              {hasStock
                ? selectedVariant?.stock_quantity
                  ? `${selectedVariant.stock_quantity} in stock`
                  : "In stock"
                : (selectedVariant?.availability?.replace("_", " ") ?? "Unavailable")}
            </Badge>
          </div>

          {product.description && (
            <p className="text-sm leading-relaxed text-muted-foreground">{product.description}</p>
          )}

          {product.variants.length > 1 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Options</p>
              <div className="grid gap-1.5">
                {product.variants.map((v) => {
                  const active = v.variant_id === variantId;
                  const available = v.availability === "IN_STOCK";
                  return (
                    <button
                      key={v.variant_id}
                      type="button"
                      disabled={!available}
                      onClick={() => setVariantId(v.variant_id)}
                      className={cn(
                        "flex items-center justify-between rounded-lg border px-3 py-2 text-sm transition-colors",
                        active ? "border-primary bg-primary/5" : "hover:bg-muted",
                        !available && "cursor-not-allowed opacity-50"
                      )}
                    >
                      <span className="flex items-center gap-2">
                        {active && <Check className="size-3.5 text-primary" />}
                        {v.name}
                      </span>
                      <span className="text-muted-foreground">
                        {v.price && formatMoney(v.price.amount, v.price.currency)}
                        {!available && " · out of stock"}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <Button
            className="w-full"
            disabled={!hasStock || !selectedVariant || isAdding}
            onClick={() => {
              if (!selectedVariant) return;
              onBuyNow(product.product_id, selectedVariant.variant_id);
              onOpenChange(false);
            }}
          >
            {isAdding ? <Loader2 className="size-4 animate-spin" /> : <ShoppingCart className="size-4" />}
            Buy now
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
