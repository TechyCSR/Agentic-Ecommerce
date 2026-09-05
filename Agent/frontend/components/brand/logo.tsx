import { Mark } from "@/components/brand/mark";
import { cn } from "@/lib/utils";

/**
 * The wordmark, wherever the product names itself.
 *
 * The mark itself lives in one place so the sidebar, the chat header and
 * the landing nav can't drift apart — the previous version drew its own
 * SVG with hardcoded indigo hex values, which stopped matching the moment
 * the palette moved to tokens.
 */
export { Mark as LogoMark } from "@/components/brand/mark";

export function Logo({
  className,
  markClassName,
  textClassName,
}: {
  className?: string;
  markClassName?: string;
  textClassName?: string;
}) {
  return (
    <span className={cn("flex items-center gap-2", className)}>
      <Mark className={markClassName ?? "size-7"} />
      <span className={cn("font-display text-lg font-semibold", textClassName)}>
        Agentic Commerce
      </span>
    </span>
  );
}
