"use client";

import { Bot, User } from "lucide-react";

import { ProductCardView } from "@/components/chat/product-card";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

export function MessageBubble({
  message,
  onBuyNow,
  selectingProductId,
}: {
  message: ChatMessage;
  onBuyNow: (productId: string, variantId: string) => void;
  selectingProductId: string | null;
}) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex size-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted"
        )}
      >
        {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
      </div>
      <div className={cn("flex max-w-[85%] flex-col gap-3", isUser && "items-end")}>
        <div
          className={cn(
            "whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm",
            isUser ? "bg-primary text-primary-foreground" : "bg-muted"
          )}
        >
          {message.content}
        </div>
        {message.product_cards && message.product_cards.length > 0 && (
          <div className="flex w-full gap-3 overflow-x-auto pb-2">
            {message.product_cards.map((product) => (
              <ProductCardView
                key={product.product_id}
                product={product}
                onBuyNow={onBuyNow}
                isSelecting={selectingProductId === product.product_id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
