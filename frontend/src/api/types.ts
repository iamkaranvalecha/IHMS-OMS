/** Normalized orchestrator domain types (UI-facing). */

export type SessionState =
  | "CREATED"
  | "HELD"
  | "CONFIRMED"
  | "ABANDONED"
  | "COMPENSATED"
  | "RECONCILED";

export interface CatalogProduct {
  sku: string;
  name: string;
  ihmsProductId: string;
  ecopsItemCode: string;
  unitPrice: number;
  availableQuantity: number;
}

export interface SessionLineItem {
  sku: string;
  name: string;
  quantity: number;
  unitPrice: number;
}

export interface CheckoutSession {
  sessionId: string;
  correlationId: string;
  state: SessionState;
  holdId: string | null;
  orderId: string | null;
  expiresAt: string | null;
  customerName: string | null;
  lineItems: SessionLineItem[];
}

export interface ObservabilityIds {
  requestId: string | null;
  correlationId: string | null;
  traceId: string | null;
}

export interface ApiResult<T> {
  data: T;
  observability: ObservabilityIds;
}

export interface CartItem {
  sku: string;
  name: string;
  unitPrice: number;
  quantity: number;
  maxQuantity: number;
}

export interface ApiError extends Error {
  status: number;
  detail: string;
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof Error && "status" in error && "detail" in error;
}
