"""Module M4: AI difficulty-adjustment predictor."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import (
    get_block_at_height,
    get_latest_block,
    get_mempool_difficulty_adjustment,
)


RETARGET_BLOCKS = 2016
RETARGET_INTERVALS = RETARGET_BLOCKS - 1
TARGET_BLOCK_SECONDS = 600
TARGET_PERIOD_SECONDS = RETARGET_BLOCKS * TARGET_BLOCK_SECONDS
MIN_ADJUSTMENT_FACTOR = 0.25
MAX_ADJUSTMENT_FACTOR = 4.0
PLOT_BG = "rgba(255,255,255,0.84)"
PAPER_BG = "rgba(255,255,255,0)"
INK = "#0b0c0d"
MUTED = "#595b57"
ACCENT = "#d8ff45"
COOL = "#5477b8"
HOT = "#f46b45"
PLOT_CONFIG = {"displaylogo": False, "displayModeBar": False, "responsive": True}
FEATURE_COLUMNS = [
    "log_difficulty",
    "actual_ratio",
    "expected_next_change_pct",
    "previous_change_pct",
    "observed_avg_block_minutes",
]


def _format_compact_number(value: float) -> str:
    units = ["", "K", "M", "B", "T", "P"]
    number = float(value)
    unit_index = 0

    while abs(number) >= 1000 and unit_index < len(units) - 1:
        number /= 1000
        unit_index += 1

    suffix = units[unit_index]
    return f"{number:,.2f}{suffix}" if suffix else f"{number:,.0f}"


def _clamp_adjustment_factor(factor: float) -> float:
    return min(max(float(factor), MIN_ADJUSTMENT_FACTOR), MAX_ADJUSTMENT_FACTOR)


def _apply_chart_theme(fig: go.Figure, title_text: str | None = None) -> go.Figure:
    layout_kwargs = {
        "paper_bgcolor": PAPER_BG,
        "plot_bgcolor": PLOT_BG,
        "font": {"family": "Archivo, sans-serif", "color": INK, "size": 13},
        "margin": {"l": 22, "r": 22, "t": 34, "b": 24},
        "xaxis": {
            "showgrid": False,
            "zeroline": False,
            "linecolor": "rgba(11,12,13,0.15)",
            "tickfont": {"color": MUTED},
            "title_font": {"color": INK},
        },
        "yaxis": {
            "gridcolor": "rgba(11,12,13,0.08)",
            "zeroline": False,
            "linecolor": "rgba(11,12,13,0.15)",
            "tickfont": {"color": MUTED},
            "title_font": {"color": INK},
        },
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "bgcolor": "rgba(255,255,255,0)",
            "font": {"color": MUTED},
        },
        "legend_title_text": "",
    }
    if title_text:
        layout_kwargs["title"] = {"text": title_text, "font": {"size": 18, "color": INK}, "x": 0.02}
    fig.update_layout(**layout_kwargs)
    return fig


def _build_completed_epoch_dataset(periods: int) -> pd.DataFrame:
    latest_block = get_latest_block()
    latest_height = int(latest_block["height"])
    current_epoch_start = latest_height - (latest_height % RETARGET_BLOCKS)
    last_complete_epoch_start = current_epoch_start - RETARGET_BLOCKS
    first_epoch_start = max(0, last_complete_epoch_start - (periods - 1) * RETARGET_BLOCKS)

    block_cache: dict[int, dict] = {}

    def block_at(height: int) -> dict:
        if height not in block_cache:
            block_cache[height] = get_block_at_height(height)
        return block_cache[height]

    rows: list[dict[str, object]] = []
    previous_change_pct = 0.0

    for epoch_start in range(first_epoch_start, last_complete_epoch_start + 1, RETARGET_BLOCKS):
        epoch_end = epoch_start + RETARGET_BLOCKS - 1
        next_epoch_start = epoch_start + RETARGET_BLOCKS
        start_block = block_at(epoch_start)
        end_block = block_at(epoch_end)
        next_start_block = block_at(next_epoch_start)

        start_ts = int(start_block["timestamp"])
        end_ts = int(end_block["timestamp"])
        actual_seconds = end_ts - start_ts
        actual_ratio = actual_seconds / TARGET_PERIOD_SECONDS
        observed_avg_minutes = (actual_seconds / RETARGET_INTERVALS) / 60
        difficulty = float(start_block["difficulty"])
        next_difficulty = float(next_start_block["difficulty"])
        target_change_pct = ((next_difficulty / difficulty) - 1) * 100
        expected_adjustment_factor = _clamp_adjustment_factor(1 / actual_ratio)
        expected_next_change_pct = (expected_adjustment_factor - 1) * 100

        rows.append(
            {
                "epoch_start": epoch_start,
                "epoch_end": epoch_end,
                "next_epoch_start": next_epoch_start,
                "start_date": datetime.fromtimestamp(start_ts, tz=timezone.utc),
                "difficulty": difficulty,
                "next_difficulty": next_difficulty,
                "target_change_pct": target_change_pct,
                "actual_ratio": actual_ratio,
                "expected_next_change_pct": expected_next_change_pct,
                "previous_change_pct": previous_change_pct,
                "observed_avg_block_minutes": observed_avg_minutes,
                "log_difficulty": float(np.log(difficulty)),
            }
        )
        previous_change_pct = target_change_pct

    return pd.DataFrame(rows)


def _fit_linear_regression(train_df: pd.DataFrame) -> dict[str, object]:
    x_train = train_df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y_train = train_df["target_change_pct"].to_numpy(dtype=float)

    means = x_train.mean(axis=0)
    stds = x_train.std(axis=0)
    stds[stds == 0] = 1.0
    x_scaled = (x_train - means) / stds
    design = np.column_stack([np.ones(len(x_scaled)), x_scaled])
    coefficients = np.linalg.lstsq(design, y_train, rcond=None)[0]

    return {
        "coefficients": coefficients,
        "means": means,
        "stds": stds,
    }


def _predict_change(model: dict[str, object], feature_df: pd.DataFrame) -> np.ndarray:
    x_values = feature_df[FEATURE_COLUMNS].to_numpy(dtype=float)
    x_scaled = (x_values - model["means"]) / model["stds"]
    design = np.column_stack([np.ones(len(x_scaled)), x_scaled])
    return design @ model["coefficients"]


def _evaluate_model(dataset_df: pd.DataFrame, holdout_periods: int) -> dict[str, object]:
    train_df = dataset_df.iloc[:-holdout_periods].copy()
    test_df = dataset_df.iloc[-holdout_periods:].copy()
    model = _fit_linear_regression(train_df)
    test_df["prediction_change_pct"] = _predict_change(model, test_df)
    test_df["predicted_next_difficulty"] = test_df["difficulty"] * (1 + test_df["prediction_change_pct"] / 100)
    test_df["absolute_error"] = (test_df["predicted_next_difficulty"] - test_df["next_difficulty"]).abs()
    test_df["absolute_pct_error"] = test_df["absolute_error"] / test_df["next_difficulty"] * 100

    mae = float(test_df["absolute_error"].mean())
    mape = float(test_df["absolute_pct_error"].mean())
    baseline_df = test_df.copy()
    baseline_df["baseline_next_difficulty"] = baseline_df["difficulty"] * (
        1 + baseline_df["expected_next_change_pct"] / 100
    )
    baseline_mae = float((baseline_df["baseline_next_difficulty"] - baseline_df["next_difficulty"]).abs().mean())

    return {
        "model": model,
        "train_df": train_df,
        "test_df": test_df,
        "mae": mae,
        "mape": mape,
        "baseline_mae": baseline_mae,
    }


@st.cache_data(ttl=900, show_spinner=False)
def _load_m4_snapshot(periods: int, holdout_periods: int) -> dict[str, object]:
    dataset_df = _build_completed_epoch_dataset(periods)
    evaluation = _evaluate_model(dataset_df, holdout_periods)
    full_model = _fit_linear_regression(dataset_df)
    latest_block = get_latest_block()
    mempool_adjustment = get_mempool_difficulty_adjustment()

    current_difficulty = float(latest_block["difficulty"])
    estimated_change = float(
        mempool_adjustment.get("difficultyChange")
        or mempool_adjustment.get("estimatedRetargetPercentage")
        or 0.0
    )
    latest_completed = dataset_df.iloc[-1]
    current_feature = pd.DataFrame(
        [
            {
                "log_difficulty": float(np.log(current_difficulty)),
                "actual_ratio": 1 / (1 + estimated_change / 100) if estimated_change > -99 else 1.0,
                "expected_next_change_pct": estimated_change,
                "previous_change_pct": float(latest_completed["target_change_pct"]),
                "observed_avg_block_minutes": 10 / (1 + estimated_change / 100) if estimated_change > -99 else 10.0,
            }
        ]
    )
    predicted_change = float(_predict_change(full_model, current_feature)[0])
    predicted_difficulty = current_difficulty * (1 + predicted_change / 100)
    formula_difficulty = current_difficulty * (1 + estimated_change / 100)

    return {
        "dataset_df": dataset_df,
        "evaluation": evaluation,
        "full_model": full_model,
        "latest_block": latest_block,
        "mempool_adjustment": mempool_adjustment,
        "predicted_change": predicted_change,
        "predicted_difficulty": predicted_difficulty,
        "formula_difficulty": formula_difficulty,
        "estimated_change": estimated_change,
    }


def _build_prediction_figure(test_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=test_df["next_epoch_start"],
            y=test_df["next_difficulty"],
            mode="lines+markers",
            line=dict(color=INK, width=3),
            marker=dict(size=9, color=INK),
            name="Actual next difficulty",
            hovertemplate="Retarget %{x}<br>Actual %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=test_df["next_epoch_start"],
            y=test_df["predicted_next_difficulty"],
            mode="lines+markers",
            line=dict(color=HOT, width=2, dash="dash"),
            marker=dict(size=9, color=HOT),
            name="Model prediction",
            customdata=test_df[["absolute_pct_error", "prediction_change_pct"]],
            hovertemplate=(
                "Retarget %{x}<br>"
                "Prediction %{y:,.0f}<br>"
                "Predicted change %{customdata[1]:+.2f}%<br>"
                "APE %{customdata[0]:.3f}%<extra></extra>"
            ),
        )
    )
    fig.update_layout(xaxis_title="Retarget height", yaxis_title="Difficulty")
    return fig


def _build_error_figure(test_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=test_df["next_epoch_start"].astype(str),
            y=test_df["absolute_pct_error"],
            marker_color=COOL,
            customdata=test_df[["absolute_error"]],
            hovertemplate=(
                "Retarget %{x}<br>"
                "Absolute percentage error %{y:.3f}%<br>"
                "Absolute error %{customdata[0]:,.0f}<extra></extra>"
            ),
            name="APE",
        )
    )
    fig.update_layout(xaxis_title="Retarget height", yaxis_title="Absolute percentage error (%)")
    return fig


def _build_feature_weight_figure(model: dict[str, object]) -> go.Figure:
    coefficients = model["coefficients"][1:]
    labels = [
        "log difficulty",
        "actual / target",
        "formula response",
        "previous change",
        "avg interval",
    ]
    colors = [HOT if value > 0 else COOL for value in coefficients]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=coefficients,
            marker_color=colors,
            hovertemplate="%{x}<br>Standardized coefficient %{y:.3f}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_color=INK, line_width=1)
    fig.update_layout(xaxis_title="Feature", yaxis_title="Standardized coefficient")
    return fig


def _build_residual_vector_figure(test_df: pd.DataFrame) -> go.Figure:
    """Show prediction residuals as actual-to-predicted vectors."""
    fig = go.Figure()
    max_value = max(
        float(test_df["next_difficulty"].max()),
        float(test_df["predicted_next_difficulty"].max()),
    )
    min_value = min(
        float(test_df["next_difficulty"].min()),
        float(test_df["predicted_next_difficulty"].min()),
    )

    for _, row in test_df.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[row["next_epoch_start"], row["next_epoch_start"]],
                y=[row["next_difficulty"], row["predicted_next_difficulty"]],
                mode="lines",
                line=dict(
                    color=HOT if row["predicted_next_difficulty"] > row["next_difficulty"] else COOL,
                    width=3,
                ),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=test_df["next_epoch_start"],
            y=test_df["next_difficulty"],
            mode="markers",
            marker=dict(size=13, color=INK, line=dict(color="white", width=1)),
            name="Actual",
            hovertemplate="Retarget %{x}<br>Actual %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=test_df["next_epoch_start"],
            y=test_df["predicted_next_difficulty"],
            mode="markers+text",
            marker=dict(
                size=test_df["absolute_pct_error"].mul(700).add(14),
                color=test_df["prediction_change_pct"],
                colorscale=[COOL, "#f2efe9", HOT],
                line=dict(color=INK, width=1),
                colorbar=dict(
                    title=dict(text="Predicted change (%)", font=dict(color=INK)),
                    tickfont=dict(color=MUTED),
                ),
            ),
            text=test_df["absolute_pct_error"].map(lambda value: f"{value:.3f}%"),
            textposition="top center",
            customdata=test_df[["absolute_error", "absolute_pct_error", "prediction_change_pct"]],
            hovertemplate=(
                "Retarget %{x}<br>"
                "Predicted %{y:,.0f}<br>"
                "Absolute error %{customdata[0]:,.0f}<br>"
                "APE %{customdata[1]:.3f}%<br>"
                "Predicted change %{customdata[2]:+.2f}%<extra></extra>"
            ),
            name="Prediction",
        )
    )

    padding = (max_value - min_value) * 0.08 if max_value > min_value else max_value * 0.02
    fig.update_layout(
        xaxis_title="Holdout retarget height",
        yaxis_title="Difficulty",
        yaxis_range=[min_value - padding, max_value + padding],
    )
    return fig


def render() -> None:
    """Render the M4 AI component."""
    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem; margin-bottom:1rem;">', unsafe_allow_html=True)
    st.subheader("AI difficulty predictor")
    st.caption(
        "This module trains a lightweight regression model on real completed Bitcoin retarget periods. "
        "It predicts the next difficulty adjustment percentage and evaluates the prediction with MAE and MAPE."
    )
    col_a, col_b = st.columns(2)
    periods = col_a.slider(
        "Historical completed retarget periods",
        min_value=12,
        max_value=36,
        value=24,
        step=4,
        key="m4_periods",
    )
    holdout_periods = col_b.slider(
        "Holdout periods for evaluation",
        min_value=3,
        max_value=8,
        value=5,
        step=1,
        key="m4_holdout",
    )
    st.markdown("</section>", unsafe_allow_html=True)

    if holdout_periods >= periods:
        st.error("Holdout periods must be smaller than the training dataset.")
        return

    with st.spinner("Training and evaluating the difficulty predictor on real retarget data..."):
        try:
            snapshot = _load_m4_snapshot(periods, holdout_periods)
        except Exception as exc:
            st.error(f"M4 could not train the predictor: {exc}")
            st.info("This module uses real Bitcoin retarget periods from public APIs.")
            return

    dataset_df: pd.DataFrame = snapshot["dataset_df"]
    evaluation: dict[str, object] = snapshot["evaluation"]
    test_df: pd.DataFrame = evaluation["test_df"]
    latest_block: dict = snapshot["latest_block"]

    metric_cols = st.columns(5)
    metric_cols[0].metric("Training rows", f"{len(evaluation['train_df'])}")
    metric_cols[1].metric("Holdout rows", f"{len(test_df)}")
    metric_cols[2].metric("MAE", _format_compact_number(evaluation["mae"]))
    metric_cols[3].metric("MAPE", f"{evaluation['mape']:.3f}%")
    metric_cols[4].metric("Next change", f"{snapshot['predicted_change']:+.2f}%")

    top_left, top_right = st.columns([1.15, 0.85])

    with top_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Holdout prediction check")
        prediction_fig = _build_prediction_figure(test_df)
        _apply_chart_theme(prediction_fig)
        st.plotly_chart(prediction_fig, width="stretch", config=PLOT_CONFIG)
        st.caption("Evaluation uses the most recent completed retarget periods held out from training.")
        st.markdown("</section>", unsafe_allow_html=True)

    with top_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Next retarget forecast")
        st.write(f"Current block height: **{int(latest_block['height']):,}**")
        st.write(f"Current difficulty: **{_format_compact_number(float(latest_block['difficulty']))}**")
        st.write(f"mempool.space estimate: **{snapshot['estimated_change']:+.2f}%**")
        st.write(f"Model predicted change: **{snapshot['predicted_change']:+.2f}%**")
        st.write(f"Predicted difficulty: **{_format_compact_number(snapshot['predicted_difficulty'])}**")
        st.write(f"Formula-based reference: **{_format_compact_number(snapshot['formula_difficulty'])}**")
        st.caption(
            "The model is intentionally simple and interpretable. It is evaluated on past retargets before being used for the current cycle."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    lower_left, lower_right = st.columns(2)

    with lower_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Prediction error")
        error_fig = _build_error_figure(test_df)
        _apply_chart_theme(error_fig)
        st.plotly_chart(error_fig, width="stretch", config=PLOT_CONFIG)
        st.caption("Absolute percentage error by holdout retarget period.")
        st.markdown("</section>", unsafe_allow_html=True)

    with lower_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Model feature weights")
        weight_fig = _build_feature_weight_figure(evaluation["model"])
        _apply_chart_theme(weight_fig)
        st.plotly_chart(weight_fig, width="stretch", config=PLOT_CONFIG)
        st.caption("Standardized linear-regression coefficients. Larger magnitude means stronger influence.")
        st.markdown("</section>", unsafe_allow_html=True)

    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
    st.subheader("Residual vector map")
    residual_fig = _build_residual_vector_figure(test_df)
    _apply_chart_theme(residual_fig)
    st.plotly_chart(residual_fig, width="stretch", config=PLOT_CONFIG)
    st.caption(
        "AI evaluation view: each vertical vector connects the real holdout difficulty to the model prediction. "
        "Longer vectors mean larger residual error."
    )
    st.markdown("</section>", unsafe_allow_html=True)

    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
    st.subheader("Training dataset")
    table_df = dataset_df[
        [
            "epoch_start",
            "next_epoch_start",
            "start_date",
            "difficulty",
            "next_difficulty",
            "target_change_pct",
            "actual_ratio",
            "expected_next_change_pct",
            "previous_change_pct",
        ]
    ].copy()
    table_df["start_date"] = table_df["start_date"].dt.strftime("%Y-%m-%d")
    table_df = table_df.rename(
        columns={
            "epoch_start": "Measured period start",
            "next_epoch_start": "Predicted retarget height",
            "start_date": "Period start date",
            "difficulty": "Difficulty at start",
            "next_difficulty": "Next difficulty",
            "target_change_pct": "Actual next change (%)",
            "actual_ratio": "Actual / target",
            "expected_next_change_pct": "Formula response (%)",
            "previous_change_pct": "Previous change (%)",
        }
    )
    st.dataframe(table_df, width="stretch", hide_index=True)
    st.caption(
        "Every training row is a completed 2016-block period. The label is the difficulty change applied at the next retarget."
    )
    st.markdown("</section>", unsafe_allow_html=True)
