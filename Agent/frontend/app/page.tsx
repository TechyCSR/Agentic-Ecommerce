import { Check, Lock } from "lucide-react";
import Link from "next/link";

import { Mark } from "@/components/brand/mark";
import { Hero } from "@/components/landing/hero";
import { Shelves } from "@/components/landing/shelves";
import { SiteNav } from "@/components/landing/site-nav";
import { Button } from "@/components/ui/button";

/** What the agent does without being asked twice. */
const AGENT_CAN = [
  "Search a live catalog and compare what it finds",
  "Check the real price and stock before it answers",
  "Fill your cart and hold the stock while you decide",
  "Save an address and price the order",
  "Cancel an order and refund it in full",
  "Read back the true status of a payment",
];

export default function LandingPage() {
  return (
    <div className="min-h-dvh">
      <SiteNav />

      <main>
        <Hero />

        <section id="boundary" className="border-t border-border/60 bg-muted/25">
          <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 md:py-24">
            <h2 className="font-display max-w-[20ch] text-3xl font-semibold text-balance sm:text-4xl">
              The agent stops at your wallet
            </h2>
            <p className="mt-4 max-w-[56ch] text-[15px] leading-relaxed text-muted-foreground">
              Most assistants are told not to spend your money. This one cannot. There is
              no tool that authorizes, captures or confirms a payment, so no amount of
              persuasion reaches one.
            </p>

            <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-border/70 bg-border/70 md:grid-cols-[1.4fr_1fr]">
              <div className="bg-background p-6 sm:p-8">
                <h3 className="text-sm font-semibold">What it does on its own</h3>
                <ul className="mt-5 space-y-3">
                  {AGENT_CAN.map((item) => (
                    <li key={item} className="flex gap-3 text-[15px] leading-snug">
                      <Check className="mt-0.5 size-4 shrink-0 text-[var(--agent-2)]" />
                      <span className="text-muted-foreground">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* The one place the warm accent appears. It marks human
                  authority, so using it decoratively anywhere else would
                  dissolve the only distinction this page is making. */}
              <div className="relative bg-background p-6 sm:p-8">
                <div
                  className="absolute inset-y-0 left-0 w-px"
                  style={{ background: "linear-gradient(180deg,transparent,var(--human),transparent)" }}
                  aria-hidden="true"
                />
                <h3 className="text-sm font-semibold">What only you can do</h3>
                <div className="mt-5 flex items-start gap-3">
                  <Lock className="mt-0.5 size-4 shrink-0 text-[var(--human)]" />
                  <div>
                    <p className="text-[15px] leading-snug">Authorize the payment</p>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                      A separate request only a signed-in person can make. It opens
                      Razorpay&apos;s own window, and the amount comes from the server,
                      never from anything the agent wrote.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-border/60">
          <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 md:py-20">
            <h2 className="font-display max-w-[22ch] text-3xl font-semibold text-balance sm:text-4xl">
              It can only show you what is actually on the shelf
            </h2>
            <p className="mt-4 max-w-[56ch] text-[15px] leading-relaxed text-muted-foreground">
              Every product card is built from a catalog lookup, never from the model&apos;s
              own prose. If a search returns nothing, it says so and tells you what is
              stocked instead.
            </p>
            <Shelves />
          </div>
        </section>

        <section className="border-t border-border/60 bg-muted/25">
          <div className="mx-auto max-w-6xl px-5 py-16 text-center sm:px-8">
            <h2 className="font-display text-3xl font-semibold text-balance sm:text-4xl">
              Tell it what you need
            </h2>
            <div className="mt-7 flex justify-center">
              <Button size="lg" className="h-11 px-6 text-[15px]" render={<Link href="/chat">Start shopping</Link>} />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border/60">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-5 py-8 text-sm text-muted-foreground sm:flex-row sm:px-8">
          <div className="flex items-center gap-2.5">
            <Mark className="size-6" />
            <span>Agentic Commerce</span>
          </div>
          <p>Payments run in Razorpay test mode.</p>
        </div>
      </footer>
    </div>
  );
}
