"use client";

import { useUser } from "@clerk/nextjs";
import { useEffect, useRef } from "react";

import { useApi } from "@/lib/use-api";

/**
 * Registers the signed-in buyer's email with the backend once per session.
 *
 * The backend verifies Clerk JWTs but never calls Clerk's API, so it has no
 * other way to answer "which account owns this email?" — which Telegram's
 * `/login <email>` needs. Renders nothing.
 */
export function ProfileSync() {
  const { isSignedIn, user } = useUser();
  const api = useApi();
  const syncedFor = useRef<string | null>(null);

  useEffect(() => {
    const email = user?.primaryEmailAddress?.emailAddress;
    if (!isSignedIn || !email || syncedFor.current === email) return;
    syncedFor.current = email;

    api
      .post("/api/v1/chat/me", { email, display_name: user?.fullName ?? undefined })
      // Best-effort: failing to register an email must never block the chat.
      .catch(() => {
        syncedFor.current = null;
      });
  }, [isSignedIn, user, api]);

  return null;
}
