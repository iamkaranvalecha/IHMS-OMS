# ADR-001: Separate checkout-orchestrator Repository

**Status:** Accepted  
**Date:** 2026-07-04

## Context

KB-IHMS (.NET hold microservice) and EC-OPS (FastAPI OMS) are frozen assignment repos. Integration requires saga coordination, catalog mapping, BFF API, and UI — none of which belong in either upstream.

## Decision

Create a dedicated repository ([IHMS-OMS](https://github.com/iamkaranvalecha/IHMS-OMS) / checkout-orchestrator) that owns all integration logic.

## Consequences

- Upstream repos remain untouched except cross-repo documentation links.
- Integration evolution (saga, reconciliation, observability) happens in one place.
- Portfolio clearly shows three-repo distributed checkout platform.
