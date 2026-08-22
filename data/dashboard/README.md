# Dashboard publication snapshot

This directory contains the content-addressed, presentation-only snapshot used
by the public Streamlit portfolio dashboard.

The source artifact remains the frozen release under `outputs/` and is not
modified by the dashboard build.

Expected first-release SHA-256 values:

- presentation CSV:
  `5b57993e1611f931f2bcba52e8e891d551754f12b62546dd5421f298af97bfe9`
- presentation summary JSON:
  `3cb175ff48426fe90731ad76e0931859d34342dae2a43d600848ceb288eac90d`

The dashboard must preserve the distinction between a 2026 forecast and an
observed 2026 outcome. `forecast_support` is a data-support label, not a
confidence score.
