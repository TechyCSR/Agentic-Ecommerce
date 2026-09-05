"use client";

import { Pause, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";

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

  /* The whole assembly tilts as one plane. A previous attempt tilted the
     cards individually and they collided; moving a single surface keeps
     every line where it was drawn. */
  const stage = useRef<HTMLDivElement>(null);

  function tilt(event: React.PointerEvent<HTMLDivElement>) {
    const el = stage.current;
    if (!el) return;
    const box = el.getBoundingClientRect();
    el.style.setProperty("--rx", `${-((event.clientY - box.top) / box.height - 0.5) * 5}deg`);
    el.style.setProperty("--ry", `${((event.clientX - box.left) / box.width - 0.5) * 6}deg`);
  }

  function level() {
    const el = stage.current;
    if (!el) return;
    el.style.setProperty("--rx", "0deg");
    el.style.setProperty("--ry", "0deg");
  }

  return (
    <div
      className="relative w-full [perspective:1800px]"
      onPointerMove={tilt}
      onPointerLeave={() => {
        level();
        setHovered(false);
      }}
      onPointerEnter={() => setHovered(true)}
    >
      <div
        ref={stage}
        className="relative rounded-[1.25rem] border border-border/60 bg-card/40 p-2.5 shadow-2xl transition-transform duration-500 ease-out sm:p-3"
        style={{
          ["--rx" as string]: "0deg",
          ["--ry" as string]: "0deg",
          transformStyle: "preserve-3d",
          transform: "rotateX(var(--rx)) rotateY(var(--ry))",
        }}
      >
        <div className="flex items-center justify-between gap-3 px-1.5 pt-1 pb-2.5">
          <h2 className="font-display text-[15px] font-semibold">Request Flow</h2>
          <button
            type="button"
            onClick={() => setPlaying((p) => !p)}
            data-state={playing ? "playing" : "paused"}
            aria-label={playing ? "Pause the sequence" : "Play the sequence"}
            className="grid size-7 place-items-center rounded-md border border-border/70 text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            {playing ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
          </button>
        </div>

        <figure className="glass w-full rounded-2xl p-4 sm:p-5">
      <figcaption className="sr-only">
        One purchase, hop by hop: the agent searches the merchant&apos;s catalog over a
        scoped API, holds stock, and prices the order. It has no connection to the
        payment provider — only you can authorize the payment, after which Razorpay
        reports the verified result back.
      </figcaption>

      <p className="pb-3 text-[11px] text-muted-foreground">
        One purchase, hop by hop — tap a step to hold it
      </p>

      <div className="min-w-0 overflow-x-auto">
        <div className="min-w-[19rem]">
          <div className="ml-6 grid grid-cols-4 border-b border-border/60 pb-2">
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

          <ol className="relative pt-1 pl-6">
            {/* The lanes themselves, running behind every hop. Inset by the
                number gutter so each lifeline stays under its heading. */}
            <span aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-0 left-6 grid grid-cols-4">
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
      </div>
    </div>
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
      {/* The step number sits outside the lanes, so it reads as an index
          rather than as another party in the conversation. */}
      <span
        aria-hidden="true"
        className={cn(
          "pointer-events-none absolute top-1/2 -left-6 w-4 -translate-y-1/2 text-right text-[10px] tabular-nums transition-colors duration-200",
          isActive ? "font-medium text-foreground" : "text-muted-foreground/50"
        )}
      >
        {index + 1}
      </span>
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
