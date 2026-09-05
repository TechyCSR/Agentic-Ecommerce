"use client";

import { Ban, Pause, Play, RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/** The four parties. Order matters — it's the horizontal axis of the diagram. */
const LANES = ["You", "Agent", "Merchant", "Razorpay"] as const;

type Kind = "ask" | "tool" | "reply" | "human" | "blocked";

type Step = {
  from: number;
  to: number;
  kind: Kind;
  label: string;
  /** The agent's own tool, where one is doing the work. Named because the
   *  claim this page makes is about which tools exist, not which URLs do. */
  tool?: string;
};

/** One real purchase, hop by hop. Every tool named here is in the agent's
 *  actual tool list; the gap at step 6 is the one that isn't. */
const STEPS: Step[] = [
  { from: 0, to: 1, kind: "ask", label: "Find me headphones under ₹5,000" },
  { from: 1, to: 2, kind: "tool", tool: "search_catalog", label: "Turns the need into constraints and searches" },
  { from: 2, to: 1, kind: "reply", label: "19 products, live price and stock" },
  { from: 1, to: 2, kind: "tool", tool: "prepare_checkout", label: "Prices the order and holds the stock for 15 minutes" },
  { from: 1, to: 0, kind: "reply", label: "₹4,499, computed on the server. A Pay button appears." },
  { from: 1, to: 3, kind: "blocked", label: "No tool exists that reaches payment" },
  { from: 0, to: 3, kind: "human", label: "You press Pay, in Razorpay's own window" },
  { from: 3, to: 1, kind: "reply", label: "Signature verified on our server" },
  { from: 1, to: 2, kind: "tool", tool: "sync order", label: "Order registered, stock comes down" },
];

const DWELL_MS = 2400;

/** number | lanes | description. Shared by the header, the lane overlay and
 *  every row, so the lifelines stay under their own headings. */
const ROW = "grid grid-cols-[1.25rem_minmax(8.5rem,1fr)_minmax(0,1.5fr)] items-center gap-x-3";

function colourFor(kind: Kind) {
  if (kind === "blocked") return "var(--destructive)";
  if (kind === "human" || kind === "ask") return "var(--human)";
  return "var(--agent-2)";
}

export function Flow() {
  const [active, setActive] = useState(0);
  const [playing, setPlaying] = useState(true);

  useEffect(() => {
    if (!playing) return;
    // Anyone who asked for less motion gets the sequence at rest, still
    // steppable by hand.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = setInterval(() => setActive((i) => (i + 1) % STEPS.length), DWELL_MS);
    return () => clearInterval(id);
  }, [playing]);

  // Tilts as one plane. Tilting the cards individually is what made an
  // earlier version of this hero slide over its own text.
  const stage = useRef<HTMLDivElement>(null);

  function tilt(event: React.PointerEvent<HTMLDivElement>) {
    const el = stage.current;
    if (!el) return;
    const box = el.getBoundingClientRect();
    el.style.setProperty("--rx", `${-((event.clientY - box.top) / box.height - 0.5) * 4}deg`);
    el.style.setProperty("--ry", `${((event.clientX - box.left) / box.width - 0.5) * 5}deg`);
  }

  function level() {
    const el = stage.current;
    if (!el) return;
    el.style.setProperty("--rx", "0deg");
    el.style.setProperty("--ry", "0deg");
  }

  const current = STEPS[active];

  return (
    <div className="relative w-full [perspective:1800px]" onPointerMove={tilt} onPointerLeave={level}>
      <div
        ref={stage}
        className="relative rounded-[1.25rem] border border-border/60 bg-card/40 p-2.5 shadow-2xl transition-transform duration-500 ease-out sm:p-3"
        style={{
          ["--rx" as string]: "0deg",
          ["--ry" as string]: "0deg",
          transform: "rotateX(var(--rx)) rotateY(var(--ry))",
        }}
      >
        <div className="flex items-center justify-between gap-3 px-1.5 pt-1 pb-2.5">
          <div>
            <h2 className="font-display text-[15px] leading-none font-semibold">Request Flow</h2>
            <p className="mt-1 text-[11px] text-muted-foreground">
              One purchase, hop by hop — tap a step to hold it
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] tabular-nums text-muted-foreground">
              {active + 1}/{STEPS.length}
            </span>
            <button
              type="button"
              onClick={() => {
                // Pressing play from the last step restarts rather than
                // looping invisibly to the top.
                if (!playing && active === STEPS.length - 1) setActive(0);
                setPlaying((p) => !p);
              }}
              aria-label={playing ? "Pause the sequence" : "Play the sequence"}
              className="grid size-7 place-items-center rounded-md border border-border/70 text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >
              {playing ? (
                <Pause className="size-3.5" />
              ) : active === STEPS.length - 1 ? (
                <RotateCcw className="size-3.5" />
              ) : (
                <Play className="size-3.5" />
              )}
            </button>
          </div>
        </div>

        <figure className="glass w-full rounded-2xl p-3 sm:p-4">
          <figcaption className="sr-only">
            One purchase, hop by hop: the agent searches the merchant&apos;s catalog over a
            scoped API and holds stock, but has no tool that reaches the payment provider.
            Only you can authorize the payment, after which Razorpay reports the verified
            result back.
          </figcaption>

          <div className="min-w-0 overflow-x-auto">
            <div className="min-w-[26rem]">
              <div className={cn(ROW, "border-b border-border/60 pb-2")}>
                <span />
                <span className="grid grid-cols-4">
                  {LANES.map((lane, i) => (
                    <span
                      key={lane}
                      className={cn(
                        "text-center text-[11px] font-medium transition-colors duration-200",
                        current.from === i || current.to === i
                          ? "text-foreground"
                          : "text-muted-foreground/60"
                      )}
                    >
                      {lane}
                    </span>
                  ))}
                </span>
                <span />
              </div>

              <ol className="relative pt-1">
                {/* Lifelines, running behind every hop and only under the
                    lane column. */}
                <span aria-hidden="true" className={cn(ROW, "pointer-events-none absolute inset-0")}>
                  <span />
                  <span className="grid h-full grid-cols-4">
                    {LANES.map((lane) => (
                      <span key={lane} className="flex justify-center">
                        <span className="h-full w-px bg-border/70" />
                      </span>
                    ))}
                  </span>
                  <span />
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
  const colour = colourFor(step.kind);

  return (
    <li className="relative">
      <button
        type="button"
        onClick={onSelect}
        aria-current={isActive ? "step" : undefined}
        aria-label={`Step ${index + 1}: ${step.label}`}
        className={cn(
          ROW,
          "w-full rounded-lg py-2 text-left transition-colors duration-200",
          isActive ? "bg-foreground/[0.04]" : "hover:bg-foreground/[0.02]",
          "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        )}
      >
        <span
          className={cn(
            "text-right text-[10px] tabular-nums transition-colors duration-200",
            isActive ? "font-medium text-foreground" : "text-muted-foreground/50"
          )}
        >
          {index + 1}
        </span>

        <span className="grid grid-cols-4 items-center">
          <span className="flex items-center" style={{ gridColumn: `${left + 1} / ${right + 2}` }}>
            <Dot show={!rightward} active={isActive} colour={colour} />
            <span className="relative h-px flex-1">
              <span
                className="absolute inset-0 transition-opacity duration-300"
                style={{
                  background:
                    step.kind === "blocked"
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
                    step.kind === "blocked" && "packet-blocked",
                    step.kind !== "blocked" && !rightward && "packet-reverse"
                  )}
                  style={{ ["--packet" as string]: colour }}
                />
              )}
            </span>
            <Dot show={rightward} active={isActive} colour={colour} />
          </span>
        </span>

        <span className="min-w-0">
          <span
            className={cn(
              "block text-[11px] leading-snug transition-colors duration-200",
              isActive ? "text-foreground" : "text-muted-foreground/70"
            )}
          >
            {step.label}
          </span>
          {step.kind === "blocked" ? (
            <span
              className="mt-1 inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[10px]"
              style={{
                borderColor: `color-mix(in oklch, ${colour}, transparent ${isActive ? "50%" : "78%"})`,
                color: isActive ? colour : "var(--muted-foreground)",
              }}
            >
              <Ban className="size-2.5" />
              no such tool
            </span>
          ) : step.tool ? (
            <span
              className="mt-1 inline-block rounded border px-1.5 py-0.5 font-mono text-[10px]"
              style={{
                borderColor: `color-mix(in oklch, ${colour}, transparent ${isActive ? "55%" : "80%"})`,
                color: isActive ? "var(--foreground)" : "var(--muted-foreground)",
              }}
            >
              {step.tool}
            </span>
          ) : null}
        </span>
      </button>
    </li>
  );
}

function Dot({ show, active, colour }: { show: boolean; active: boolean; colour: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "size-1.5 shrink-0 rounded-full transition-transform duration-300",
        active && show && "scale-150"
      )}
      style={{ background: colour, opacity: show ? (active ? 1 : 0.25) : 0 }}
    />
  );
}
