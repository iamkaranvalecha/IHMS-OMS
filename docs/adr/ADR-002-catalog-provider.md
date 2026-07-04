# ADR-002: CatalogProvider Anti-Corruption Layer

**Status:** Accepted  
**Date:** 2026-07-04

## Context

KB-IHMS and EC-OPS use different product identifiers. Mapping must not leak into frozen assignment code.

## Decision

Introduce `CatalogProvider` protocol in `src/catalog/` with `JsonCatalogProvider` backed by `catalog/products.json`.

## Consequences

- Orchestrator translates SKU → `ihms_product_id` and `ecops_item_code`.
- Catalog can later swap to DB or external PIM without changing saga logic.
- Single place to update when upstream schemas diverge.
