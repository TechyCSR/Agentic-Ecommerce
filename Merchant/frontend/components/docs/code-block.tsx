import { cn } from "@/lib/utils";

export function CodeBlock({
  children,
  className,
}: {
  children: string;
  className?: string;
}) {
  return (
    <pre
      className={cn(
        "overflow-x-auto rounded-lg border bg-muted/50 p-4 text-xs leading-relaxed sm:text-sm",
        className
      )}
    >
      <code className="font-mono">{children}</code>
    </pre>
  );
}
