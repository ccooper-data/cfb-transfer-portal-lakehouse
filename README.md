# CFB Transfer Portal Lakehouse

A data-engineering-first platform for measuring what happens after college football players enter the transfer portal.

The centerpiece is **entity resolution**, not model complexity. The portal endpoint does not expose a player ID, while roster and production endpoints do. This repository therefore treats the name-to-player-ID join as a measured, testable product with explicit unresolved and ambiguous states.

## Research questions

1. **Player-level prediction:** does portal information improve prediction of post-transfer production beyond a point-in-time baseline built from returning production and prior player/team information?
2. **Team-level association:** how much does incoming portal talent add beyond returning production when describing subsequent team performance?

The second question is deliberately not framed as causal. Good programs attract good transfers, and the available portal era produces only a few hundred team-seasons. See `docs/decisions/0003-no-causal-claim.md` and `0004-team-level-secondary.md`.

## Architecture

```text
CollegeFootballData API
        |
        v
immutable raw JSON objects  data/raw/objects/<sha-prefix>/<sha>.json
        |
        +--> data/raw/manifest.sqlite  (request + source provenance)
        |
        v
portal rows + historical rosters
        |
        v
blocked-and-scored entity resolver
        |
        +--> resolved player_id
        +--> manual review
        +--> ambiguous holdout
        +--> unresolved reason
        |
        v
labeled evaluation + resolution-rate publication
        |
        v
Delta/Databricks feature tables and modeling (next layer)
```

The raw archive mirrors the proven manifest pattern from the GTFS project: exact source bytes are content-addressed by SHA-256 and stored once, while every API observation is retained separately in SQLite with timestamps, request parameters, source URL, headers, and object pointer. This keeps the source layer reproducible and auditable.

## Source endpoints

The current CFBD Python client documents `GET /player/portal`, historical rosters at `GET /roster`, returning production at `GET /player/returning`, player season stats at `GET /stats/player/season`, and team season stats at `GET /stats/season`. The official package is installable as `cfbd`.

This project uses a tiny raw HTTP client for ingestion so the exact JSON response bytes can be archived before any generated-client model coercion. The official `cfbd` package is pinned in `requirements.txt` for exploration and downstream typed access.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -r requirements.txt
export CFBD_API_KEY='...'
```

Archive a portal season:

```bash
make portal YEAR=2024
```

Archive a roster season:

```bash
make roster YEAR=2024
```

Or only a destination roster:

```bash
make roster YEAR=2024 TEAM='Ohio State'
```

Run tests:

```bash
make test
```

Run the complete 2021-present source pull once `CFBD_API_KEY` is set:

```bash
make ingest-all START=2021 END=2026
make build-resolution START=2021 END=2026
```

The build writes:

- `outputs/resolutions_2021_2026.jsonl`
- `outputs/resolver_accounting_2021_2026.json`
- `outputs/entity_resolution_audit_2021_2026.csv`
- `outputs/raw_manifest.jsonl`

The audit CSV is deliberately stratified across resolver statuses/reasons so the human review set does not consist only of easy exact-name matches.

## Entity-resolution contract

The resolver **never silently fuzzy-joins** a portal row to a player ID.

### Blocking

Candidates must be on the disclosed destination roster in the portal season. Position group is used as a primary block when available, with a destination-team fallback because positions can be dirty or missing.

### Scoring

- last name similarity: 55%
- first name similarity / common alias equivalence: 30%
- position-group agreement: 15%

Common first-name variants such as `Mike` / `Michael` are treated as supporting equivalence, not as proof of identity.

### Decisions

- `resolved`: high score **and** clear margin over runner-up
- `review`: plausible match but requires human label
- `ambiguous`: same-name collision or insufficient score margin
- `unresolved`: no destination, no roster candidate, or low score

An exact same-name collision is deliberately held out rather than forced.

## The metric that matters first

Before publishing model accuracy, publish the resolver accounting table:

```text
portal entries                         N
resolved automatically                 n / N
manual-review candidates               n / N
ambiguous same-name collisions         n / N
no subsequent destination roster row   n / N
low-score unresolved                   n / N
manual-audit misses                    n / audited_n
```

The target write-up should read like:

> “8,431 of 8,947 portal entries (94.2%) resolved; of the 5.8% unresolved, 3.1% never appeared on a subsequent roster, 1.9% were ambiguous same-name collisions held out, and 0.8% were missed on manual audit.”

Those numbers are **illustrative until the labeled evaluation is run**. The repository is structured so the final paragraph is computed, not hand-written.

## Labeled evaluation set

`data/labels/entity_resolution_labels.csv` is the human-reviewed gold set. Do not tune only on easy exact-name matches. Include:

- nicknames / formal first names
- suffixes
- punctuation / diacritics
- same-name collisions at one destination
- position changes
- portal withdrawals
- destination changes
- players missing from the subsequent roster

Split labels into development and locked audit subsets before threshold tuning.

## Point-in-time discipline

Player-level models must use only information known before the target season outcome. Returning production is the baseline the portal signal has to beat. The planned negative control predicts **prior-season change** from future portal features; if that “works,” the design is contaminated by confounding or leakage.

## Databricks plan

The repository now includes a **Declarative Automation Bundle** and a three-task Lakeflow Job for the first medallion slice:

- **Bronze:** `bronze_source_manifest` — immutable request/source provenance exported from the local SQLite manifest.
- **Silver:** `silver_transfer_resolution` — stable portal entry key, entity-resolution decision, player ID when resolved, scores, reasons, and candidate evidence.
- **Gold:** `gold_resolver_accounting` — season/status/reason counts and shares that drive the published resolver-quality statement.

The next Databricks increments add raw portal/roster/player-stat tables, the resolved player-season bridge, point-in-time player production features, returning-production baseline, negative-control panel, and then modeling/MLflow. See `databricks/README.md`.

Streamlit is intentionally last. The primary deliverables are the platform, resolver evaluation, ADRs, reproducible jobs, Delta tables, and written analysis.

## Decisions

See `docs/decisions/`:

1. immutable raw source archive and manifest
2. measured entity resolution with explicit holdouts
3. no causal claim from observational portal data
4. team-level analysis is secondary and underpowered
5. Streamlit is the final presentation layer, not the platform

## Current status

**Phase 1 foundation is implemented:**

- immutable content-addressed raw archive
- SQLite source/request manifest
- portal/roster ingestion commands
- blocked-and-scored player-ID resolver
- explicit ambiguous/unresolved reason codes
- label-file contract and evaluation helper
- unit tests and GitHub Actions CI
- five ADRs

The local Phase 1 workflow is now end-to-end and waiting only on a CFBD API key for the first real source pull. It can ingest every portal/roster season from 2021-present, resolve the archived data, publish complete resolver accounting, generate a deterministic stratified human-audit template, and export the raw manifest for Databricks. A Declarative Automation Bundle then materializes Bronze provenance, Silver entity-resolution decisions, and Gold resolver-accounting Delta tables.

The next evidence milestone is the **real 2021-present run and labeled audit**. No resolution percentage will be published until that run is completed and the held-out labels are reviewed.

## Source references

- CollegeFootballData API: https://api.collegefootballdata.com
- Getting started / API key: https://api.collegefootballdata.com/getting-started
- Official Python client: https://github.com/CFBD/cfbd-python
- Transfer portal reference (cfbfastR): https://cfbfastr.sportsdataverse.org/reference/cfbd_recruiting_transfer_portal.html
