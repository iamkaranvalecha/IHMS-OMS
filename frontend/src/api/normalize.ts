import type {
  ApiError,
  CatalogProduct,
  CheckoutSession,
  ObservabilityIds,
  SessionLineItem,
  SessionState,
} from "./types";

interface WireCatalogProduct {
  sku: string;
  name: string;
  ihms_product_id: string;
  ecops_item_code: string;
  unit_price: number;
  available_quantity: number | null;
  description?: string | null;
  image_url?: string | null;
  category?: string | null;
}

interface WireSessionLineItem {
  sku: string;
  name: string;
  quantity: number;
  unit_price: number;
}

interface WireSession {
  session_id: string;
  correlation_id: string;
  state: string;
  hold_id?: string | null;
  order_id?: string | null;
  expires_at?: string | null;
  customer_name?: string | null;
  line_items?: WireSessionLineItem[];
}

const SESSION_STATES: SessionState[] = [
  "CREATED",
  "HELD",
  "FULFILL_PENDING",
  "CONFIRMED",
  "ABANDONED",
  "COMPENSATED",
  "RECONCILED",
];

export function normalizeSessionState(value: string): SessionState {
  if (SESSION_STATES.includes(value as SessionState)) {
    return value as SessionState;
  }
  throw new Error(`Unknown session state: ${value}`);
}

export function normalizeCatalogProduct(raw: WireCatalogProduct): CatalogProduct {
  return {
    sku: raw.sku,
    name: raw.name,
    ihmsProductId: raw.ihms_product_id,
    ecopsItemCode: raw.ecops_item_code,
    unitPrice: raw.unit_price,
    availableQuantity: raw.available_quantity ?? null,
    description: raw.description ?? null,
    imageUrl: raw.image_url ?? null,
    category: raw.category ?? null,
  };
}

export function normalizeLineItem(raw: WireSessionLineItem): SessionLineItem {
  return {
    sku: raw.sku,
    name: raw.name,
    quantity: raw.quantity,
    unitPrice: raw.unit_price,
  };
}

export function normalizeSession(raw: WireSession): CheckoutSession {
  return {
    sessionId: raw.session_id,
    correlationId: raw.correlation_id,
    state: normalizeSessionState(raw.state),
    holdId: raw.hold_id ?? null,
    orderId: raw.order_id ?? null,
    expiresAt: raw.expires_at ?? null,
    customerName: raw.customer_name ?? null,
    lineItems: (raw.line_items ?? []).map(normalizeLineItem),
  };
}

export function observabilityFromHeaders(headers: Headers): ObservabilityIds {
  return {
    requestId: headers.get("X-Request-ID"),
    correlationId: headers.get("X-Correlation-ID"),
    traceId: headers.get("X-Trace-ID"),
  };
}

export async function parseApiError(response: Response): Promise<ApiError> {
  let detail = response.statusText;
  try {
    const body = (await response.json()) as { detail?: string | unknown };
    if (typeof body.detail === "string") {
      detail = body.detail;
    } else if (Array.isArray(body.detail)) {
      detail = body.detail.map(String).join("; ");
    }
  } catch {
    // keep statusText
  }
  const error = new Error(detail) as ApiError;
  error.status = response.status;
  error.detail = detail;
  return error;
}

export function secondsUntil(iso: string | null, now = Date.now()): number | null {
  if (!iso) {
    return null;
  }
  const expiresMs = new Date(iso).getTime();
  return Math.max(0, Math.floor((expiresMs - now) / 1000));
}

export function isHoldExpired(expiresAt: string | null, now = Date.now()): boolean {
  if (!expiresAt) {
    return false;
  }
  return new Date(expiresAt).getTime() <= now;
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(amount);
}
