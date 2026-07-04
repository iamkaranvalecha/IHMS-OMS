# ADR-003: Product Mapping Not in EC-OPS or IHMS

**Status:** Accepted  
**Date:** 2026-07-04

## Context

Both upstream repos are frozen assignments. Adding cross-system SKU mapping would violate assignment boundaries and couple unrelated codebases.

## Decision

All product mapping lives exclusively in checkout-orchestrator (`catalog/` module).

## Consequences

- No PRs to KB-IHMS or EC-OPS for mapping tables.
- Demo catalog is version-controlled JSON; production would use external catalog service.
