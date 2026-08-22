# ADR 0001 — Archive immutable source responses before transformation

**Status:** Accepted

## Context

The project depends on third-party API responses that can change over time. A reproducible analysis needs to prove exactly which source payload produced each downstream row.

## Decision

Archive exact JSON response bytes under SHA-256 content-addressed object paths and record every request in `data/raw/manifest.sqlite` with endpoint, parameters, request/receipt timestamps, source URL, HTTP status, relevant headers, byte count, hash, and object path.

The ingestion layer intentionally uses raw HTTP rather than relying exclusively on generated Python model objects. The official `cfbd` client remains available for exploration and typed downstream use.

## Consequences

- Repeated identical payloads consume storage once but retain multiple request observations.
- Raw evidence can be re-parsed after schema changes.
- API provenance is inspectable without trusting notebook state.
