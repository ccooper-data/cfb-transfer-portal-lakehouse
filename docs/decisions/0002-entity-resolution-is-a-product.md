# ADR 0002 — Treat portal-to-player identity resolution as a measured product

**Status:** Accepted

## Context

Portal rows lack the stable player identifier needed to join rosters and production. Names are not keys. Nicknames, suffixes, same-name collisions, withdrawals, and roster non-appearance make a simple string join indefensible.

## Decision

Use blocked-and-scored candidate generation with four explicit outcomes: resolved, review, ambiguous, unresolved. Same-name collisions are held out unless independent blocking evidence resolves them. Thresholds are evaluated on a labeled gold set and a locked manual-audit subset.

## Consequences

The project publishes resolver coverage, ambiguity, unresolved reasons, false matches, and audit miss rate before any downstream model result. Downstream production joins are only permitted through the resolved bridge or explicit human labels.
