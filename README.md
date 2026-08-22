# CFB Transfer Portal Lakehouse

A data-engineering-first college football analytics platform that resolves transfer-portal identities, links players to longitudinal production, builds point-in-time modeling features, and evaluates post-transfer production on a strict future-season holdout.

The centerpiece is **measured entity resolution and reproducible analytical lineage**, not model complexity.

The CollegeFootballData transfer-portal endpoint does not expose a player ID, while roster and player-stat endpoints do. This repository therefore treats portal-name → CFBD-player-ID resolution as a first-class product with explicit unresolved, review, and ambiguous states before any production modeling occurs.

## What has been built

The project now runs end to end from authenticated CFBD acquisition through predictive evaluation:

```text
CollegeFootballData API
        |
        v
immutable raw JSON objects
content-addressed by SHA-256
        |
        +--> SQLite request/source manifest
        |
        v
portal rows + historical rosters
        |
        v
blocked-and-scored entity resolver
        |
        +--> same-season resolution
        +--> conservative next-season fallback
        +--> review / ambiguous / unresolved
        |
        v
locked resolver precision audit
        |
        v
resolved player-season production bridge
        |
        v
108-column pre/post production feature matrix
        |
        v
position-aware modeling targets
        |
        +--> strict 2025 holdout evaluation
        +--> returning-production baseline
        +--> negative-control selection diagnostic
```

Databricks currently materializes the initial Bronze/Silver/Gold resolver slice. The next productionization step is to port the completed local player bridge, feature, holdout, and negative-control layers into Delta tables and MLflow-tracked jobs.

## Current evidence snapshot

### Source acquisition and entity resolution

Authenticated CFBD ingestion has been completed for portal seasons **2021–2026**.

- **18,878** portal rows processed
- **10,685** automatically resolved to a CFBD player ID
- **56.60%** overall automatic resolution coverage
- **13,927** portal rows disclosed a destination
- **76.72%** automatic resolution coverage among destination-known rows
- **10,531** same-season resolutions
- **154** conservative next-season fallback resolutions
- 2026 next-season fallback is unavailable because a 2027 roster does not yet exist

The resolver never overrides review or ambiguous states merely to improve coverage.

### Locked resolver precision audit

Resolver v1 was frozen before the precision audit.

The locked audit contains **274** records:

- 120 deterministic same-season sample rows — 20 per portal season from 2021–2026
- all 154 next-season fallback resolutions — a complete census of that strategy

AI-assisted independent evidence review produced:

- **270 correct**
- **0 verified incorrect**
- **4 uncertain**

The audit should **not** be described as 100% accuracy.

Strict verified results, where uncertain rows are not silently counted as correct:

- next-season fallback census: **99.35%**
- combined production-resolution precision estimate: **98.89%**
- approximate 95% interval for the combined strict estimate: **94.28%–99.79%**

The evidence review is **AI-assisted with human confirmation pending**. See `docs/decisions/0006-resolver-v1-locked-precision-audit.md`.

### Player-production bridge

Resolved transfer records are joined to CFBD player-season statistics by the stable `playerId`.

The production bridge contains:

- **10,685** resolved transfer rows
- **132,956** linked long-form stat rows
- **4,388** transfers with observed expected-team production in both the pre-transfer and post-transfer seasons
- **54.52%** complete pre/post coverage among the 8,049 transfers whose outcome season is complete

The bridge preserves explicit flags for team mismatches and missing production. Missing statistics are not silently converted to zero.

The 2026 post-transfer outcome is explicitly right-censored because 2026 player-season statistics are not yet available.

### Feature layer

The analytical feature layer contains:

- **10,685** one-row-per-transfer feature records
- **108** raw CFBD production features
- **54 pre-transfer** feature columns
- **54 post-transfer** feature columns
- **4,388** complete pre/post analysis rows

Feature identity preserves the full:

```text
phase + category + statType
```

For example, passing yards and rushing yards remain separate metrics.

### Position-aware modeling population

Position-specific anchor outcomes are used instead of forcing every football position into one generic target.

Examples:

- QB → passing yards
- RB → rushing yards
- WR / TE → receiving yards
- DB / DL / EDGE / LB → total tackles
- K → kicking points
- P → yards per punt

The position-aware target layer retains **4,168** modeling rows from the 4,388-row complete cohort.

Offensive line and long-snapper rows are explicitly excluded because the available CFBD individual statistics do not provide a defensible equivalent production target.

## 2025 holdout evaluation

The first predictive evaluation uses a strict time split:

- train: **2021–2024**
- holdout: **2025**
- hyperparameter selection: expanding-year validation inside 2021–2024 only
- no 2025 observations used for model fitting or alpha selection
- no `post_*` production variables used as predictors

Each position-specific ridge model is benchmarked against a simple **returning-production baseline**:

> predict the player's post-transfer anchor production with the player's observed pre-transfer anchor production.

Eight position groups met the sample-size requirement and all eight reduced 2025 holdout MAE versus that baseline.

| Position | 2025 holdout rows | Baseline MAE | Model MAE | MAE improvement |
| --- | ---: | ---: | ---: | ---: |
| RB | 160 | 392.50 | 279.47 | **28.8%** |
| EDGE | 54 | 13.22 | 10.09 | **23.7%** |
| WR | 261 | 285.05 | 222.78 | **21.8%** |
| DL | 194 | 12.30 | 10.11 | **17.8%** |
| LB | 154 | 33.68 | 28.07 | **16.7%** |
| DB | 388 | 20.31 | 17.89 | **11.9%** |
| TE | 91 | 124.47 | 116.20 | **6.6%** |
| QB | 106 | 897.18 | 868.10 | **3.2%** |

The evaluated holdout contains **1,408** transfer cases.

These results support a predictive claim:

> the position-specific numeric profiles reduced absolute prediction error relative to simply carrying forward prior-season production.

They do **not** support a causal claim that transferring caused the production change. Several groups still have weak or negative R² despite improved MAE, so the project deliberately avoids describing the models as universally “high accuracy.”

Punter was skipped because only 30 training rows were available.

## Negative-control / selection diagnostic

A falsification test asks whether future portal-side information can predict a performance change that happened **before the transfer**.

For portal season `S`, the negative-control outcome is:

```text
anchor production(S-1) - anchor production(S-2)
```

The future-side predictors are portal destination, rating, and stars. Destination encoding is learned on training rows only.

Design:

- train seasons: **2022–2024**
- strict holdout: **2025**
- **2,893** negative-control panel rows
- **1,023** 2025 holdout predictions
- **8** position groups evaluated
- **3** groups triggered the diagnostic criterion: DL, RB, and TE

The detected signal is modest:

- DL: about **2.62%** MAE improvement versus historical mean
- RB: about **0.93%**
- TE: about **0.90%**

This is evidence that player selection into portal destinations is associated with performance trajectories already underway before the move.

That finding does **not** invalidate predictive forecasting. It does reinforce the decision to avoid interpreting post-transfer prediction as a causal estimate of school or transfer effects.

## Research questions

1. **Player-level prediction:** can point-in-time pre-transfer information predict post-transfer production better than returning production alone?
2. **Selection/confounding diagnostics:** do future portal characteristics contain signal about outcomes that were already determined before the transfer?
3. **Team-level association:** how much does incoming portal talent add beyond returning production when describing subsequent team performance?

The third question remains secondary. The portal era yields only a few hundred team-seasons, and successful programs attract better transfers. Team-level results will therefore be treated as association, not causal effect.

## Source endpoints

The project uses CollegeFootballData endpoints including:

- `GET /player/portal`
- `GET /roster`
- `GET /stats/player/season`
- `GET /player/returning`
- `GET /stats/season`
- `GET /records`

A small raw HTTP client is used for ingestion so exact response bytes can be archived before any generated-client coercion.

The official `cfbd` Python package is pinned in `requirements.txt` for exploration and downstream typed access.

## Source provenance

Raw API responses are immutable and content-addressed:

```text
data/raw/objects/<sha-prefix>/<sha256>.json
```

Every observation is recorded separately in the local SQLite manifest with request parameters, source information, timestamps, headers, byte count, record count, SHA-256, and object pointer.

This gives the project a reproducible lineage from source response through resolution and analytical outputs.

Raw authenticated source payloads and credentials are intentionally excluded from version control.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -r requirements.txt
```

Set the CFBD API key in your shell before authenticated ingestion:

```bash
export CFBD_API_KEY='...'
```

Run tests:

```bash
make test
```

Archive a single portal or roster season:

```bash
make portal YEAR=2024
make roster YEAR=2024
```

Run portal/roster ingestion and resolution:

```bash
make ingest-all START=2021 END=2026
make build-resolution START=2021 END=2026
```

Player statistics are archived separately so the identity layer does not need to be rerun:

```bash
for YEAR in 2020 2021 2022 2023 2024 2025 2026
do
  PYTHONPATH=src python3 -m cfb_portal.ingest player_stats --season "$YEAR"
done
```

## Reproducible analytical layers

Key local scripts include:

```text
scripts/evaluate_precision_audit.py
scripts/build_player_season_bridge.py
scripts/build_player_feature_matrix.py
scripts/build_position_modeling_table.py
scripts/evaluate_holdout_2025.py
scripts/evaluate_negative_control.py
```

Generated analytical CSV/JSON/JSONL files are intentionally treated as reproducible outputs rather than source code, except for selected locked audit artifacts that are committed as part of the governance record.

## Entity-resolution contract

The resolver **never silently fuzzy-joins** a portal row to a player ID.

### Blocking

Candidates are drawn from the disclosed destination roster. Position group is used as a primary block when available, with same-team fallback because roster positions can be dirty, broad, or missing.

### Scoring

- last-name similarity: 55%
- first-name similarity / supported alias equivalence: 30%
- position-group agreement: 15%

### Decisions

- `resolved` — high score and sufficient margin
- `review` — plausible match requiring review
- `ambiguous` — same-name collision or insufficient score margin
- `unresolved` — no destination, no roster candidate, or low score

A conservative next-season roster is only attempted for eligible same-season unresolved rows. It never overrides review or ambiguous states.

## Point-in-time discipline

The analytical design enforces temporal separation.

- post-transfer production is never used as a predictor
- 2025 holdout observations are not used to fit 2021–2024 models
- 2025 is not used for hyperparameter selection
- destination encodings in the negative control are learned from training rows only
- missing anchor outcomes are excluded rather than converted to zero
- 2026 post-transfer outcomes are marked right-censored

Returning production is the benchmark the predictive model has to beat.

## Databricks

The repository includes a Declarative Automation Bundle and the first three-task Lakeflow medallion slice:

- **Bronze** — `bronze_source_manifest`
- **Silver** — `silver_transfer_resolution`
- **Gold** — `gold_resolver_accounting`

The local Python pipeline now goes beyond that initial Databricks slice. The next Databricks increment will materialize the resolved player-season bridge, feature matrix, modeling populations, holdout evaluation outputs, and negative-control diagnostics as governed Delta tables, then add MLflow experiment tracking.

Streamlit remains intentionally last.

## Architectural decisions

See `docs/decisions/`:

1. immutable raw source archive and provenance manifest
2. entity resolution is a measured product
3. no causal claim from observational portal data
4. team-level analysis is secondary and underpowered
5. Streamlit is the final presentation layer
6. resolver v1 is frozen before its locked precision audit

## Tests

The current local suite contains **41 passing tests** covering source provenance, deterministic identity keys, resolver safeguards, next-season fallback behavior, locked-audit evaluation, player-stat bridging, feature construction, position targets, strict holdout separation, and the negative-control design.

## Current status

The project has completed the main local analytical proof:

- authenticated portal and roster ingestion
- immutable source provenance
- audited resolver v1
- exact-ID player-production bridge
- point-in-time feature layer
- position-aware targets
- strict 2025 predictive holdout
- returning-production benchmark
- negative-control selection diagnostic

The next engineering milestone is **Databricks productionization of the completed player-level analytical layers**, followed by MLflow tracking and, only after those platform layers are stable, the final Streamlit presentation layer.

## Source references

- CollegeFootballData API: https://api.collegefootballdata.com
- CollegeFootballData getting started: https://api.collegefootballdata.com/getting-started
- Official CFBD Python client: https://github.com/CFBD/cfbd-python
- cfbfastR transfer-portal reference: https://cfbfastr.sportsdataverse.org/reference/cfbd_recruiting_transfer_portal.html
