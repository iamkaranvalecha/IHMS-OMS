# ADR-005: REST-First; RabbitMQ Optional Later

**Status:** Accepted  
**Date:** 2026-07-04

## Context

Both upstreams expose HTTP APIs. KB-IHMS also publishes hold events via RabbitMQ.

## Decision

Phase 1–4 use REST only for orchestrator ↔ upstream communication. Event consumer is Phase 5 stretch goal.

## Consequences

- Simpler debugging and testing with synchronous flows.
- Future event-driven sync documented but not blocking MVP.
- Gateway module designed for HTTP first; consumer would be separate module.
