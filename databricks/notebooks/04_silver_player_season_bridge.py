# Databricks notebook source
# COMMAND ----------
dbutils.widgets.text("bridge_path", "")
dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "cfb_transfer_portal")

bridge_path = dbutils.widgets.get("bridge_path")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

if not bridge_path:
    raise ValueError("bridge_path is required")

bridge = spark.read.json(bridge_path)

required = {
    "portal_key",
    "portal_season",
    "player_id",
    "origin",
    "destination",
    "pre_season",
    "post_season",
    "post_outcome_right_censored",
}
missing = required.difference(bridge.columns)
if missing:
    raise ValueError(f"Missing bridge columns: {sorted(missing)}")

row_count = bridge.count()
distinct_portal_keys = bridge.select("portal_key").distinct().count()

if row_count != 10685:
    raise ValueError(f"Expected 10,685 bridge rows for v1, found {row_count}")
if distinct_portal_keys != row_count:
    raise ValueError(
        f"Bridge portal_key must be unique: rows={row_count}, "
        f"distinct_portal_keys={distinct_portal_keys}"
    )

(
    bridge.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{schema}.silver_player_season_bridge")
)

display(
    spark.table(f"{catalog}.{schema}.silver_player_season_bridge")
    .groupBy("portal_season")
    .count()
    .orderBy("portal_season")
)
