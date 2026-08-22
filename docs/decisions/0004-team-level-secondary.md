# ADR 0004 — Keep team-level inference secondary

**Status:** Accepted

## Context

Portal data begins in the modern portal era, producing many player transfers but only hundreds of team-seasons. Team-season sample size is much smaller than the player-level sample and clustered within programs.

## Decision

Make player-level prediction the primary statistical analysis. Team-level models are descriptive/secondary, use program-aware uncertainty, report wide intervals, include returning production, and include the negative control from ADR 0003.

## Consequences

The project does not overstate precision from a small number of team-seasons. The limitation is prominent in the written analysis rather than buried in a footnote.
