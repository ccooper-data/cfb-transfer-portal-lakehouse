# Databricks notebook source
# COMMAND ----------
from pyspark.sql import functions as F

dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "cfb_transfer_portal")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

src = spark.table(f"{catalog}.{schema}.silver_transfer_resolution")
counts = (
    src.groupBy("portal_season", "status", "reason")
    .agg(F.count("*").alias("n"))
)
totals = src.groupBy("portal_season").agg(F.count("*").alias("season_n"))
accounting = (
    counts.join(totals, "portal_season")
    .withColumn("share", F.col("n") / F.col("season_n"))
)
(
    accounting.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{schema}.gold_resolver_accounting")
)

display(spark.table(f"{catalog}.{schema}.gold_resolver_accounting").orderBy("portal_season", "status", "reason"))
