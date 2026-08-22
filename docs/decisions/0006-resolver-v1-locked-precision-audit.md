# ADR 0006: Freeze resolver v1 after locked precision audit

## Status

Accepted — 2026-08-22.

## Context

The transfer-portal endpoint does not expose a stable player ID, so downstream player-season analysis depends on the resolver that maps a portal row to a destination-roster player ID. Resolver v1 was frozen before evaluation. The immutable pre-label audit artifact is `outputs/resolved_precision_audit_v1.csv`, with SHA-256:

`d216bcab69949a960423a713ea08981a87edaa3e29f1777d31429c262b84a096`

The locked audit contains 274 production auto-resolutions:

- all 154 next-season fallback resolutions (a census of that production path)
- 20 deterministic hash-selected same-season resolutions from each portal season 2021–2026 (120 total)

Review/ambiguous rows are not part of this precision audit because they are not production auto-resolutions.

## Decision

Resolver v1 remains frozen. The audit is used to measure it, not tune it.

The completed review artifact is `data/labels/resolved_precision_audit_v1_ai_review.csv`. It is explicitly an **AI-assisted independent evidence review**, not a claim that a human manually adjudicated all 274 rows. Evidence is recorded in the `notes` field. Independent destination-school rosters, bios, transfer announcements, media guides, and other public sources were preferred over resolver inputs.

Allowed outcomes are:

- `correct`: independent evidence supports the predicted roster player as the same portal entrant
- `incorrect`: independent evidence establishes the predicted player is wrong
- `uncertain`: available evidence does not independently establish the identity

Uncertain rows are never silently converted to correct.

## Results

Across all 274 audited auto-resolutions:

- 270 correct
- 0 verified incorrect
- 4 uncertain

### Next-season fallback census

- 154 production matches audited
- 153 correct
- 0 incorrect
- 1 uncertain
- strict verified rate: **99.35%**

Because this is a census of the production fallback path, no sampling interval is reported for that rate.

### Same-season stratified sample

Production same-season auto-resolutions by season are:

| Portal season | Population N | Audit n | Correct | Incorrect | Uncertain |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | 551 | 20 | 18 | 0 | 2 |
| 2022 | 1,047 | 20 | 20 | 0 | 0 |
| 2023 | 1,242 | 20 | 19 | 0 | 1 |
| 2024 | 2,017 | 20 | 20 | 0 | 0 |
| 2025 | 3,038 | 20 | 20 | 0 | 0 |
| 2026 | 2,636 | 20 | 20 | 0 | 0 |
| **Total** | **10,531** | **120** | **117** | **0** | **3** |

The production-weighted strict verified estimate is **98.89%**. "Strict" treats uncertain rows as not verified.

For sampling uncertainty, the evaluator reports an **approximate 95% weighted Wilson interval using Kish effective sample size** for the unequal per-record stratum weights. The current interval is **94.20%–99.79%** with Kish effective n ≈ **95.65**.

This interval is intentionally identified as approximate; the audit sample is deterministic hash selection rather than a separately randomized survey sample.

### Combined production auto-resolutions

Resolver v1 auto-resolved 10,685 portal rows:

- 10,531 same-season matches
- 154 next-season fallback matches

Combining the population-weighted same-season estimate with the fallback census gives a strict verified point estimate of **98.89%**. Propagating the same-season approximate interval while holding the fallback census fixed gives **94.28%–99.79%**.

The possible upper bound is 100% if every uncertain row is ultimately verified correct. The project does **not** report "100% accuracy."

## Consequences

1. Resolver v1 is not modified based on this audit.
2. Any threshold, alias, blocking, or fallback change becomes resolver v2 and requires a new locked audit.
3. The four uncertain rows remain uncertainty, not hidden success.
4. Downstream modeling may use production auto-resolutions while carrying resolver quality and coverage limitations into interpretation.
5. The 2026 next-season fallback remains right-censored because no 2027 roster exists in the archived source set.
6. Precision and coverage are reported separately: high precision does not erase structurally unresolved portal rows.

## Reproduction

Run:

```bash
python scripts/evaluate_precision_audit.py \
  data/labels/resolved_precision_audit_v1_ai_review.csv
```

The evaluator validates label consistency and reproduces the fallback census, population-weighted same-season estimate, Kish effective sample size, and combined production estimate.
