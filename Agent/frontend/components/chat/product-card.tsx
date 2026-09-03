"use client";

import { Loader2, Package, ShoppingCart, Store } from "lucide-react";
import Image from "next/image";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatMoney } from "@/lib/money";
import type { ProductCard as ProductCardType } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ProductCardView({
  product,
  onBuyNow,
  isAdding,
}: {
  product: ProductCardType;
  onBuyNow: (productId: string, variantId: string) => void;
  isAdding: boolean;
}) {
  const inStockVariants = product.variants.filter((v) => v.availability === "IN_STOCK");
  const defaultVariant = inStockVariants[0] ?? product.variants[0];
  const [variantId, setVariantId] = useState(defaultVariant?.variant_id);
  const selectedVariant =
    product.variants.find((v) => v.variant_id === variantId) ?? defaultVariant;

  const hasStock = selectedVariant?.availability === "IN_STOCK";

  return (
    <Card className="w-64 shrink-0 overflow-hidden">
      <div className="relative aspect-square w-full bg-muted">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.name}
            fill
            unoptimized
            className="object-cover"
          />
        ) : (
          <div className="flex size-full items-center justify-center">
            <Package className="size-8 text-muted-foreground" />
          </div>
        )}
      </div>
      <CardHeader className="p-3 pb-0">
        <CardTitle className="line-clamp-2 text-sm leading-snug">{product.name}</CardTitle>
        {product.store_name && (
          <CardDescription className="flex items-center gap-1 text-xs">
            <Store className="size-3" /> {product.store_name}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent className="space-y-2 p-3 pt-2">
        <div className="flex items-center justify-between">
          <span className="text-base font-semibold">
            {selectedVariant?.price
              ? formatMoney(selectedVariant.price.amount, selectedVariant.price.currency)
              : "—"}
          </span>
          <Badge variant={hasStock ? "default" : "outline"} className="text-xs">
            {selectedVariant?.availability?.replace("_", " ") ?? "Unknown"}
          </Badge>
        </div>

        {product.variants.length > 1 && (
          <Select value={variantId} onValueChange={(v) => v && setVariantId(v)}>
            <SelectTrigger className="h-8 w-full text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {product.variants.map((v) => (
                <SelectItem key={v.variant_id} value={v.variant_id} className="text-xs">
                  {v.name}
                  {v.availability !== "IN_STOCK" ? " (out of stock)" : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </CardContent>
      <CardFooter className="grid grid-cols-2 gap-2 p-3 pt-0">
        <Dialog>
          <DialogTrigger render={<Button variant="outline" size="sm" />}>
            View Details
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{product.name}</DialogTitle>
              <DialogDescription>
                {product.brand && <span>{product.brand} · </span>}
                {product.category}
              </DialogDescription>
            </DialogHeader>
            <p className="text-sm text-muted-foreground">
              {product.description || "No description available."}
            </p>
            <div className="space-y-1.5">
              {product.variants.map((v) => (
                <div
                  key={v.variant_id}
                  className={cn(
                    "flex items-center justify-between rounded-md border p-2 text-sm",
                    v.variant_id === variantId && "border-primary"
                  )}
                >
                  <span>{v.name}</span>
                  <span className="flex items-center gap-2">
                    {v.price && formatMoney(v.price.amount, v.price.currency)}
                    <Badge variant={v.availability === "IN_STOCK" ? "default" : "outline"}>
                      {v.availability?.replace("_", " ")}
                    </Badge>
                  </span>
                </div>
              ))}
            </div>
          </DialogContent>
        </Dialog>
        <Button
          size="sm"
          disabled={!hasStock || !selectedVariant || isAdding}
          onClick={() => selectedVariant && onBuyNow(product.product_id, selectedVariant.variant_id)}
        >
          {isAdding ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <ShoppingCart className="size-3.5" />
          )}
          Add to cart
        </Button>
      </CardFooter>
    </Card>
  );
}
