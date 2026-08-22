from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = Path("data/dashboard/player_predictions_2026_v2_presentation.csv")
SUMMARY_PATH = Path(
    "data/dashboard/player_predictions_2026_v2_presentation_summary.json"
)

EXPECTED_ROWS = 2074
EXPECTED_SUPPORT_COUNTS = {
    "STRONG": 1521,
    "STANDARD": 84,
    "LIMITED": 469,
}

POSITION_ORDER = ["QB", "RB", "WR", "TE", "DB", "LB", "EDGE", "DL"]
SUPPORT_ORDER = ["STRONG", "STANDARD", "LIMITED"]

st.set_page_config(
    page_title="2026 CFB Transfer Portal Forecast Board",
    page_icon="🏈",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    .forecast-banner {
        border: 1px solid rgba(120,120,120,.25);
        border-radius: 12px;
        padding: 0.9rem 1rem;
        margin: 0.4rem 0 1rem 0;
        background: rgba(120,120,120,.07);
    }
    .small-note {font-size: 0.88rem; opacity: 0.82;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, dict]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dashboard snapshot not found: {DATA_PATH}. "
            "Run the dashboard snapshot build step first."
        )
    if not SUMMARY_PATH.exists():
        raise FileNotFoundError(
            f"Dashboard summary not found: {SUMMARY_PATH}. "
            "Run the dashboard snapshot build step first."
        )

    frame = pd.read_csv(DATA_PATH)
    with SUMMARY_PATH.open() as f:
        summary = json.load(f)

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
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Dashboard snapshot is missing columns: {sorted(missing)}")

    if len(frame) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS:,} frozen presentation rows; "
            f"found {len(frame):,}"
        )
    if frame["portal_key"].nunique() != EXPECTED_ROWS:
        raise ValueError("portal_key must remain unique in dashboard snapshot")
    if set(frame["portal_season"].astype(int)) != {2026}:
        raise ValueError("Dashboard snapshot must contain 2026 rows only")
    if set(frame["forecast_status"].dropna()) != {"unobserved_2026_outcome"}:
        raise ValueError("Dashboard must contain unobserved 2026 forecasts only")

    actual_support = (
        frame["forecast_support"].value_counts().to_dict()
    )
    if actual_support != EXPECTED_SUPPORT_COUNTS:
        raise ValueError(
            "Forecast-support counts changed: "
            f"expected={EXPECTED_SUPPORT_COUNTS} actual={actual_support}"
        )

    frame["player_name"] = (
        frame["portal_first_name"].fillna("").str.strip()
        + " "
        + frame["portal_last_name"].fillna("").str.strip()
    ).str.strip()
    frame["transfer_path"] = (
        frame["origin"].fillna("Unknown")
        + " → "
        + frame["destination"].fillna("Unknown")
    )
    frame["prior_observed"] = ~frame[
        "baseline_pre_production_missing"
    ].astype(bool)
    frame["forecast_minus_prior"] = (
        frame["predicted_post_transfer_production"]
        - frame["baseline_pre_production"]
    )
    return frame, summary


def pct(part: int, whole: int) -> str:
    if whole == 0:
        return "0.0%"
    return f"{100 * part / whole:.1f}%"


def metric_display_name(raw: str) -> str:
    return str(raw).replace("_", " ").strip().title()


def filtered_frame(
    frame: pd.DataFrame,
    positions: list[str],
    supports: list[str],
    destination_search: str,
    player_search: str,
) -> pd.DataFrame:
    out = frame[
        frame["model_position_group"].isin(positions)
        & frame["forecast_support"].isin(supports)
    ].copy()

    if destination_search.strip():
        out = out[
            out["destination"]
            .fillna("")
            .str.contains(destination_search.strip(), case=False, regex=False)
        ]

    if player_search.strip():
        out = out[
            out["player_name"]
            .str.contains(player_search.strip(), case=False, regex=False)
        ]
    return out


frame, summary = load_data()

st.title("2026 College Football Transfer Portal Forecast Board")
st.caption(
    "Frozen v2 player-level forecasts with governed data-support metadata."
)

st.markdown(
    """
    <div class="forecast-banner">
    <strong>Forecast status:</strong> 2026 outcomes are unobserved.
    These are predictive point estimates, not 2026 accuracy results and not
    causal estimates of school or transfer effects.
    <br>
    <strong>Forecast Support</strong> describes observed input support.
    It is not a confidence score, probability, or prediction interval.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Filters")
    position_options = [
        p for p in POSITION_ORDER if p in set(frame["model_position_group"])
    ]
    positions = st.multiselect(
        "Position group",
        position_options,
        default=position_options,
    )
    supports = st.multiselect(
        "Forecast support",
        SUPPORT_ORDER,
        default=SUPPORT_ORDER,
    )
    destination_search = st.text_input(
        "Destination contains",
        placeholder="e.g. Ohio State",
    )
    player_search = st.text_input(
        "Player contains",
        placeholder="e.g. Brown",
    )
    st.divider()
    st.caption(
        "STRONG = prior production observed and ≤2 model features missing. "
        "STANDARD = prior production observed and >2 missing. "
        "LIMITED = prior-production anchor unavailable."
    )

filtered = filtered_frame(
    frame,
    positions,
    supports,
    destination_search,
    player_search,
)

strong = int((frame["forecast_support"] == "STRONG").sum())
limited = int((frame["forecast_support"] == "LIMITED").sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Frozen forecasts", f"{len(frame):,}")
c2.metric("Strong support", f"{strong:,}", pct(strong, len(frame)))
c3.metric("Limited support", f"{limited:,}", pct(limited, len(frame)))
c4.metric("Modeled groups", frame["model_position_group"].nunique())

tabs = st.tabs(
    [
        "Forecast Board",
        "Position View",
        "Data Support",
        "Model Evidence",
    ]
)

with tabs[0]:
    st.subheader("Forecast Board")
    st.caption(
        f"{len(filtered):,} rows match the current filters. "
        "Forecast magnitudes should be compared within position/target metric, "
        "not across unlike football positions."
    )

    board = filtered.copy()
    board["position_rank"] = (
        board.groupby("model_position_group")[
            "predicted_post_transfer_production"
        ]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    board = board.sort_values(
        ["model_position_group", "position_rank", "player_name"]
    )

    display_board = board[
        [
            "position_rank",
            "player_name",
            "model_position_group",
            "portal_position",
            "origin",
            "destination",
            "target_metric",
            "baseline_pre_production",
            "predicted_post_transfer_production",
            "forecast_support",
            "model_feature_missing_count",
        ]
    ].rename(
        columns={
            "position_rank": "Rank",
            "player_name": "Player",
            "model_position_group": "Group",
            "portal_position": "Portal Pos.",
            "origin": "Origin",
            "destination": "Destination",
            "target_metric": "Target",
            "baseline_pre_production": "Prior",
            "predicted_post_transfer_production": "Forecast",
            "forecast_support": "Support",
            "model_feature_missing_count": "Missing Features",
        }
    )

    st.dataframe(
        display_board,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Prior": st.column_config.NumberColumn(format="%.2f"),
            "Forecast": st.column_config.NumberColumn(format="%.2f"),
        },
    )

with tabs[1]:
    st.subheader("Position View")
    available = [
        p for p in POSITION_ORDER if p in set(frame["model_position_group"])
    ]
    selected_position = st.selectbox("Position group", available)

    pos = frame[
        frame["model_position_group"] == selected_position
    ].copy()
    pos = pos.sort_values(
        "predicted_post_transfer_production",
        ascending=False,
    )
    target_metric = metric_display_name(pos["target_metric"].mode().iloc[0])

    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("Players", f"{len(pos):,}")
    pc2.metric(
        "Strong support",
        pct(int((pos["forecast_support"] == "STRONG").sum()), len(pos)),
    )
    pc3.metric("Target metric", target_metric)

    top_n = st.slider("Top N forecasts", 5, 40, 20)
    top = pos.head(top_n).sort_values(
        "predicted_post_transfer_production",
        ascending=True,
    )
    fig = px.bar(
        top,
        x="predicted_post_transfer_production",
        y="player_name",
        orientation="h",
        hover_data={
            "origin": True,
            "destination": True,
            "forecast_support": True,
            "predicted_post_transfer_production": ":.2f",
        },
        labels={
            "predicted_post_transfer_production": f"Forecast: {target_metric}",
            "player_name": "Player",
        },
        title=f"Top {top_n} {selected_position} Forecasts",
    )
    fig.update_layout(height=max(420, 28 * top_n))
    st.plotly_chart(fig, use_container_width=True)

    observed = pos[
        ~pos["baseline_pre_production_missing"].astype(bool)
    ].copy()
    if not observed.empty:
        st.caption(
            "Observed-prior comparison is descriptive. "
            "Forecast-minus-prior is not a transfer effect."
        )
        scatter = px.scatter(
            observed,
            x="baseline_pre_production",
            y="predicted_post_transfer_production",
            hover_name="player_name",
            hover_data=["origin", "destination", "forecast_support"],
            labels={
                "baseline_pre_production": f"Observed prior: {target_metric}",
                "predicted_post_transfer_production": f"Forecast: {target_metric}",
            },
            title=f"{selected_position}: Prior Production vs Forecast",
        )
        lo = min(
            observed["baseline_pre_production"].min(),
            observed["predicted_post_transfer_production"].min(),
        )
        hi = max(
            observed["baseline_pre_production"].max(),
            observed["predicted_post_transfer_production"].max(),
        )
        scatter.add_trace(
            go.Scatter(
                x=[lo, hi],
                y=[lo, hi],
                mode="lines",
                name="Prior = forecast",
                hoverinfo="skip",
            )
        )
        st.plotly_chart(scatter, use_container_width=True)

with tabs[2]:
    st.subheader("Forecast Support")
    st.caption(
        "Support labels describe input completeness and prior-production "
        "availability. They are not calibrated uncertainty."
    )

    support_counts = (
        frame.groupby(["model_position_group", "forecast_support"])
        .size()
        .reset_index(name="players")
    )
    support_counts["model_position_group"] = pd.Categorical(
        support_counts["model_position_group"],
        categories=POSITION_ORDER,
        ordered=True,
    )
    support_counts["forecast_support"] = pd.Categorical(
        support_counts["forecast_support"],
        categories=SUPPORT_ORDER,
        ordered=True,
    )
    support_counts = support_counts.sort_values(
        ["model_position_group", "forecast_support"]
    )

    support_fig = px.bar(
        support_counts,
        x="model_position_group",
        y="players",
        color="forecast_support",
        barmode="stack",
        category_orders={"forecast_support": SUPPORT_ORDER},
        labels={
            "model_position_group": "Position group",
            "players": "Forecasts",
            "forecast_support": "Support",
        },
        title="2026 Forecast Support by Position",
    )
    st.plotly_chart(support_fig, use_container_width=True)

    support_table = (
        support_counts.pivot(
            index="model_position_group",
            columns="forecast_support",
            values="players",
        )
        .fillna(0)
        .astype(int)
    )
    support_table["TOTAL"] = support_table.sum(axis=1)
    st.dataframe(support_table, use_container_width=True)

with tabs[3]:
    st.subheader("Locked Historical Evidence")
    st.caption(
        "Primary v2 rolling-origin evidence uses historical holdouts "
        "2022–2024. The 2026 season is not part of this accuracy evidence."
    )

    e1, e2, e3 = st.columns(3)
    e1.metric("Rolling predictions", "2,941")
    e2.metric("Wins vs historical mean", "16 / 20")
    e3.metric("Paired wins vs prior production", "18 / 20")

    st.markdown(
        """
        **2024 cross-position result:** all eight evaluable position groups
        beat both historical-mean and returning-production baselines.

        **Governance:** the model is predictive, not causal. Selection and
        confounding diagnostics found modest signal in 3 of 8 groups, which
        reinforces the decision not to interpret forecasts as school effects.

        **2026 release:** 2,074 frozen forecasts across DB, DL, EDGE, LB, QB,
        RB, TE, and WR. Punter was excluded from the 2026 release because the
        locked v2 evidence did not contain an evaluable rolling fold; kicker
        had no outcome-observed training cohort.
        """
    )

    with st.expander("Forecast Support definitions"):
        st.markdown(
            """
            - **STRONG:** prior production observed and no more than 2 model
              features missing.
            - **STANDARD:** prior production observed and more than 2 model
              features missing.
            - **LIMITED:** prior-production anchor unavailable; the point
              forecast relies more heavily on imputation and other observed
              inputs.

            These labels are **not** confidence scores, probabilities,
            prediction intervals, or guarantees of correctness.
            """
        )

st.divider()
st.caption(
    "Frozen 2026 v2 presentation release. "
    "Point forecasts are unchanged from the locked forecast artifact."
)
