"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { createApiClient } from "@/lib/api";

const STORAGE_KEY = "agentic_commerce_admin_session";

interface AdminSession {
  token: string;
  email: string;
  expiresAt: string;
}

function readStoredSession(): AdminSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AdminSession;
    if (!parsed.token || new Date(parsed.expiresAt).getTime() <= Date.now()) {
      window.sessionStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

/**
 * Admin sessions are separate from Clerk: a single operator account
 * (email/password checked against backend env vars) that can manage the
 * one central, platform-wide API key set. The token lives in
 * sessionStorage only — it's an operator tool, not a customer account.
 */
export function useAdminSession() {
  const [session, setSession] = useState<AdminSession | null>(null);
  const [ready, setReady] = useState(false);

  // sessionStorage isn't available during SSR, so reading it has to happen
  // after mount — it's syncing from an external system, not deriving state.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setSession(readStoredSession());
    setReady(true);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const login = useCallback(async (email: string, password: string) => {
    const api = createApiClient(async () => null);
    const data = await api.post<{ token: string; email: string; expires_at: string }>(
      "/api/v1/admin/login",
      { email, password }
    );
    const next: AdminSession = {
      token: data.token,
      email: data.email,
      expiresAt: data.expires_at,
    };
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSession(next);
  }, []);

  const logout = useCallback(() => {
    window.sessionStorage.removeItem(STORAGE_KEY);
    setSession(null);
  }, []);

  const api = useMemo(
    () => createApiClient(async () => session?.token ?? null),
    [session?.token]
  );

  return { session, ready, login, logout, api };
}
