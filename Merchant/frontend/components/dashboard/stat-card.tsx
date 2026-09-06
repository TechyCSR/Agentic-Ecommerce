import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  hint?: string;
  /** Money received. The warm accent means the same on both sides of the
   *  product — the buyer's Pay button and the revenue it produced — so it
   *  stays off every other tile. */
  money?: boolean;
}

export function StatCard({ title, value, icon: Icon, hint, money }: StatCardProps) {
  return (
    <Card
      className={money ? "border-[color-mix(in_oklch,var(--human),transparent_65%)]" : undefined}
    >
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className={cn("size-4", money ? "text-[var(--human)]" : "text-muted-foreground")} />
      </CardHeader>
      <CardContent>
        <div className="font-display text-2xl font-semibold tabular-nums">{value}</div>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}
