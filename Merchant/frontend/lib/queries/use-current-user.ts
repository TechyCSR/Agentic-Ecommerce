"use client";

import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/lib/use-api";
import type { User } from "@/lib/types";

export function useCurrentUser() {
  const api = useApi();

  return useQuery({
    queryKey: ["current-user"],
    queryFn: () => api.get<User>("/api/v1/auth/me"),
  });
}
