"use client";

import { useQuery } from "@tanstack/react-query";

import { API_URL } from "@/lib/api";

export interface ShowcaseProduct {
  name: string;
  brand: string | null;
  category: string;
  image_url: string;
  price: number | null;
  currency: string;
}

export interface CatalogHighlights {
  showcase: ShowcaseProduct[];
  categories: { name: string; product_count: number }[];
  starter_categories: string[];
  brands: string[];
  category_count: number;
  brand_count: number;
}

const EMPTY: CatalogHighlights = {
  showcase: [],
  categories: [],
  starter_categories: [],
  brands: [],
  category_count: 0,
  brand_count: 0,
};

/**
 * Live catalog facts, used wherever the UI talks about what's in stock.
 *
 * Public and unauthenticated, so the landing page can state real numbers
 * before anyone signs in. Falls back to empty rather than throwing: the copy
 * around it is written to still make sense with nothing to show.
 */
export function useHighlights() {
  return useQuery({
    queryKey: ["catalog-highlights"],
    queryFn: async (): Promise<CatalogHighlights> => {
      const res = await fetch(`${API_URL}/api/v1/catalog/highlights`);
      if (!res.ok) return EMPTY;
      const body = await res.json();
      return (body?.data as CatalogHighlights) ?? EMPTY;
    },
    staleTime: 5 * 60_000,
    retry: 1,
  });
}
