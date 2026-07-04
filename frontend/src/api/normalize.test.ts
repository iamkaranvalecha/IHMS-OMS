import { describe, expect, it } from "vitest";

import {
  formatCurrency,
  isHoldExpired,
  normalizeCatalogProduct,
  normalizeSession,
  normalizeSessionState,
  secondsUntil,
} from "./normalize";

describe("normalizeCatalogProduct", () => {
  it("maps wire snake_case to UI camelCase", () => {
    const product = normalizeCatalogProduct({
      sku: "WIDGET-001",
      name: "Widget",
      ihms_product_id: "prod-1",
      ecops_item_code: "WIDGET-001",
      unit_price: 19.99,
    });
    expect(product).toEqual({
      sku: "WIDGET-001",
      name: "Widget",
      ihmsProductId: "prod-1",
      ecopsItemCode: "WIDGET-001",
      unitPrice: 19.99,
    });
  });
});

describe("normalizeSession", () => {
  it("maps session wire payload", () => {
    const session = normalizeSession({
      session_id: "abc",
      correlation_id: "corr-1",
      state: "HELD",
      hold_id: "hold-1",
      expires_at: "2026-07-04T15:00:00Z",
      line_items: [{ sku: "WIDGET-001", name: "Widget", quantity: 1, unit_price: 19.99 }],
    });
    expect(session.sessionId).toBe("abc");
    expect(session.state).toBe("HELD");
    expect(session.lineItems[0]?.unitPrice).toBe(19.99);
  });
});

describe("normalizeSessionState", () => {
  it("throws on unknown state", () => {
    expect(() => normalizeSessionState("UNKNOWN")).toThrow();
  });
});

describe("secondsUntil", () => {
  it("returns remaining seconds", () => {
    const now = Date.parse("2026-07-04T14:00:00Z");
    expect(secondsUntil("2026-07-04T14:01:30Z", now)).toBe(90);
  });

  it("returns zero when expired", () => {
    const now = Date.parse("2026-07-04T14:02:00Z");
    expect(secondsUntil("2026-07-04T14:01:00Z", now)).toBe(0);
  });
});

describe("isHoldExpired", () => {
  it("detects expiry", () => {
    const now = Date.parse("2026-07-04T14:02:00Z");
    expect(isHoldExpired("2026-07-04T14:01:00Z", now)).toBe(true);
    expect(isHoldExpired("2026-07-04T14:03:00Z", now)).toBe(false);
  });
});

describe("formatCurrency", () => {
  it("formats USD", () => {
    expect(formatCurrency(19.99)).toMatch(/19\.99/);
  });
});
