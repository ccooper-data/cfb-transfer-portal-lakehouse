# Databricks notebook source
# COMMAND ----------
dbutils.widgets.text("manifest_path", "")
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "cfb_transfer_portal")

manifest_path = dbutils.widgets.get("manifest_path")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
if not manifest_path:
    raise ValueError("manifest_path is required")

spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`")
manifest = spark.read.json(manifest_path)
(
    manifest.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{schema}.bronze_source_manifest")
)

# The manifest is the provenance spine: every archived source response can be traced
# to exact request parameters, timestamps, source URL, SHA-256, and immutable object path.
display(spark.table(f"{catalog}.{schema}.bronze_source_manifest").orderBy("id"))
