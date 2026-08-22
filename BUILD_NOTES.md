# Build notes

## 2026-08-21 — Phase 1 execution layer

Implemented the runnable path from immutable CFBD source acquisition to measurable entity-resolution quality:

- multi-season portal + full-roster ingestion (`2021..END`)
- exact-parameter manifest lookup so team-specific roster pulls cannot accidentally replace the full-season roster in analysis
- stable SHA-256 `portal_key` derived from all ten portal fields
- resolver accounting by status and reason
- deterministic stratified human-audit sample and label template
- SQLite manifest export to JSONL for Databricks ingestion
- end-to-end manifest → resolver integration test
- Declarative Automation Bundle with Lakeflow Job
- Bronze provenance, Silver entity-resolution, and Gold resolver-accounting Delta materializations

Authenticated CFBD ingestion has been executed locally for the 2021-2026 portal seasons. The production entity resolver processed 18,878 portal entries and auto-resolved 10,685 (56.60% overall). Because 4,951 portal entries have no destination and are structurally unavailable to destination-roster matching, coverage among the 13,927 destination-known entries is 76.72%. The resolver uses same-season destination rosters first and a conservative next-season fallback only for unresolved destination-known records; review and ambiguous cases are never auto-overridden. The current test suite contains 20 passing tests. Raw authenticated source payloads and credentials remain excluded from version control.
