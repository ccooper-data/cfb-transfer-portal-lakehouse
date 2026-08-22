# Databricks notebook source
# COMMAND ----------
dbutils.widgets.text("resolutions_path", "")
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "cfb_transfer_portal")

resolutions_path = dbutils.widgets.get("resolutions_path")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
if not resolutions_path:
    raise ValueError("resolutions_path is required")

resolutions = spark.read.json(resolutions_path)
required = {"portal_key", "portal_season", "status", "reason", "candidate_count"}
missing = required.difference(resolutions.columns)
if missing:
    raise ValueError(f"Missing resolution columns: {sorted(missing)}")

(
    resolutions.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{schema}.silver_transfer_resolution")
)

display(spark.table(f"{catalog}.{schema}.silver_transfer_resolution"))
