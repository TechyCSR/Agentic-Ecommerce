"use client";

import { Ban, Fingerprint, ShieldCheck, Store, Wrench } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * The hero: two services, a payment provider, and one deliberately broken wire.
 *
 * This is the actual shape of the system — a merchant that exposes its
 * catalog over a scoped API, an agent that shops it, and Razorpay taking
 * the money. The wire between the agent and the money is drawn severed
 * because that is literally true: no tool exists that reaches it. Drawing
 * the gap is the whole argument.
 *
 * Laid out with grid and CSS connectors rather than one fixed SVG, so it
 * reflows to a vertical stack on a phone instead of scaling into
 * illegibility.
 */
export function Architecture({ productCount }: { productCount?: number }) {
  return (
    <figure className="relative w-full">
      <figcaption className="sr-only">
        The merchant service exposes its catalog over a scoped API. The agent reads that
        catalog and registers orders through it, but has no connection to the payment
        provider. Only a signed-in person can authorize a payment with Razorpay, which
        then reports the verified result back to the agent.
      </figcaption>

      <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-start md:gap-0">
        <Node
          icon={Store}
          eyebrow="Merchant service"
          title="The catalog"
          detail={
            productCount
              ? `${productCount.toLocaleString("en-IN")} products, priced and counted live`
              : "Products, prices and stock, live"
          }
          tone="agent"
        />

        <Wire label="catalog:read · checkout:create" />

        <Node
          icon={Wrench}
          eyebrow="Buyer's agent"
          title="17 tools"
          detail="Searches, compares, fills a cart, prices an order"
          tone="agent"
        />
      </div>

      {/* The severed connection. Everything above is a working wire; this one
          is drawn as a gap on purpose. */}
      <div className="relative mt-4 grid gap-4 md:mt-6 md:grid-cols-[1fr_auto_1fr] md:items-center md:gap-0">
        <div className="hidden md:block" />
        <BrokenWire />
        <div className="hidden md:block" />
      </div>

      <div className="mt-4 grid gap-4 md:mt-6 md:grid-cols-[1fr_auto_1fr] md:items-start md:gap-0">
        <Node
          icon={Fingerprint}
          eyebrow="You"
          title="Press Pay"
          detail="A separate request only a signed-in person can make"
          tone="human"
        />

        <Wire label="you authorize" tone="human" />

        <Node
          icon={ShieldCheck}
          eyebrow="Razorpay"
          title="Takes the money"
          detail="Signature verified on our server before anything reads as paid"
          tone="human"
        />
      </div>
    </figure>
  );
}

function Node({
  icon: Icon,
  eyebrow,
  title,
  detail,
  tone,
}: {
  icon: React.ComponentType<{ className?: string }>;
  eyebrow: string;
  title: string;
  detail: string;
  tone: "agent" | "human";
}) {
  const accent = tone === "agent" ? "var(--agent-1)" : "var(--human)";
  return (
    <div
      className="glass rounded-2xl p-4 sm:p-5"
      style={{ borderColor: `color-mix(in oklch, ${accent}, transparent 72%)` }}
    >
      <div className="flex items-center gap-2.5">
        <span
          className="grid size-8 shrink-0 place-items-center rounded-lg"
          style={{ background: `color-mix(in oklch, ${accent}, transparent 86%)`, color: accent }}
        >
          <Icon className="size-4" />
        </span>
        <span className="text-[11px] font-medium text-muted-foreground">{eyebrow}</span>
      </div>
      <p className="font-display mt-3 text-lg leading-tight font-semibold">{title}</p>
      <p className="mt-1.5 text-[13px] leading-snug text-muted-foreground">{detail}</p>
    </div>
  );
}

/** A live connection. The travelling dashes are the only unprompted motion
 *  on the page, and the reduced-motion rule stops them. */
function Wire({ label, tone = "agent" }: { label: string; tone?: "agent" | "human" }) {
  const accent = tone === "agent" ? "var(--agent-2)" : "var(--human)";
  return (
    <div className="relative flex items-center justify-center px-2 md:h-full md:min-h-24 md:w-32 md:flex-col">
      <span
        className={cn(
          "wire-flow h-px w-full md:mt-9 md:h-px md:w-full",
        )}
        style={{ ["--wire" as string]: accent }}
        aria-hidden="true"
      />
      <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-background px-2 text-[10px] whitespace-nowrap text-muted-foreground md:top-9 md:translate-y-2">
        {label}
      </span>
    </div>
  );
}

function BrokenWire() {
  return (
    <div className="flex items-center justify-center gap-3 md:w-32">
      <span className="h-px w-8 bg-[color-mix(in_oklch,var(--foreground),transparent_80%)] md:w-6" aria-hidden="true" />
      <span
        className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] whitespace-nowrap"
        style={{
          borderColor: "color-mix(in oklch, var(--destructive), transparent 70%)",
          color: "color-mix(in oklch, var(--destructive), var(--foreground) 20%)",
        }}
      >
        <Ban className="size-3" />
        no tool reaches this
      </span>
      <span className="h-px w-8 bg-[color-mix(in_oklch,var(--foreground),transparent_80%)] md:w-6" aria-hidden="true" />
    </div>
  );
}
