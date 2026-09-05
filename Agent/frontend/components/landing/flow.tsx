"use client";

import { Pause, Play } from "lucide-react";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

/** The four parties. Order matters — it's the horizontal axis of the diagram. */
const LANES = ["You", "Agent", "Merchant", "Razorpay"] as const;

type Step = {
  from: number;
  to: number;
  label: string;
  wire?: string;
  /** The one hop that cannot happen. */
  blocked?: boolean;
  /** Human authority: the buyer acting, not the agent. */
  human?: boolean;
};

/** One real purchase, hop by hop. Every wire here exists in the running
 *  system — the scoped catalog calls, the stock hold, the signature check. */
const STEPS: Step[] = [
  { from: 0, to: 1, label: "Find me headphones under ₹5,000", human: true },
  { from: 1, to: 2, label: "Search the catalog", wire: "GET /agent/catalog/search" },
  { from: 2, to: 1, label: "19 products, live price and stock" },
  { from: 1, to: 2, label: "Hold the stock for 15 minutes", wire: "POST /agent/reservations" },
  { from: 1, to: 0, label: "₹4,499, priced on the server. Pay appears." },
  { from: 1, to: 3, label: "No tool reaches payment", blocked: true },
  { from: 0, to: 3, label: "You press Pay, in Razorpay's own window", human: true },
  { from: 3, to: 1, label: "Signature verified on our server" },
  { from: 1, to: 2, label: "Order registered, stock decremented", wire: "POST /agent/orders" },
];

const DWELL_MS = 2200;

export function Flow() {
  const [active, setActive] = useState(0);
  // Two separate things: whether the viewer wants it running, and whether
  // the pointer is resting on it. Collapsing them into one flag meant
  // clicking a step to read it, then moving away, silently resumed and
  // threw the selection away.
  const [playing, setPlaying] = useState(true);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    if (!playing || hovered) return;
    // Someone who asked for less motion gets the whole sequence at rest,
    // still steppable by hand.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = setInterval(() => setActive((i) => (i + 1) % STEPS.length), DWELL_MS);
    return () => clearInterval(id);
  }, [playing, hovered]);

  return (
    <figure
      className="glass w-full rounded-2xl p-4 sm:p-5"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <figcaption className="sr-only">
        One purchase, hop by hop: the agent searches the merchant&apos;s catalog over a
        scoped API, holds stock, and prices the order. It has no connection to the
        payment provider — only you can authorize the payment, after which Razorpay
        reports the verified result back.
      </figcaption>

      <div className="flex items-center justify-between gap-3 pb-3">
        <p className="text-[11px] text-muted-foreground">One purchase, hop by hop</p>
        <button
          type="button"
          onClick={() => setPlaying((p) => !p)}
          data-state={playing ? "playing" : "paused"}
          aria-label={playing ? "Pause the sequence" : "Play the sequence"}
          className="grid size-6 place-items-center rounded-md text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          {playing ? <Pause className="size-3" /> : <Play className="size-3" />}
        </button>
      </div>

      <div className="min-w-0 overflow-x-auto">
        <div className="min-w-[19rem]">
          <div className="grid grid-cols-4 border-b border-border/60 pb-2">
            {LANES.map((lane, i) => (
              <span
                key={lane}
                className={cn(
                  "text-center text-[11px] font-medium transition-colors duration-200",
                  STEPS[active].from === i || STEPS[active].to === i
                    ? "text-foreground"
                    : "text-muted-foreground/70"
                )}
              >
                {lane}
              </span>
            ))}
          </div>

          <ol className="relative pt-1">
            {/* The lanes themselves, running behind every hop. */}
            <span aria-hidden="true" className="pointer-events-none absolute inset-0 grid grid-cols-4">
              {LANES.map((lane) => (
                <span key={lane} className="flex justify-center">
                  <span className="h-full w-px bg-border/70" />
                </span>
              ))}
            </span>

            {STEPS.map((step, i) => (
              <Hop
                key={step.label}
                step={step}
                index={i}
                isActive={i === active}
                onSelect={() => {
                  setActive(i);
                  setPlaying(false);
                }}
              />
            ))}
          </ol>
        </div>
      </div>

      <p className="min-h-[2.5rem] pt-3 text-[13px] leading-snug">
        <span className={cn(STEPS[active].blocked ? "text-destructive" : "text-foreground")}>
          {STEPS[active].label}
        </span>
        {STEPS[active].wire && (
          <span className="ml-2 font-mono text-[11px] text-muted-foreground">
            {STEPS[active].wire}
          </span>
        )}
      </p>
    </figure>
  );
}

function Hop({
  step,
  index,
  isActive,
  onSelect,
}: {
  step: Step;
  index: number;
  isActive: boolean;
  onSelect: () => void;
}) {
  const left = Math.min(step.from, step.to);
  const right = Math.max(step.from, step.to);
  const rightward = step.to > step.from;

  const colour = step.blocked
    ? "var(--destructive)"
    : step.human
      ? "var(--human)"
      : "var(--agent-2)";

  return (
    <li className="relative">
      <button
        type="button"
        onClick={onSelect}
        aria-current={isActive ? "step" : undefined}
        aria-label={`Step ${index + 1}: ${step.label}`}
        className="grid w-full grid-cols-4 items-center rounded-md py-[7px] focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
      >
        <span
          className="flex items-center"
          style={{ gridColumn: `${left + 1} / ${right + 2}` }}
        >
          {/* Tail dot sits on the sending lane, head on the receiving one. */}
          <Dot show={!rightward} active={isActive} colour={colour} head />
          {/* The line, with the request itself running along it while this
              hop is the live one. */}
          <span className="relative h-px flex-1">
            <span
              className={cn(
                "absolute inset-0 transition-all duration-300",
                step.blocked && "opacity-70"
              )}
              style={{
                background: step.blocked
                  ? `repeating-linear-gradient(90deg, ${colour} 0 4px, transparent 4px 9px)`
                  : colour,
                opacity: isActive ? 1 : 0.22,
              }}
            />
            {isActive && (
              <span
                aria-hidden="true"
                className={cn(
                  "packet",
                  step.blocked && "packet-blocked",
                  !step.blocked && !rightward && "packet-reverse"
                )}
                style={{ ["--packet" as string]: colour }}
              />
            )}
          </span>
          <Dot show={rightward} active={isActive} colour={colour} head />
        </span>
      </button>
    </li>
  );
}

function Dot({
  show,
  active,
  colour,
  head,
}: {
  show: boolean;
  active: boolean;
  colour: string;
  head?: boolean;
}) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "size-1.5 shrink-0 rounded-full transition-all duration-300",
        !show && "opacity-0",
        active && show && head && "scale-150"
      )}
      style={{ background: colour, opacity: show ? (active ? 1 : 0.25) : 0 }}
    />
  );
}
