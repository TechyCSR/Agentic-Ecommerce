"use client";

import { Package } from "lucide-react";
import Image from "next/image";
import { useState } from "react";

import { cn } from "@/lib/utils";

/** Image with a skeleton underneath and a caller-reserved aspect ratio, so
 * nothing reflows when it loads. Sources come from the product payload that
 * already arrived with the message — never a separate lookup. */
export function ProductImage({
  src,
  alt,
  className,
  sizes = "(max-width: 768px) 60vw, 220px",
  priority = false,
}: {
  src: string | null | undefined;
  alt: string;
  className?: string;
  sizes?: string;
  priority?: boolean;
}) {
  const [loaded, setLoaded] = useState(false);

  if (!src) {
    return (
      <div className={cn("flex size-full items-center justify-center bg-muted", className)}>
        <Package className="size-7 text-muted-foreground/60" />
      </div>
    );
  }

  return (
    <div className={cn("relative size-full overflow-hidden bg-muted", className)}>
      {!loaded && <div className="absolute inset-0 animate-pulse bg-muted" />}
      <Image
        src={src}
        alt={alt}
        fill
        unoptimized
        sizes={sizes}
        priority={priority}
        loading={priority ? undefined : "lazy"}
        onLoad={() => setLoaded(true)}
        className={cn(
          "object-cover transition-opacity duration-300",
          loaded ? "opacity-100" : "opacity-0"
        )}
      />
    </div>
  );
}
