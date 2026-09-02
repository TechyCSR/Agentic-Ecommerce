"use client";

import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/lib/use-api";
import type { Category } from "@/lib/types";

export function useCategories() {
  const api = useApi();

  return useQuery({
    queryKey: ["categories"],
    queryFn: () => api.get<Category[]>("/api/v1/categories"),
    staleTime: 5 * 60_000,
  });
}
