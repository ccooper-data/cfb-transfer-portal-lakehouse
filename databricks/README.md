# Databricks execution layer

The local collector/resolver owns immutable source acquisition and human-auditable identity decisions. Databricks owns scalable materialization and downstream analytics.

This repo uses a **Declarative Automation Bundle** (`databricks.yml`) with a Lakeflow Job that materializes:

1. `bronze_source_manifest` — request/source provenance exported from SQLite.
2. `silver_transfer_resolution` — one row per portal entry with stable `portal_key`, status, reason, candidate evidence, and player ID when resolved.
3. `gold_resolver_accounting` — season/status/reason counts and rates suitable for the published resolver-quality paragraph.

Before deployment, copy `outputs/raw_manifest.jsonl` and `outputs/resolutions_<start>_<end>.jsonl` to a Unity Catalog Volume or other workspace-readable path. Then set bundle variables for `cluster_id`, `manifest_path`, and `resolutions_path`.

Typical flow:

```bash
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run -t dev transfer_portal_lakehouse
```

The bundle intentionally uses an existing cluster variable rather than hard-coding a cloud-specific node type into a public portfolio repository.
