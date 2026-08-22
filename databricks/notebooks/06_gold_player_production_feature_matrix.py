# Databricks notebook source
# COMMAND ----------
dbutils.widgets.text("feature_matrix_path", "")
dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "cfb_transfer_portal")

feature_matrix_path = dbutils.widgets.get("feature_matrix_path")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

if not feature_matrix_path:
    raise ValueError("feature_matrix_path is required")

matrix = spark.read.json(feature_matrix_path)

required = {
    "portal_key",
    "portal_season",
    "player_id",
    "portal_position",
    "analysis_eligible_complete_pre_post",
    "post_outcome_right_censored",
}
missing = required.difference(matrix.columns)
if missing:
    raise ValueError(f"Missing feature-matrix columns: {sorted(missing)}")

row_count = matrix.count()
distinct_portal_keys = matrix.select("portal_key").distinct().count()
feature_columns = [
    name for name in matrix.columns
    if name.startswith("pre_") or name.startswith("post_")
]

if row_count != 10685:
    raise ValueError(f"Expected 10,685 feature-matrix rows for v1, found {row_count}")
if distinct_portal_keys != row_count:
    raise ValueError(
        f"Feature matrix portal_key must be unique: rows={row_count}, "
        f"distinct_portal_keys={distinct_portal_keys}"
    )
if len(feature_columns) != 108:
    raise ValueError(
        f"Expected 108 pre/post feature columns for v1, found {len(feature_columns)}"
    )

(
    matrix.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{schema}.gold_player_production_feature_matrix")
)

display(
    spark.table(f"{catalog}.{schema}.gold_player_production_feature_matrix")
    .groupBy("portal_season")
    .count()
    .orderBy("portal_season")
)
