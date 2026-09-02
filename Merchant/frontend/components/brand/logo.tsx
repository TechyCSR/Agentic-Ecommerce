import { useId } from "react";

import { cn } from "@/lib/utils";

/**
 * The icon mark: a package outline (commerce) with a solid agent node at
 * its center and a satellite node above it (the agent reaching in).
 */
export function LogoMark({ className }: { className?: string }) {
  const gradientId = useId();

  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={cn("size-7 shrink-0", className)}
      aria-hidden="true"
    >
      <rect width="32" height="32" rx="9" fill={`url(#${gradientId})`} />
      <path
        d="M16 7.5 22.5 11v10L16 24.5 9.5 21V11L16 7.5Z"
        stroke="white"
        strokeOpacity="0.6"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <circle cx="16" cy="16" r="3" fill="white" />
      <circle cx="16" cy="7.5" r="1.5" fill="white" />
      <defs>
        <linearGradient
          id={gradientId}
          x1="0"
          y1="0"
          x2="32"
          y2="32"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#6366f1" />
          <stop offset="1" stopColor="#7c3aed" />
        </linearGradient>
      </defs>
    </svg>
  );
}

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
      <LogoMark className={markClassName} />
      <span
        className={cn(
          "text-lg font-semibold tracking-tight",
          textClassName
        )}
      >
        Agentic Commerce
      </span>
    </span>
  );
}
