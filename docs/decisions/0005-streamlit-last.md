# ADR 0005 — Build the platform and written analysis before Streamlit

**Status:** Accepted

## Context

A polished dashboard can hide weak source provenance, unresolved identities, leakage, or underpowered inference.

## Decision

Streamlit is the final presentation layer. The required deliverables before UI work are: immutable ingestion, tested entity resolution, labeled evaluation, point-in-time feature tables, negative control, reproducible analysis, ADRs, and a written methods/results narrative.

## Consequences

UI work cannot become a substitute for analytical validity. The eventual app will read certified Gold outputs rather than contain business logic that exists only in the presentation layer.
