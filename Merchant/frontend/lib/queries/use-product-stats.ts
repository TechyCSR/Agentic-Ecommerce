"use client";

import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/lib/use-api";

export interface ProductStats {
  total_products: number;
  active_products: number;
  out_of_stock_products: number;
  total_inventory: number;
}

export function useProductStats() {
  const api = useApi();

  return useQuery({
    queryKey: ["product-stats"],
    queryFn: () => api.get<ProductStats>("/api/v1/products/stats"),
  });
}
