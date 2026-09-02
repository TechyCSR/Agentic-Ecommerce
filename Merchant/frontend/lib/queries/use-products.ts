"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/lib/use-api";
import type { ApiSuccess, Product, ProductImage, ProductVariant } from "@/lib/types";

export interface VariantPayload {
  sku: string;
  name: string;
  price: number;
  currency?: string;
  compare_at_price?: number | null;
  stock_quantity?: number;
  status?: string;
}

export interface ImagePayload {
  image_url: string;
  cloudinary_public_id?: string;
  alt_text?: string;
  position?: number;
  is_primary?: boolean;
}

export interface ProductPayload {
  store_id?: string;
  name: string;
  slug?: string;
  short_description?: string;
  description?: string;
  brand?: string;
  category_ids?: string[];
  status?: string;
  is_agent_searchable?: boolean;
  variants?: VariantPayload[];
  images?: ImagePayload[];
}

export interface ProductFilters {
  store_id?: string;
  status?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

function buildQuery(filters: ProductFilters) {
  const params = new URLSearchParams();
  if (filters.store_id) params.set("store_id", filters.store_id);
  if (filters.status) params.set("status", filters.status);
  if (filters.q) params.set("q", filters.q);
  if (filters.limit) params.set("limit", String(filters.limit));
  if (filters.offset) params.set("offset", String(filters.offset));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function useProducts(filters: ProductFilters) {
  const api = useApi();

  return useQuery({
    queryKey: ["products", filters],
    queryFn: () =>
      api.getWithMeta<Product[]>(`/api/v1/products${buildQuery(filters)}`) as Promise<
        ApiSuccess<Product[]>
      >,
  });
}

export function useProduct(productId: string | undefined) {
  const api = useApi();

  return useQuery({
    queryKey: ["product", productId],
    queryFn: () => api.get<Product>(`/api/v1/products/${productId}`),
    enabled: !!productId,
  });
}

export function useCreateProduct() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ProductPayload) =>
      api.post<Product>("/api/v1/products", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useUpdateProduct() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      productId,
      payload,
    }: {
      productId: string;
      payload: Partial<ProductPayload>;
    }) => api.patch<Product>(`/api/v1/products/${productId}`, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["product", variables.productId] });
    },
  });
}

export function useDeleteProduct() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (productId: string) =>
      api.delete<{ deleted: boolean }>(`/api/v1/products/${productId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useProductStatusAction() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      productId,
      action,
    }: {
      productId: string;
      action: "activate" | "deactivate" | "archive";
    }) => api.post<Product>(`/api/v1/products/${productId}/${action}`),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["product", variables.productId] });
    },
  });
}

export function useAddVariant() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      productId,
      payload,
    }: {
      productId: string;
      payload: VariantPayload;
    }) => api.post<ProductVariant>(`/api/v1/products/${productId}/variants`, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["product", variables.productId] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useUpdateVariant() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      variantId,
      payload,
    }: {
      variantId: string;
      productId: string;
      payload: Partial<VariantPayload>;
    }) =>
      api.patch<ProductVariant>(`/api/v1/products/variants/${variantId}`, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["product", variables.productId] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useDeleteVariant() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ variantId }: { variantId: string; productId: string }) =>
      api.delete<{ deleted: boolean }>(`/api/v1/products/variants/${variantId}`),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["product", variables.productId] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useAddImage() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      productId,
      payload,
    }: {
      productId: string;
      payload: ImagePayload;
    }) => api.post<ProductImage>(`/api/v1/products/${productId}/images`, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["product", variables.productId] });
    },
  });
}

export function useDeleteImage() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ productId, imageId }: { productId: string; imageId: string }) =>
      api.delete<{ deleted: boolean }>(
        `/api/v1/products/${productId}/images/${imageId}`
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["product", variables.productId] });
    },
  });
}

export function useSetPrimaryImage() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ productId, imageId }: { productId: string; imageId: string }) =>
      api.patch<ProductImage[]>(
        `/api/v1/products/${productId}/images/${imageId}/primary`
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["product", variables.productId] });
    },
  });
}
