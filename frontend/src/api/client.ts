import {
  normalizeCatalogProduct,
  normalizeSession,
  observabilityFromHeaders,
  parseApiError,
} from "./normalize";
import type { ApiResult, CatalogProduct, CheckoutSession } from "./types";

function apiBaseUrl(): string {
  const base = import.meta.env.VITE_API_URL;
  if (!base) {
    return "";
  }
  return base.replace(/\/$/, "");
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiResult<T>> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const observability = observabilityFromHeaders(response.headers);
  if (!response.ok) {
    throw await parseApiError(response);
  }
  const data = (await response.json()) as T;
  return { data, observability };
}

export async function fetchCatalog(): Promise<ApiResult<CatalogProduct[]>> {
  const result = await requestJson<unknown[]>("/catalog");
  return {
    observability: result.observability,
    data: result.data.map((item) => normalizeCatalogProduct(item as never)),
  };
}

export async function createSession(): Promise<ApiResult<CheckoutSession>> {
  const result = await requestJson<{ session_id: string; correlation_id: string; state: string }>(
    "/sessions",
    { method: "POST", body: JSON.stringify({}) },
  );
  return {
    observability: result.observability,
    data: normalizeSession({
      session_id: result.data.session_id,
      correlation_id: result.data.correlation_id,
      state: result.data.state,
    }),
  };
}

export async function fetchSession(sessionId: string): Promise<ApiResult<CheckoutSession>> {
  const result = await requestJson<unknown>(`/sessions/${sessionId}`);
  return {
    observability: result.observability,
    data: normalizeSession(result.data as never),
  };
}

export async function placeHold(
  sessionId: string,
  payload: { sku: string; quantity: number; customerName: string },
): Promise<ApiResult<CheckoutSession>> {
  const result = await requestJson<unknown>(`/sessions/${sessionId}/hold`, {
    method: "POST",
    body: JSON.stringify({
      sku: payload.sku,
      quantity: payload.quantity,
      customer_name: payload.customerName,
    }),
  });
  return {
    observability: result.observability,
    data: normalizeSession(result.data as never),
  };
}

export async function confirmSession(
  sessionId: string,
  idempotencyKey: string,
): Promise<ApiResult<CheckoutSession>> {
  const result = await requestJson<unknown>(`/sessions/${sessionId}/confirm`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({}),
  });
  return {
    observability: result.observability,
    data: normalizeSession(result.data as never),
  };
}

export async function abandonSession(sessionId: string): Promise<ApiResult<CheckoutSession>> {
  const result = await requestJson<unknown>(`/sessions/${sessionId}`, { method: "DELETE" });
  return {
    observability: result.observability,
    data: normalizeSession(result.data as never),
  };
}

export async function fetchHealth(): Promise<ApiResult<{ status: string }>> {
  return requestJson<{ status: string }>("/health");
}
