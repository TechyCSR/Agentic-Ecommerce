"use client";

import Link from "next/link";

import { Shelf } from "@/components/landing/shelf";
import { Button } from "@/components/ui/button";
import { useHighlights } from "@/lib/queries/use-highlights";

export function Hero() {
  const { data } = useHighlights();

  return (
    <section className="halo relative overflow-hidden">
      <div className="relative z-10 mx-auto grid max-w-6xl items-center gap-12 px-5 py-16 sm:px-8 md:py-24 lg:grid-cols-[1.05fr_1fr] lg:gap-8">
        <div>
          <h1 className="font-display text-[2.6rem] leading-[1.03] font-semibold text-balance sm:text-6xl">
            Seventeen tools. None of them can spend your money.
          </h1>

          <p className="mt-6 max-w-[46ch] text-[15px] leading-relaxed text-muted-foreground sm:text-base">
            Ask in plain words. The agent searches a real catalog, compares what it finds,
            holds the stock and prices your order. Pressing Pay stays yours — not because
            it is asked to stop, but because it has no way to start.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            {/* Deliberately the same for everyone: signed-out visitors are
                sent to sign in and land back here, so this never waits on
                auth to resolve. */}
            <Button size="lg" className="h-11 px-5 text-[15px]" render={<Link href="/chat">Start shopping</Link>} />
            <Button
              variant="outline"
              size="lg"
              className="h-11 px-5 text-[15px]"
              render={<Link href="#boundary">How the boundary works</Link>}
            />
          </div>

          {data && data.category_count > 0 && (
            <p className="mt-8 text-sm text-muted-foreground">
              Live right now:{" "}
              <span className="font-medium text-foreground tabular-nums">{data.category_count}</span>{" "}
              shelves stocked by{" "}
              <span className="font-medium text-foreground tabular-nums">{data.brand_count}</span>{" "}
              real brands, priced in rupees.
            </p>
          )}
        </div>

        <Shelf products={data?.showcase ?? []} />
      </div>
    </section>
  );
}
