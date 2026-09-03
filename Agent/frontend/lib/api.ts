import type { ApiFailure, ApiSuccess } from "@/lib/types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

export class ApiRequestError extends Error {
  code: string;
  status: number;
  details?: unknown;

  constructor(message: string, code: string, status: number, details?: unknown) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

type GetToken = () => Promise<string | null>;

async function request<T>(
  path: string,
  getToken: GetToken,
  options: RequestInit = {}
): Promise<T> {
  const token = await getToken();

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  const body = (await res.json().catch(() => null)) as
    | ApiSuccess<T>
    | ApiFailure
    | null;

  if (!res.ok || !body || body.success === false) {
    const failure = body as ApiFailure | null;
    throw new ApiRequestError(
      failure?.error?.message || "Something went wrong",
      failure?.error?.code || "UNKNOWN_ERROR",
      res.status,
      failure?.error?.details
    );
  }

  return (body as ApiSuccess<T>).data;
}

async function requestFull<T>(
  path: string,
  getToken: GetToken,
  options: RequestInit = {}
): Promise<ApiSuccess<T>> {
  const token = await getToken();

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  const body = (await res.json().catch(() => null)) as
    | ApiSuccess<T>
    | ApiFailure
    | null;

  if (!res.ok || !body || body.success === false) {
    const failure = body as ApiFailure | null;
    throw new ApiRequestError(
      failure?.error?.message || "Something went wrong",
      failure?.error?.code || "UNKNOWN_ERROR",
      res.status,
      failure?.error?.details
    );
  }

  return body as ApiSuccess<T>;
}

export function createApiClient(getToken: GetToken) {
  return {
    get: <T>(path: string) => request<T>(path, getToken, { method: "GET" }),
    getWithMeta: <T>(path: string) =>
      requestFull<T>(path, getToken, { method: "GET" }),
    post: <T>(path: string, body?: unknown) =>
      request<T>(path, getToken, {
        method: "POST",
        body: body !== undefined ? JSON.stringify(body) : undefined,
      }),
    patch: <T>(path: string, body?: unknown) =>
      request<T>(path, getToken, {
        method: "PATCH",
        body: body !== undefined ? JSON.stringify(body) : undefined,
      }),
    delete: <T>(path: string) => request<T>(path, getToken, { method: "DELETE" }),
  };
}

export type ApiClientInstance = ReturnType<typeof createApiClient>;
