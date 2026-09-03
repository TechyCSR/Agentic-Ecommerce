"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { ProductCardView } from "@/components/chat/product-card";
import { Button } from "@/components/ui/button";
import type { ProductCard } from "@/lib/types";

const INITIAL_VISIBLE = 3;

export function ProductGallery({
  products,
  onBuyNow,
  addingProductId,
  selectedProductIds,
}: {
  products: ProductCard[];
  onBuyNow: (productId: string, variantId: string) => void;
  addingProductId: string | null;
  selectedProductIds?: Set<string>;
}) {
  const [showAll, setShowAll] = useState(false);

  if (products.length === 0) return null;

  const visible = showAll ? products : products.slice(0, INITIAL_VISIBLE);
  const hidden = products.length - visible.length;

  return (
    <div className="space-y-2">
      {/* Horizontally scrollable on small screens, wrapping grid on wide ones —
          same markup, no duplicate rendering of the cards. */}
      <div className="-mx-1 flex snap-x snap-mandatory gap-3 overflow-x-auto px-1 pb-2 md:flex-wrap md:overflow-visible">
        {visible.map((product) => (
          <ProductCardView
            key={product.product_id}
            product={product}
            onBuyNow={onBuyNow}
            isAdding={addingProductId === product.product_id}
            isSelected={selectedProductIds?.has(product.product_id)}
          />
        ))}
      </div>

      {hidden > 0 && (
        <Button variant="ghost" size="sm" className="gap-1 text-xs" onClick={() => setShowAll(true)}>
          View all {products.length} products
          <ChevronDown className="size-3.5" />
        </Button>
      )}
    </div>
  );
}
