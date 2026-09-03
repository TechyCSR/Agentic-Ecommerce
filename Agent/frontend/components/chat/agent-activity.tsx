"use client";

import { AlertCircle, Check, ChevronRight, Package, Search, Sparkles } from "lucide-react";
import { useState } from "react";

import { formatMoney } from "@/lib/money";
import type { ActivityStep, ToolArgs } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEP_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  search_catalog: Search,
  get_product_details: Package,
};

/** Turns raw tool args into the few lines a shopper actually understands. */
function readableArgs(args: ToolArgs): [string, string][] {
  const rows: [string, string][] = [];
  const push = (label: string, value: unknown) => {
    if (value === undefined || value === null || value === "") return;
    rows.push([label, String(value)]);
  };

  push("Search", args.q);
  push("Category", args.category);
  push("Brand", args.brand);
  if (typeof args.min_price === "number" && typeof args.max_price === "number") {
    rows.push([
      "Budget",
      `${formatMoney(args.min_price)} – ${formatMoney(args.max_price)}`,
    ]);
  } else if (typeof args.max_price === "number") {
    rows.push(["Budget", `Under ${formatMoney(args.max_price)}`]);
  } else if (typeof args.min_price === "number") {
    rows.push(["Budget", `Over ${formatMoney(args.min_price)}`]);
  }
  if (args.in_stock === true) rows.push(["Availability", "In stock only"]);

  return rows;
}

function StepIcon({ step }: { step: ActivityStep }) {
  if (step.status === "error") {
    return <AlertCircle className="size-3.5 text-destructive" />;
  }
  if (step.status === "done") {
    return <Check className="size-3.5 text-primary" />;
  }
  const Icon = (step.tool && STEP_ICONS[step.tool]) || Sparkles;
  return <Icon className="size-3.5 text-muted-foreground" />;
}

function ActivityRow({ step }: { step: ActivityStep }) {
  const [open, setOpen] = useState(false);
  const rows = step.args ? readableArgs(step.args) : [];
  const expandable = rows.length > 0 || step.resultCount !== undefined;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-1 duration-300">
      <button
        type="button"
        disabled={!expandable}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "group flex w-full items-center gap-2 rounded-md px-1.5 py-1 text-left text-xs transition-colors",
          expandable && "hover:bg-muted/60",
          !expandable && "cursor-default"
        )}
      >
        <span className="relative flex size-4 shrink-0 items-center justify-center">
          {step.status === "running" && (
            <span className="absolute inline-flex size-4 animate-ping rounded-full bg-primary/25" />
          )}
          <StepIcon step={step} />
        </span>

        <span className={cn("truncate", step.status === "running" ? "text-foreground" : "text-muted-foreground")}>
          {step.label}
        </span>

        {step.detail && (
          <span className="truncate text-muted-foreground/80">· {step.detail}</span>
        )}

        {expandable && (
          <ChevronRight
            className={cn(
              "ml-auto size-3 shrink-0 text-muted-foreground transition-transform duration-200",
              open && "rotate-90"
            )}
          />
        )}
      </button>

      {open && rows.length > 0 && (
        <dl className="animate-in fade-in slide-in-from-top-1 mt-1 ml-7 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 border-l pl-3 text-xs duration-200">
          {rows.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="truncate text-foreground">{value}</dd>
            </div>
          ))}
          {step.resultCount !== undefined && (
            <div className="contents">
              <dt className="text-muted-foreground">Results</dt>
              <dd className="text-foreground">
                {step.resultCount} product{step.resultCount === 1 ? "" : "s"} found
              </dd>
            </div>
          )}
        </dl>
      )}
    </div>
  );
}

export function AgentActivity({ steps }: { steps: ActivityStep[] }) {
  if (steps.length === 0) return null;

  return (
    <div className="w-fit min-w-56 max-w-full space-y-0.5 rounded-xl border bg-muted/30 p-1.5 backdrop-blur-sm">
      {steps.map((step) => (
        <ActivityRow key={step.id} step={step} />
      ))}
    </div>
  );
}
