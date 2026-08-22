# Databricks notebook source
# COMMAND ----------
dbutils.widgets.text("stats_path", "")
dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "cfb_transfer_portal")

stats_path = dbutils.widgets.get("stats_path")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

if not stats_path:
    raise ValueError("stats_path is required")

stats = spark.read.json(stats_path)

required = {
    "portal_key",
    "portal_season",
    "phase",
    "player_id",
    "expected_team",
    "stat_season",
    "category",
    "stat_type",
    "stat",
}
missing = required.difference(stats.columns)
if missing:
    raise ValueError(f"Missing long-stat columns: {sorted(missing)}")

row_count = stats.count()
if row_count != 132956:
    raise ValueError(f"Expected 132,956 linked stat rows for v1, found {row_count}")

bad_phase_count = stats.filter(~stats.phase.isin("pre", "post")).count()
if bad_phase_count:
    raise ValueError(f"Found {bad_phase_count} rows with phase outside pre/post")

(
    stats.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{schema}.silver_player_stats_long")
)

display(
    spark.table(f"{catalog}.{schema}.silver_player_stats_long")
    .groupBy("portal_season", "phase")
    .count()
    .orderBy("portal_season", "phase")
)
