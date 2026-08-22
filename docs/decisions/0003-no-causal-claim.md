# ADR 0003 — Do not answer the causal portal-impact question

**Status:** Accepted

## Context

A naive regression of team improvement on incoming portal talent is confounded: strong programs attract strong transfers, coaching changes affect both recruiting and outcomes, and portal participation is not randomly assigned.

## Decision

Frame the primary player-level work as prediction with point-in-time features. At team level, report associations with wide uncertainty and require returning production as a baseline. Add a negative control: if portal features predict the **prior** season's performance change, the design is detecting confounding/leakage rather than treatment effect.

## Consequences

No coefficient is described as “the effect of the portal.” Causal language is prohibited unless a future design introduces defensible identification assumptions and diagnostics.
