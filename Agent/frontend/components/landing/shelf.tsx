"use client";

import { useRef } from "react";

import { ProductImage } from "@/components/chat/product-image";
import { formatMoney } from "@/lib/money";
import type { ShowcaseProduct } from "@/lib/queries/use-highlights";

/**
 * The hero's centrepiece: real catalog products, stacked in depth.
 *
 * These are the same products the agent would return — the page claims it
 * only ever shows real stock, so the hero is held to that too rather than
 * being dressed with stock photography.
 *
 * The tilt follows the pointer through two CSS custom properties rather
 * than React state: a re-render per mousemove would be the expensive way to
 * do the one thing on this page that has to stay smooth.
 */
export function Shelf({ products }: { products: ShowcaseProduct[] }) {
  const stage = useRef<HTMLDivElement>(null);

  function track(event: React.PointerEvent<HTMLDivElement>) {
    const el = stage.current;
    if (!el) return;
    const box = el.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width - 0.5;
    const y = (event.clientY - box.top) / box.height - 0.5;
    el.style.setProperty("--tilt-y", `${x * 16}deg`);
    el.style.setProperty("--tilt-x", `${-y * 12}deg`);
  }

  function release() {
    const el = stage.current;
    if (!el) return;
    el.style.setProperty("--tilt-y", "0deg");
    el.style.setProperty("--tilt-x", "0deg");
  }

  const cards = products.slice(0, 5);
  if (cards.length === 0) return <ShelfSkeleton />;

  return (
    <div
      ref={stage}
      onPointerMove={track}
      onPointerLeave={release}
      className="perspective-shelf relative mx-auto aspect-square w-full max-w-[30rem] touch-none"
      style={{ ["--tilt-x" as string]: "0deg", ["--tilt-y" as string]: "0deg" }}
      aria-hidden="true"
    >
      <div
        className="absolute inset-0 transition-transform duration-500 ease-out"
        style={{
          transformStyle: "preserve-3d",
          transform: "rotateX(var(--tilt-x)) rotateY(var(--tilt-y))",
        }}
      >
        {cards.map((product, i) => {
          // Fanned along all three axes so the stack reads as depth rather
          // than as a pile of offset rectangles.
          const depth = i * -120;
          const lift = i * -26;
          const slide = i * 42;
          return (
            <article
              key={`${product.name}-${i}`}
              className="glass absolute top-1/2 left-1/2 w-52 overflow-hidden rounded-2xl p-2 shadow-2xl sm:w-56"
              style={{
                transform: `translate3d(calc(-50% + ${slide}px), calc(-50% + ${lift}px), ${depth}px) rotateY(-18deg) rotateX(6deg)`,
                zIndex: cards.length - i,
                opacity: 1 - i * 0.12,
              }}
            >
              <div className="relative aspect-[4/3] overflow-hidden rounded-xl">
                <ProductImage src={product.image_url} alt="" sizes="224px" priority={i === 0} />
              </div>
              <div className="space-y-0.5 px-1.5 pt-2 pb-1">
                <p className="truncate text-[13px] font-medium">{product.name}</p>
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-semibold tabular-nums">
                    {product.price ? formatMoney(product.price, product.currency) : "—"}
                  </span>
                  <span className="truncate text-[11px] text-muted-foreground">
                    {product.category}
                  </span>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function ShelfSkeleton() {
  return (
    <div className="perspective-shelf relative mx-auto aspect-square w-full max-w-[30rem]" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="glass absolute top-1/2 left-1/2 w-52 rounded-2xl p-2 sm:w-56"
          style={{
            transform: `translate3d(calc(-50% + ${i * 42}px), calc(-50% + ${i * -26}px), ${i * -120}px) rotateY(-18deg) rotateX(6deg)`,
            opacity: 1 - i * 0.2,
          }}
        >
          <div className="aspect-[4/3] animate-pulse rounded-xl bg-muted" />
          <div className="mt-2 h-3 w-2/3 animate-pulse rounded bg-muted" />
          <div className="mt-1.5 h-3 w-1/3 animate-pulse rounded bg-muted" />
        </div>
      ))}
    </div>
  );
}
