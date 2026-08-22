# Databricks notebook source
# COMMAND ----------
from pyspark.sql import functions as F

dbutils.widgets.text("predictions_2026_v2_presentation_path", "")
dbutils.widgets.text("predictions_2026_v2_presentation_summary_path", "")
dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "cfb_transfer_portal")

presentation_path = dbutils.widgets.get("predictions_2026_v2_presentation_path")
summary_path = dbutils.widgets.get(
    "predictions_2026_v2_presentation_summary_path"
)
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

if not presentation_path:
    raise ValueError("predictions_2026_v2_presentation_path is required")
if not summary_path:
    raise ValueError(
        "predictions_2026_v2_presentation_summary_path is required"
    )

# COMMAND ----------
LOCKED_SHA256 = {
    "presentation": "5b57993e1611f931f2bcba52e8e891d551754f12b62546dd5421f298af97bfe9",
    "summary": "3cb175ff48426fe90731ad76e0931859d34342dae2a43d600848ceb288eac90d",
}

def sha256_for_file(path: str) -> str:
    rows = (
        spark.read.format("binaryFile")
        .load(path)
        .select(F.sha2(F.col("content"), 256).alias("sha256"))
        .collect()
    )
    if len(rows) != 1:
        raise ValueError(
            f"Expected exactly one file at {path}; found {len(rows)}"
        )
    return rows[0]["sha256"]

actual_hashes = {
    "presentation": sha256_for_file(presentation_path),
    "summary": sha256_for_file(summary_path),
}
for name, expected in LOCKED_SHA256.items():
    actual = actual_hashes[name]
    if actual != expected:
        raise ValueError(
            f"Frozen presentation SHA-256 mismatch for {name}: "
            f"expected={expected} actual={actual}"
        )

# COMMAND ----------
presentation = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(presentation_path)
)

summary = (
    spark.read
    .option("multiLine", "true")
    .json(summary_path)
)

required = {
    "portal_key",
    "portal_season",
    "player_id",
    "portal_first_name",
    "portal_last_name",
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
    "forecast_support",
    "forecast_support_reason",
}
missing = required.difference(presentation.columns)
if missing:
    raise ValueError(
        f"Missing presentation columns: {sorted(missing)}"
    )
if "target_post_production" in presentation.columns:
    raise ValueError(
        "2026 presentation must not contain target_post_production"
    )

# COMMAND ----------
rows = presentation.count()
distinct_keys = presentation.select("portal_key").distinct().count()
non_2026 = presentation.filter(F.col("portal_season") != 2026).count()
bad_forecast_status = presentation.filter(
    F.col("forecast_status") != "unobserved_2026_outcome"
).count()

support_counts = {
    row["forecast_support"]: row["count"]
    for row in presentation.groupBy("forecast_support").count().collect()
}
expected_support_counts = {
    "STRONG": 1521,
    "STANDARD": 84,
    "LIMITED": 469,
}

if rows != 2074:
    raise ValueError(f"Expected 2,074 presentation rows, found {rows}")
if distinct_keys != rows:
    raise ValueError(
        f"Presentation portal_key must be unique: "
        f"rows={rows}, distinct={distinct_keys}"
    )
if non_2026:
    raise ValueError(
        f"All presentation rows must be 2026; non_2026={non_2026}"
    )
if bad_forecast_status:
    raise ValueError(
        f"All presentation rows must remain unobserved forecasts; "
        f"bad_rows={bad_forecast_status}"
    )
if support_counts != expected_support_counts:
    raise ValueError(
        "Forecast-support counts do not match locked presentation release: "
        f"expected={expected_support_counts} actual={support_counts}"
    )

# COMMAND ----------
bad_limited = presentation.filter(
    (F.col("forecast_support") == "LIMITED")
    & (F.col("baseline_pre_production_missing") != True)
).count()

bad_strong = presentation.filter(
    (F.col("forecast_support") == "STRONG")
    & (
        (F.col("baseline_pre_production_missing") != False)
        | (F.col("model_feature_missing_count") > 2)
    )
).count()

bad_standard = presentation.filter(
    (F.col("forecast_support") == "STANDARD")
    & (
        (F.col("baseline_pre_production_missing") != False)
        | (F.col("model_feature_missing_count") <= 2)
    )
).count()

if bad_limited or bad_strong or bad_standard:
    raise ValueError(
        "Forecast-support contract violation: "
        f"limited={bad_limited}, strong={bad_strong}, "
        f"standard={bad_standard}"
    )

# COMMAND ----------
source_predictions = spark.table(
    f"{catalog}.{schema}.gold_player_predictions_2026_v2"
).select(
    "portal_key",
    F.col("predicted_post_transfer_production").alias(
        "source_point_prediction"
    ),
)

comparison = presentation.select(
    "portal_key",
    F.col("predicted_post_transfer_production").alias(
        "presentation_point_prediction"
    ),
).join(
    source_predictions,
    on="portal_key",
    how="full",
)

missing_source = comparison.filter(
    F.col("source_point_prediction").isNull()
).count()
missing_presentation = comparison.filter(
    F.col("presentation_point_prediction").isNull()
).count()
changed_prediction = comparison.filter(
    F.abs(
        F.col("presentation_point_prediction")
        - F.col("source_point_prediction")
    ) > F.lit(1e-12)
).count()

if missing_source or missing_presentation or changed_prediction:
    raise ValueError(
        "Presentation must preserve the frozen point predictions exactly: "
        f"missing_source={missing_source}, "
        f"missing_presentation={missing_presentation}, "
        f"changed_prediction={changed_prediction}"
    )

# COMMAND ----------
summary_row = summary.select(
    F.col("rows").alias("rows"),
    F.col("support_counts.STRONG").alias("strong"),
    F.col("support_counts.STANDARD").alias("standard"),
    F.col("support_counts.LIMITED").alias("limited"),
    F.col("prediction_modified").alias("prediction_modified"),
    F.col("2026_outcome_used").alias("outcome_used"),
    F.col("causal_claim").alias("causal_claim"),
    F.col("governance.support_is_confidence").alias(
        "support_is_confidence"
    ),
    F.col("governance.support_is_prediction_interval").alias(
        "support_is_prediction_interval"
    ),
    F.col("governance.support_is_accuracy").alias(
        "support_is_accuracy"
    ),
    F.col("governance.point_forecasts_changed").alias(
        "point_forecasts_changed"
    ),
    F.col("governance.2026_outcomes_observed").alias(
        "outcomes_observed"
    ),
).first()

if summary_row is None:
    raise ValueError("Presentation summary JSON is empty")
if int(summary_row["rows"]) != 2074:
    raise ValueError("Presentation summary row count mismatch")
if int(summary_row["strong"]) != 1521:
    raise ValueError("Presentation summary STRONG count mismatch")
if int(summary_row["standard"]) != 84:
    raise ValueError("Presentation summary STANDARD count mismatch")
if int(summary_row["limited"]) != 469:
    raise ValueError("Presentation summary LIMITED count mismatch")

false_fields = (
    "prediction_modified",
    "outcome_used",
    "causal_claim",
    "support_is_confidence",
    "support_is_prediction_interval",
    "support_is_accuracy",
    "point_forecasts_changed",
    "outcomes_observed",
)
for field in false_fields:
    if bool(summary_row[field]):
        raise ValueError(
            f"Presentation governance field {field} must be false"
        )

# COMMAND ----------
tables = {
    "gold_player_predictions_2026_v2_presentation": presentation,
    "gold_player_predictions_2026_v2_presentation_summary": summary,
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
    spark.table(
        f"{catalog}.{schema}.gold_player_predictions_2026_v2_presentation"
    )
    .groupBy("model_position_group", "forecast_support")
    .agg(
        F.count("*").alias("rows"),
        F.avg("predicted_post_transfer_production").alias(
            "avg_predicted_post_transfer_production"
        ),
    )
    .orderBy("model_position_group", "forecast_support")
)
