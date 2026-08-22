# CFB Transfer Portal Lakehouse

**A governed college-football analytics platform for entity resolution, point-in-time feature engineering, temporal model evaluation, and frozen 2026 transfer forecasts.**

[Live 2026 Forecast Dashboard](https://cfb-transfer-forecast.streamlit.app/) · [Repository](https://github.com/ccooper-data/cfb-transfer-portal-lakehouse)

This project starts with a difficult data problem: the CollegeFootballData transfer-portal endpoint does not expose a stable player ID, while roster and player-stat endpoints do. The platform therefore treats **identity resolution, observability, temporal leakage control, and reproducible evidence as first-class analytical products** before any forecast is published.

The result is more than a prediction notebook. It is an end-to-end lakehouse and model-governance case study spanning immutable source ingestion, measured entity resolution, longitudinal feature construction, Databricks medallion layers, rolling temporal evaluation, frozen evidence artifacts, preregistered 2026 scoring, and a public Streamlit application.

---

## Executive findings

### 1. The identity problem is measurable, not hand-waved

Across portal seasons **2021–2026**, the project processed **18,878 transfer rows** and automatically resolved **10,685** to CFBD player IDs.

- Overall automatic resolution coverage: **56.60%**
- Resolution coverage among destination-known rows: **76.72%**
- Same-season resolutions: **10,531**
- Conservative next-season fallback resolutions: **154**

Resolver v1 was frozen before audit. The locked audit reviewed **274 records** and produced **270 correct, 0 verified incorrect, and 4 uncertain** classifications. The strict combined production-resolution precision estimate is approximately **98.89%**. The audit is AI-assisted with human confirmation pending; it is **not** described as 100% accuracy.

### 2. The production model shows repeatable out-of-time value

The v2 position-specific production model is evaluated with rolling temporal holdouts for **2022, 2023, and 2024**. Training always uses only seasons earlier than the holdout year, and preprocessing/hyperparameter selection are fit inside the training period.

Across the locked primary evidence:

- **20** position-year folds were evaluable
- **16/20** beat a historical-mean baseline on all holdout rows
- **18/20** beat a returning-production baseline on the paired subset
- In **2024, all eight evaluable position groups beat both baselines**

The project does not claim that every fold wins or that prediction quality is uniform across positions.

### 3. The project discovered a second problem: outcome observability

The original production estimand is conditional on the exact post-transfer target being observable. Rather than treating missing targets as zeros or silently dropping them, the project created a separate v3 observability study.

Among **6,478** historical 2021–2025 transfers in the eight scoreable position groups that were conservatively linked to the destination roster in the same season:

- exact v2 target observed: **5,557 (85.78%)**
- any CFBD stat but exact target missing: **108 (1.67%)**
- no CFBD player-stat row: **813 (12.55%)**

That means missing target values are primarily an **observability problem**, not evidence that a player failed to make a roster, did not play, or produced zero.

### 4. Observability signal transported into a harder 2025 environment

The first locked 2022–2024 v3 rolling study produced **3,251 out-of-time predictions** and beat the training-period prevalence baseline in **13/19** evaluated folds. The pooled Brier improvement was modest, and the original pooled calibration slope was about **0.51**, so the model was kept as a diagnostic rather than promoted as a production-ready probability model.

A separately preregistered **2025 temporal stress test** then evaluated all **2,431** eligible 2025 rows using only 2021–2024 training data.

- All **8/8** position groups beat their locked prevalence baseline on Brier score
- Pooled Brier: **0.1427** vs **0.1500** baseline
- Pooled Brier skill: approximately **+4.9%**
- ROC AUC: **0.6788** vs **0.5700** baseline
- Pooled calibration slope: approximately **0.795**

The strongest 2025 probability evidence was in **DB, DL, and TE**. Some position-level calibration remained unstable, especially for smaller/high-prevalence groups, so the probabilities are not presented as equally calibrated across every position.

---

## What the project does — and does not — claim

The project supports carefully scoped predictive claims:

- pre-transfer information can improve post-transfer production prediction relative to simple baselines for many position-year cohorts;
- target observability contains measurable out-of-time signal beyond position-specific historical prevalence;
- the 2025 observability stress test showed broad positive temporal transport across all eight evaluated position groups.

The project **does not** claim:

- transfer destination causes production changes;
- unresolved portal records represent players who disappeared, failed to make a roster, or did not play;
- missing target statistics equal zero production;
- the v3 observability probability is “probability the player will play”;
- forecast support tiers are confidence intervals or accuracy probabilities;
- 2026 forecast accuracy is already known.

These boundaries are encoded in the repository's decision records rather than left as presentation disclaimers.

---

## 2026 frozen forecast release

The current public release contains **2,074 frozen 2026 forecasts** across:

`DB · DL · EDGE · LB · QB · RB · TE · WR`

The forecast file was hash-locked before 2026 outcomes were available:

```text
outputs/player_predictions_2026_v2.csv
SHA-256:
306268a4dbb633592c781b2288bb1ff8f93ea8c9584b0f8fb2e32ab08f9e1ef9
```

Forecast support is an **input/data-support label**, not a confidence score:

| Support | Forecasts |
| --- | ---: |
| STRONG | 1,521 |
| STANDARD | 84 |
| LIMITED | 469 |
| **Total** | **2,074** |

The 2026 outcome remains unobserved. The repository includes a preregistered accuracy protocol that fixes the frozen population, target definitions, baselines, metrics, missing-outcome accounting states, and bootstrap comparison procedure before final 2026 evaluation.

---

## Why the observability layer matters

A conventional workflow might have trained only on rows with observed post-transfer statistics and moved on.

This project treats that conditioning as an analytical risk.

For same-season destination-roster-linked historical rows, a missing CFBD target is not assumed to mean:

```text
not on roster
did not play
zero production
```

Instead, the governed decomposition is:

```text
conservative destination-roster linkage
        |
        v
target-stat observability
        |
        v
production conditional on target observed
```

The production forecast and observability probability remain separate estimands. They are **not multiplied together and relabeled as expected football production** because the data do not establish that an unobserved target has true value zero.

---

## Architecture

```text
CollegeFootballData API
        |
        v
immutable raw JSON responses
content-addressed by SHA-256
        |
        +--> request/source provenance manifest
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
resolved player-season bridge
        |
        +--> longitudinal CFBD player statistics
        |
        v
108-column pre/post production feature matrix
        |
        +--> 54 pre-transfer features
        +--> 54 post-transfer outcome fields
        |
        +------------------------------+
        |                              |
        v                              v
v2 conditional production       v3 target observability
rolling temporal backtest       rolling temporal backtest
        |                              |
        v                              v
frozen 2026 forecasts           2025 stress test
        |                              |
        +---------------+--------------+
                        |
                        v
              governed evidence artifacts
                        |
                        v
               Databricks Gold layers
                        |
                        v
             public Streamlit dashboard
```

---

## Point-in-time discipline

Temporal leakage controls are explicit:

- `post_*` production fields are never model predictors;
- each outer temporal holdout is trained only on earlier seasons;
- preprocessing is fit on training rows only;
- hyperparameter selection occurs only inside the training period;
- destination encoding in the exploratory negative control is fit on training rows only;
- missing target outcomes are never silently converted to zero;
- 2026 outcomes are not used to train or tune the frozen 2026 release.

The v2 primary rolling evidence uses 2022–2024. Because 2025 results had been inspected in earlier development, 2025 is not relabeled as a pristine fresh v2 holdout.

---

## Position-specific targets

Football production is modeled with position-aware targets instead of forcing unlike positions into one generic outcome.

| Position group | Target |
| --- | --- |
| QB | passing yards |
| RB | rushing yards |
| WR | receiving yards |
| TE | receiving yards |
| DB | total tackles |
| DL | total tackles |
| EDGE | total tackles |
| LB | total tackles |

Kicker, punter, offensive-line, and long-snapper rows are not included in the frozen eight-group 2026 v2 release. The source data do not provide a sufficiently comparable individual production target for every position.

---

## Entity-resolution contract

The resolver never silently fuzzy-joins a portal row to a player ID.

### Blocking

Candidates are drawn from the disclosed destination roster. Position group is used when available, with same-team fallback because roster positions can be dirty, broad, or missing.

### Scoring

- last-name similarity: **55%**
- first-name similarity / supported alias equivalence: **30%**
- position-group agreement: **15%**

### Decisions

- `resolved` — high score with sufficient margin
- `review` — plausible match requiring review
- `ambiguous` — collision or insufficient margin
- `unresolved` — no destination, no roster candidate, or score below threshold

A conservative next-season roster fallback is attempted only for eligible same-season unresolved rows. It does not override `review` or `ambiguous` states.

---

## Resolver audit

Resolver v1 was frozen before evaluation.

The locked audit consists of:

- **120** deterministic same-season sample rows — 20 per portal season from 2021–2026
- **154** next-season fallback rows — the complete fallback census

AI-assisted independent evidence review produced:

- **270 correct**
- **0 verified incorrect**
- **4 uncertain**

Strict results do not silently count uncertain rows as correct.

The combined strict production-resolution precision estimate is approximately **98.89%**. Because the same-season audit is deterministic rather than a randomized survey sample, its interval estimate is presented as approximate.

---

## Production feature layer

Resolved transfers are linked to CFBD player-season statistics using the stable player ID after resolution.

Core scale:

- **10,685** resolved transfer rows
- **132,956** linked long-form player-stat rows
- **10,685** one-row-per-transfer feature records
- **108** raw production variables
- **54** pre-transfer features
- **54** post-transfer outcome fields

Feature identity preserves:

```text
phase + category + statType
```

so, for example, passing yards and rushing yards remain distinct metrics.

---

## v2 rolling production evidence

The locked v2 rolling design evaluates portal years:

```text
2022 <- train on 2021
2023 <- train on 2021-2022
2024 <- train on 2021-2023
```

Primary evidence:

- **2,941** out-of-time predictions
- **20** evaluated position-year folds
- **7** skipped folds because the preregistered support threshold was not met
- **16/20** wins versus historical-mean baseline on all rows
- **18/20** wins versus returning-production baseline on paired rows

The 2024 cohort is particularly useful as a mature-year check: all eight evaluable groups beat both baselines.

This is predictive evidence. It is not a causal estimate of transfer or destination effect.

---

## v3 target-observability evidence

The v3 estimand is:

```text
P(
  exact position-specific CFBD target observed
  |
  conservative same-season destination-roster linkage,
  information available at scoring time
)
```

The first locked rolling study uses 2022–2024 outer holdouts and regularized logistic regression with Brier score as the primary metric.

### First locked rolling study

- historical cohort: **6,478**
- exact targets observed: **5,557**
- exact targets missing: **921**
- out-of-time predictions: **3,251**
- evaluated folds: **19**
- Brier wins vs training prevalence: **13/19**
- pooled model Brier: **0.1048**
- pooled baseline Brier: **0.1066**
- pooled ROC AUC: **0.6731**
- pooled calibration slope: approximately **0.51**

Because calibration was weak, the first model remained a diagnostic.

### 2025 temporal stress test

2025 was explicitly locked as a stress test, not described as a pristine untouched holdout.

Using only 2021–2024 training data:

| Group | N | Brier skill vs prevalence |
| --- | ---: | ---: |
| DB | 668 | **+6.13%** |
| DL | 329 | **+5.84%** |
| EDGE | 95 | **+0.91%** |
| LB | 249 | **+3.07%** |
| QB | 213 | **+1.27%** |
| RB | 207 | **+1.33%** |
| TE | 206 | **+10.37%** |
| WR | 464 | **+3.70%** |

All eight groups were positive on the locked primary metric, while position-level calibration remained heterogeneous.

---

## Exploratory negative control

The project also includes an exploratory falsification/selection diagnostic asking whether future portal-side information can predict a performance change that occurred **before** the transfer.

For portal season `S`, the diagnostic outcome is:

```text
anchor production(S-1) - anchor production(S-2)
```

The current negative control bundles destination, rating, and stars and found modest signal in **3/8** position groups. It is treated as an exploratory selection/confounding diagnostic, not causal proof.

A future version can separate destination-only, rating/stars-only, and combined feature sets and add within-season/position permutation nulls without rewriting the original evidence.

---

## Databricks lakehouse

The repository includes a Databricks Asset Bundle and a working multi-task medallion pipeline.

The current successful job materializes:

```text
bronze_manifest
silver_resolutions
gold_resolver_accounting
silver_player_season_bridge
silver_player_stats_long
gold_player_production_feature_matrix
gold_player_outcome_observed_modeling_v2
gold_player_predictions_2026_v2
gold_player_predictions_2026_v2_presentation
```

This moves the project beyond a local notebook demonstration: governed bridge, feature, modeling, scoring, and presentation layers have been operationalized in Databricks.

---

## Public forecast application

The public Streamlit application presents the frozen 2026 release without changing the underlying predictions.

**Live app:** https://cfb-transfer-forecast.streamlit.app/

The dashboard separates:

- forecast board;
- position-level views;
- input/data support;
- historical model evidence.

It also keeps the core governance messages visible:

- 2026 outcomes are not observed yet;
- forecasts are not a claim of known 2026 accuracy;
- support is not confidence;
- comparisons should be made within position because target units differ.

---

## Evidence and governance

The repository uses decision records and SHA-256 manifests to make analytical changes auditable.

Important governance milestones include:

```text
0006  resolver v1 precision audit
0008  v2 rolling temporal backtest design
0009  v2 rolling evidence lock
0010  2026 v2 scoring contract
0011  first 2026 forecast release lock
0012  2026 forecast support contract
0013  presentation release lock
0014  preregistered 2026 v2 accuracy protocol
0015  v3 target-observability design
0016  first v3 evidence interpretation
0017  2025 v3 temporal stress-test protocol
0018  2025 v3 stress-test interpretation
```

The sequence matters: designs are locked before results when possible, first-run evidence is hashed and published, and later extensions are versioned rather than used to rewrite earlier outcomes.

---

## Reproducibility

Selected frozen evidence artifacts are committed to the repository so public SHA manifests resolve to public files.

Examples include:

```text
outputs/v2_rolling_backtest_predictions_2022_2024.csv
outputs/v2_rolling_backtest_results_2022_2024.json
outputs/player_predictions_2026_v2.csv
outputs/player_scoring_cohort_2026_v2.csv
outputs/player_scoring_exclusions_2026_v2.csv
outputs/v3_target_observability_cohort_2021_2025.csv
outputs/v3_target_observability_predictions_2022_2024.csv
outputs/v3_target_observability_results_2022_2024.json
outputs/v3_target_observability_stress_test_predictions_2025.csv
outputs/v3_target_observability_stress_test_results_2025.json
```

Raw authenticated CFBD payloads and credentials remain excluded from version control.

---

## Quick start

Create the environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -r requirements.txt
```

Set the CFBD API key before authenticated ingestion:

```bash
export CFBD_API_KEY='...'
```

Run tests:

```bash
make test
```

Run the public dashboard locally:

```bash
streamlit run app.py
```

---

## Key analytical scripts

```text
scripts/evaluate_precision_audit.py
scripts/build_player_season_bridge.py
scripts/build_player_feature_matrix.py
scripts/build_outcome_observed_modeling_v2.py
scripts/evaluate_rolling_backtest_v2.py
scripts/score_2026_v2.py
scripts/build_2026_forecast_presentation.py
scripts/evaluate_target_observability_v3.py
scripts/evaluate_2025_observability_stress_test.py
```

---

## Testing

The repository currently has **69 passing local tests** covering source provenance, deterministic identity keys, resolver safeguards, fallback behavior, locked-audit evaluation, player-stat bridging, feature construction, position targets, temporal split discipline, v2 scoring, support labeling, v3 observability evaluation, and the separately governed 2025 stress test.

---

## What this repository demonstrates

From a portfolio perspective, the project is designed to show several capabilities in one auditable system:

- **Data engineering:** authenticated ingestion, immutable raw storage, provenance, medallion layers, Databricks jobs
- **Analytics engineering:** stable identity keys, reusable bridge tables, wide feature matrices, explicit contracts
- **Data science:** position-specific targets, temporal backtesting, regularization, baselines, calibration, probability scoring
- **Data governance:** preregistration, evidence locking, SHA manifests, traceable decision records, explicit claim boundaries
- **Technical leadership judgment:** refusing to convert missing outcomes to zero, separating observability from production, preserving failed/mixed folds, and versioning extensions instead of tuning away inconvenient results
- **Product delivery:** frozen forecast release and public Streamlit application

The governing principle is simple:

> **A model is only as credible as the identity, timing, observability, and evidence controls underneath it.**

---

## Current status

Completed:

- authenticated CFBD ingestion for 2021–2026
- immutable source provenance
- audited entity resolver
- player-season bridge and long-form statistics
- 108-variable production feature matrix
- governed v2 outcome-observed modeling cohort
- locked 2022–2024 rolling temporal evidence
- frozen 2026 forecast release
- preregistered 2026 accuracy protocol
- public Streamlit dashboard
- Databricks productionization through forecast presentation Gold
- governed v3 target-observability study
- locked 2025 v3 temporal stress test

Still intentionally open:

- final 2026 outcome evaluation after the source is documented as complete
- human confirmation of the AI-assisted resolver audit
- separately versioned calibration or alternative v3 models
- stronger negative-control decomposition and permutation inference
- second resolver audit concentrated near the weakest score/margin bands

The frozen v2 forecast is not modified by any v3 extension.

---

## Source references

- CollegeFootballData API: https://api.collegefootballdata.com
- CollegeFootballData getting started: https://api.collegefootballdata.com/getting-started
- Official CFBD Python client: https://github.com/CFBD/cfbd-python
- cfbfastR transfer-portal reference: https://cfbfastr.sportsdataverse.org/reference/cfbd_recruiting_transfer_portal.html
