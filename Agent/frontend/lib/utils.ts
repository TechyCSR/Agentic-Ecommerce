import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Buckets items with an `updated_at`/date field into ChatGPT-style
 * sidebar groups, preserving each bucket's incoming order. */
export function groupByRecency<T>(items: T[], getDate: (item: T) => string): [string, T[]][] {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const oneDay = 24 * 60 * 60 * 1000;

  const buckets: Record<string, T[]> = {
    Today: [],
    Yesterday: [],
    "Previous 7 days": [],
    Older: [],
  };

  for (const item of items) {
    const t = new Date(getDate(item)).getTime();
    const diffDays = Math.floor((startOfToday - t) / oneDay);
    if (diffDays <= 0) buckets["Today"].push(item);
    else if (diffDays === 1) buckets["Yesterday"].push(item);
    else if (diffDays <= 7) buckets["Previous 7 days"].push(item);
    else buckets["Older"].push(item);
  }

  return Object.entries(buckets).filter(([, items]) => items.length > 0);
}
