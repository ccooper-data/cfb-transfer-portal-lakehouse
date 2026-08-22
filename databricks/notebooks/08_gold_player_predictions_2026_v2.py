# Databricks notebook source
# COMMAND ----------
from pyspark.sql import functions as F

dbutils.widgets.text("scoring_cohort_2026_v2_path", "")
dbutils.widgets.text("scoring_exclusions_2026_v2_path", "")
dbutils.widgets.text("predictions_2026_v2_path", "")
dbutils.widgets.text("predictions_2026_v2_summary_path", "")
dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "cfb_transfer_portal")

scoring_cohort_path = dbutils.widgets.get("scoring_cohort_2026_v2_path")
scoring_exclusions_path = dbutils.widgets.get("scoring_exclusions_2026_v2_path")
predictions_path = dbutils.widgets.get("predictions_2026_v2_path")
summary_path = dbutils.widgets.get("predictions_2026_v2_summary_path")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

required_paths = {
    "scoring_cohort_2026_v2_path": scoring_cohort_path,
    "scoring_exclusions_2026_v2_path": scoring_exclusions_path,
    "predictions_2026_v2_path": predictions_path,
    "predictions_2026_v2_summary_path": summary_path,
}
missing_paths = [name for name, value in required_paths.items() if not value]
if missing_paths:
    raise ValueError(f"Required forecast-release paths are missing: {missing_paths}")

# COMMAND ----------
LOCKED_SHA256 = {
    "scoring_cohort": "86dfe5490ff48866396878787bd6e9c99a748fe86796c55167345499e0f8472c",
    "scoring_exclusions": "1ee05a4f631cf29d55945d83a645a65431edfeed450d8d6db7b023325d5de0b7",
    "predictions": "306268a4dbb633592c781b2288bb1ff8f93ea8c9584b0f8fb2e32ab08f9e1ef9",
    "summary": "23af46a1c2ad30d241708ca1047c54106a14400a470c6e32f2c437338fb322e5",
}

def sha256_for_file(path: str) -> str:
    rows = (
        spark.read.format("binaryFile")
        .load(path)
        .select(F.sha2(F.col("content"), 256).alias("sha256"))
        .collect()
    )
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one file at {path}; found {len(rows)}")
    return rows[0]["sha256"]

actual_hashes = {
    "scoring_cohort": sha256_for_file(scoring_cohort_path),
    "scoring_exclusions": sha256_for_file(scoring_exclusions_path),
    "predictions": sha256_for_file(predictions_path),
    "summary": sha256_for_file(summary_path),
}
for name, expected in LOCKED_SHA256.items():
    actual = actual_hashes[name]
    if actual != expected:
        raise ValueError(
            f"Frozen-release SHA-256 mismatch for {name}: "
            f"expected={expected} actual={actual}"
        )

# COMMAND ----------
scoring_cohort = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(scoring_cohort_path)
)

scoring_exclusions = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(scoring_exclusions_path)
)

predictions = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(predictions_path)
)

summary = (
    spark.read
    .option("multiLine", "true")
    .json(summary_path)
)

# COMMAND ----------
cohort_required = {
    "portal_key",
    "portal_season",
    "player_id",
    "portal_position",
    "model_position_group",
    "origin",
    "destination",
    "target_metric",
    "baseline_pre_production",
    "baseline_pre_production_missing",
    "post_outcome_status",
    "model_feature_count",
    "model_feature_missing_count",
    "model_feature_observed_count",
}
prediction_required = {
    "portal_key",
    "portal_season",
    "player_id",
    "portal_position",
    "model_position_group",
    "origin",
    "destination",
    "target_metric",
    "predicted_post_transfer_production",
    "baseline_pre_production",
    "baseline_pre_production_missing",
    "model_feature_missing_count",
    "chosen_alpha",
    "training_rows",
    "forecast_status",
}
exclusion_required = {
    "portal_key",
    "portal_season",
    "player_id",
    "portal_position",
    "model_position_group",
    "exclusion_reason",
}

for label, frame, required in (
    ("scoring cohort", scoring_cohort, cohort_required),
    ("predictions", predictions, prediction_required),
    ("exclusions", scoring_exclusions, exclusion_required),
):
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing {label} columns: {sorted(missing)}")

if "target_post_production" in scoring_cohort.columns:
    raise ValueError("2026 scoring cohort must not contain target_post_production")
if "target_post_production" in predictions.columns:
    raise ValueError("2026 predictions must not contain target_post_production")

# COMMAND ----------
cohort_rows = scoring_cohort.count()
cohort_distinct_keys = scoring_cohort.select("portal_key").distinct().count()
prediction_rows = predictions.count()
prediction_distinct_keys = predictions.select("portal_key").distinct().count()
exclusion_rows = scoring_exclusions.count()

missing_pre_rows = scoring_cohort.filter(
    F.col("baseline_pre_production_missing") == True
).count()
observed_pre_rows = scoring_cohort.filter(
    F.col("baseline_pre_production_missing") == False
).count()

non_2026_cohort = scoring_cohort.filter(F.col("portal_season") != 2026).count()
non_2026_predictions = predictions.filter(F.col("portal_season") != 2026).count()
bad_outcome_status = scoring_cohort.filter(
    F.col("post_outcome_status") != "right_censored_unobserved"
).count()
bad_forecast_status = predictions.filter(
    F.col("forecast_status") != "unobserved_2026_outcome"
).count()

if cohort_rows != 2074:
    raise ValueError(f"Expected 2,074 scoring cohort rows, found {cohort_rows}")
if cohort_distinct_keys != cohort_rows:
    raise ValueError(
        f"Scoring cohort portal_key must be unique: rows={cohort_rows}, "
        f"distinct={cohort_distinct_keys}"
    )
if prediction_rows != 2074:
    raise ValueError(f"Expected 2,074 prediction rows, found {prediction_rows}")
if prediction_distinct_keys != prediction_rows:
    raise ValueError(
        f"Prediction portal_key must be unique: rows={prediction_rows}, "
        f"distinct={prediction_distinct_keys}"
    )
if exclusion_rows != 562:
    raise ValueError(f"Expected 562 exclusion rows, found {exclusion_rows}")
if missing_pre_rows != 469:
    raise ValueError(
        f"Expected 469 scoring rows with missing pre anchor, found {missing_pre_rows}"
    )
if observed_pre_rows != 1605:
    raise ValueError(
        f"Expected 1,605 scoring rows with observed pre anchor, found {observed_pre_rows}"
    )
if non_2026_cohort or non_2026_predictions:
    raise ValueError(
        f"All scoring/prediction rows must be 2026: "
        f"cohort_non_2026={non_2026_cohort}, "
        f"prediction_non_2026={non_2026_predictions}"
    )
if bad_outcome_status:
    raise ValueError(
        f"Expected right-censored scoring outcomes; bad rows={bad_outcome_status}"
    )
if bad_forecast_status:
    raise ValueError(
        f"Expected unobserved 2026 forecast status; bad rows={bad_forecast_status}"
    )

# COMMAND ----------
summary_row = summary.select(
    F.col("cohort.scoreable_rows").alias("cohort_scoreable_rows"),
    F.col("cohort.pre_anchor_observed_rows").alias("pre_anchor_observed_rows"),
    F.col("cohort.pre_anchor_missing_rows").alias("pre_anchor_missing_rows"),
    F.col("scoring.prediction_rows").alias("prediction_rows"),
    F.col("scoring.governance.2026_outcome_used").alias("outcome_used"),
    F.col("scoring.governance.causal_claim").alias("causal_claim"),
).first()

if summary_row is None:
    raise ValueError("2026 prediction summary JSON is empty")
if int(summary_row["cohort_scoreable_rows"]) != 2074:
    raise ValueError("Summary scoreable-row count does not match locked release")
if int(summary_row["prediction_rows"]) != 2074:
    raise ValueError("Summary prediction-row count does not match locked release")
if int(summary_row["pre_anchor_observed_rows"]) != 1605:
    raise ValueError("Summary observed-pre count does not match locked release")
if int(summary_row["pre_anchor_missing_rows"]) != 469:
    raise ValueError("Summary missing-pre count does not match locked release")
if bool(summary_row["outcome_used"]):
    raise ValueError("2026 outcome_used must be false")
if bool(summary_row["causal_claim"]):
    raise ValueError("causal_claim must be false")

# COMMAND ----------
tables = {
    "gold_player_scoring_cohort_2026_v2": scoring_cohort,
    "gold_player_scoring_exclusions_2026_v2": scoring_exclusions,
    "gold_player_predictions_2026_v2": predictions,
    "gold_player_predictions_2026_v2_summary": summary,
}

for table_name, frame in tables.items():
    (
        frame.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"{catalog}.{schema}.{table_name}")
    )

# COMMAND ----------
display(
    spark.table(f"{catalog}.{schema}.gold_player_predictions_2026_v2")
    .groupBy("model_position_group")
    .agg(
        F.count("*").alias("prediction_rows"),
        F.sum(
            F.col("baseline_pre_production_missing").cast("int")
        ).alias("missing_pre_anchor_rows"),
        F.avg("predicted_post_transfer_production").alias(
            "avg_predicted_post_transfer_production"
        ),
    )
    .orderBy("model_position_group")
)
