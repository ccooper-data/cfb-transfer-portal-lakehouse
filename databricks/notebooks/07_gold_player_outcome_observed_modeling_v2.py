# Databricks notebook source
# COMMAND ----------
from pyspark.sql import functions as F

dbutils.widgets.text("outcome_modeling_v2_path", "")
dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "cfb_transfer_portal")

outcome_modeling_v2_path = dbutils.widgets.get("outcome_modeling_v2_path")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

if not outcome_modeling_v2_path:
    raise ValueError("outcome_modeling_v2_path is required")

modeling = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(outcome_modeling_v2_path)
)

required = {
    "portal_key",
    "portal_season",
    "player_id",
    "portal_position",
    "model_position_group",
    "target_metric",
    "baseline_pre_production",
    "baseline_pre_production_missing",
    "target_post_production",
    "pre_feature_observed_count",
    "pre_feature_missing_count",
    "any_pre_feature_observed",
}
missing = required.difference(modeling.columns)
if missing:
    raise ValueError(f"Missing v2 modeling columns: {sorted(missing)}")

row_count = modeling.count()
distinct_portal_keys = modeling.select("portal_key").distinct().count()

pre_metadata_columns = {
    "pre_feature_observed_count",
    "pre_feature_missing_count",
}
pre_feature_columns = [
    name
    for name in modeling.columns
    if name.startswith("pre_") and name not in pre_metadata_columns
]
missingness_indicator_columns = [
    name for name in modeling.columns if name.startswith("missing_pre_")
]
post_predictor_columns = [
    name for name in modeling.columns if name.startswith("post_")
]

missing_pre_anchor_rows = modeling.filter(
    F.col("baseline_pre_production_missing") == True
).count()
observed_pre_anchor_rows = modeling.filter(
    F.col("baseline_pre_production_missing") == False
).count()
missing_target_rows = modeling.filter(
    F.col("target_post_production").isNull()
).count()

if row_count != 5631:
    raise ValueError(f"Expected 5,631 v2 modeling rows, found {row_count}")
if distinct_portal_keys != row_count:
    raise ValueError(
        f"v2 portal_key must be unique: rows={row_count}, "
        f"distinct_portal_keys={distinct_portal_keys}"
    )
if len(pre_feature_columns) != 54:
    raise ValueError(
        f"Expected 54 raw pre-transfer production features, "
        f"found {len(pre_feature_columns)}"
    )
if len(missingness_indicator_columns) != 54:
    raise ValueError(
        f"Expected 54 explicit pre-feature missingness indicators, "
        f"found {len(missingness_indicator_columns)}"
    )
if post_predictor_columns:
    raise ValueError(
        f"Post-transfer predictor columns are prohibited: {post_predictor_columns}"
    )
if missing_pre_anchor_rows != 1463:
    raise ValueError(
        f"Expected 1,463 rows with missing pre anchor, "
        f"found {missing_pre_anchor_rows}"
    )
if observed_pre_anchor_rows != 4168:
    raise ValueError(
        f"Expected 4,168 rows with observed pre anchor, "
        f"found {observed_pre_anchor_rows}"
    )
if missing_target_rows:
    raise ValueError(
        f"Expected observed post target for every v2 row; "
        f"found {missing_target_rows} missing"
    )

(
    modeling.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(
        f"{catalog}.{schema}.gold_player_outcome_observed_modeling_v2"
    )
)

display(
    spark.table(
        f"{catalog}.{schema}.gold_player_outcome_observed_modeling_v2"
    )
    .groupBy("portal_season", "model_position_group")
    .agg(
        F.count("*").alias("rows"),
        F.sum(
            F.col("baseline_pre_production_missing").cast("int")
        ).alias("missing_pre_anchor_rows"),
    )
    .orderBy("portal_season", "model_position_group")
)
