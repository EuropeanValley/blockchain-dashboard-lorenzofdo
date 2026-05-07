"""Module M7: second AI approach using inter-block anomaly detection."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import get_recent_blocks


PLOT_BG = "rgba(255,255,255,0.84)"
PAPER_BG = "rgba(255,255,255,0)"
INK = "#0b0c0d"
MUTED = "#595b57"
ACCENT = "#d8ff45"
COOL = "#5477b8"
HOT = "#f46b45"
PLOT_CONFIG = {"displaylogo": False, "displayModeBar": False, "responsive": True}


def _apply_chart_theme(fig: go.Figure, title_text: str | None = None) -> go.Figure:
    layout_kwargs = {
        "paper_bgcolor": PAPER_BG,
        "plot_bgcolor": PLOT_BG,
        "font": {"family": "Archivo, sans-serif", "color": INK, "size": 13},
        "margin": {"l": 24, "r": 24, "t": 34, "b": 28},
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


def _build_intervals_dataframe(blocks: list[dict]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for newer, older in zip(blocks, blocks[1:]):
        interval_seconds = int(newer["timestamp"]) - int(older["timestamp"])
        rows.append(
            {
                "height": int(newer["height"]),
                "block_hash": str(newer["id"]),
                "timestamp": datetime.fromtimestamp(int(newer["timestamp"]), tz=timezone.utc),
                "interval_seconds": max(interval_seconds, 0),
                "interval_minutes": max(interval_seconds, 0) / 60,
                "tx_count": int(newer.get("tx_count", 0)),
                "size": int(newer.get("size", 0)),
                "weight": int(newer.get("weight", 0)),
            }
        )

    return pd.DataFrame(rows).sort_values("height").reset_index(drop=True)


def _fit_exponential_detector(train_df: pd.DataFrame) -> dict[str, float]:
    mean_seconds = max(float(train_df["interval_seconds"].mean()), 1.0)
    return {"mean_seconds": mean_seconds, "rate": 1.0 / mean_seconds}


def _score_intervals(interval_df: pd.DataFrame, model: dict[str, float], alpha: float) -> pd.DataFrame:
    df = interval_df.copy()
    mean_seconds = model["mean_seconds"]
    x = df["interval_seconds"].astype(float).clip(lower=0)
    cdf = 1 - np.exp(-x / mean_seconds)
    lower_tail = cdf
    upper_tail = np.exp(-x / mean_seconds)
    two_tail_p = np.minimum(1.0, 2 * np.minimum(lower_tail, upper_tail))
    df["expected_cdf"] = cdf
    df["tail_probability"] = two_tail_p
    df["anomaly_score"] = -np.log10(np.maximum(two_tail_p, 1e-12))
    df["is_anomaly"] = two_tail_p < alpha
    return df


def _evaluate_detector(test_df: pd.DataFrame, model: dict[str, float]) -> dict[str, float]:
    if test_df.empty:
        return {"ks_statistic": 0.0, "mean_nll": 0.0, "mean_interval": 0.0}

    mean_seconds = model["mean_seconds"]
    sorted_seconds = np.sort(test_df["interval_seconds"].to_numpy(dtype=float))
    n = len(sorted_seconds)
    empirical_cdf = np.arange(1, n + 1) / n
    expected_cdf = 1 - np.exp(-sorted_seconds / mean_seconds)
    ks_statistic = float(np.max(np.abs(empirical_cdf - expected_cdf)))
    mean_nll = float(np.mean(np.log(mean_seconds) + sorted_seconds / mean_seconds))

    return {
        "ks_statistic": ks_statistic,
        "mean_nll": mean_nll,
        "mean_interval": float(test_df["interval_seconds"].mean()),
    }


@st.cache_data(ttl=60, show_spinner=False)
def _load_m7_snapshot(block_count: int) -> dict[str, object]:
    blocks = get_recent_blocks(limit=block_count + 1)
    intervals_df = _build_intervals_dataframe(blocks)
    return {"blocks": blocks, "intervals_df": intervals_df}


def _build_timeline_figure(scored_df: pd.DataFrame, mean_seconds: float) -> go.Figure:
    normal_df = scored_df[~scored_df["is_anomaly"]]
    anomaly_df = scored_df[scored_df["is_anomaly"]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=normal_df["height"],
            y=normal_df["interval_minutes"],
            mode="lines+markers",
            line=dict(color="rgba(11,12,13,0.35)", width=2),
            marker=dict(size=7, color=COOL, line=dict(color=INK, width=0.7)),
            name="Normal interval",
            customdata=normal_df[["tail_probability", "anomaly_score", "tx_count"]],
            hovertemplate=(
                "Block %{x}<br>"
                "Interval %{y:.2f} min<br>"
                "p-value %{customdata[0]:.4f}<br>"
                "score %{customdata[1]:.2f}<br>"
                "Transactions %{customdata[2]}<extra></extra>"
            ),
        )
    )
    if not anomaly_df.empty:
        fig.add_trace(
            go.Scatter(
                x=anomaly_df["height"],
                y=anomaly_df["interval_minutes"],
                mode="markers+text",
                marker=dict(size=15, color=HOT, line=dict(color=INK, width=1.2)),
                text=anomaly_df["anomaly_score"].map(lambda value: f"{value:.1f}"),
                textposition="top center",
                name="Anomaly",
                customdata=anomaly_df[["tail_probability", "anomaly_score", "tx_count"]],
                hovertemplate=(
                    "Block %{x}<br>"
                    "Interval %{y:.2f} min<br>"
                    "p-value %{customdata[0]:.4f}<br>"
                    "score %{customdata[1]:.2f}<br>"
                    "Transactions %{customdata[2]}<extra></extra>"
                ),
            )
        )

    fig.add_hline(
        y=mean_seconds / 60,
        line_color=ACCENT,
        line_dash="dash",
        annotation_text="trained mean interval",
        annotation_position="top right",
    )
    fig.update_layout(xaxis_title="Block height", yaxis_title="Minutes between blocks")
    return fig


def _build_score_histogram(scored_df: pd.DataFrame, threshold_score: float) -> go.Figure:
    fig = go.Figure(
        go.Histogram(
            x=scored_df["anomaly_score"],
            nbinsx=24,
            marker_color=INK,
            opacity=0.9,
            hovertemplate="Score %{x:.2f}<br>Count %{y}<extra></extra>",
            name="Scores",
        )
    )
    fig.add_vline(
        x=threshold_score,
        line_color=HOT,
        line_dash="dash",
        annotation_text="threshold",
        annotation_position="top right",
    )
    fig.update_layout(xaxis_title="-log10(two-sided p-value)", yaxis_title="Block count", showlegend=False)
    return fig


def _build_qq_figure(test_df: pd.DataFrame, mean_seconds: float) -> go.Figure:
    if test_df.empty:
        return go.Figure()

    observed = np.sort(test_df["interval_seconds"].to_numpy(dtype=float)) / 60
    n = len(observed)
    probabilities = (np.arange(1, n + 1) - 0.5) / n
    theoretical = -mean_seconds * np.log(1 - probabilities) / 60
    max_value = max(float(observed.max()), float(theoretical.max()), 1.0)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=theoretical,
            y=observed,
            mode="markers",
            marker=dict(size=8, color=COOL, line=dict(color=INK, width=0.8)),
            hovertemplate="Expected %{x:.2f} min<br>Observed %{y:.2f} min<extra></extra>",
            name="Intervals",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[0, max_value],
            y=[0, max_value],
            mode="lines",
            line=dict(color=INK, width=2, dash="dot"),
            name="Ideal exponential fit",
            hoverinfo="skip",
        )
    )
    fig.update_layout(xaxis_title="Theoretical exponential quantile (min)", yaxis_title="Observed quantile (min)")
    return fig


def _build_comparison_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Module": "M4",
                "AI approach": "Supervised regression",
                "Target": "Next difficulty adjustment",
                "Training data": "Completed 2016-block retarget periods",
                "Evaluation": "MAE and MAPE on holdout retargets",
            },
            {
                "Module": "M7",
                "AI approach": "Unsupervised anomaly detector",
                "Target": "Abnormal inter-block intervals",
                "Training data": "Recent block intervals fitted to an exponential baseline",
                "Evaluation": "KS statistic, negative log-likelihood, anomaly rate",
            },
        ]
    )


def render() -> None:
    """Render the M7 second AI approach."""
    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem; margin-bottom:1rem;">', unsafe_allow_html=True)
    st.subheader("Second AI approach: anomaly detector")
    st.caption(
        "Optional M7 uses a different AI method from M4. It fits an exponential baseline to Bitcoin inter-block times and flags statistically unusual blocks."
    )
    controls = st.columns(3)
    block_count = controls[0].slider(
        "Recent intervals to analyze",
        min_value=80,
        max_value=300,
        value=180,
        step=20,
        key="m7_block_count",
    )
    train_fraction = controls[1].slider(
        "Training fraction",
        min_value=0.50,
        max_value=0.85,
        value=0.70,
        step=0.05,
        key="m7_train_fraction",
    )
    alpha = controls[2].slider(
        "Anomaly threshold p-value",
        min_value=0.01,
        max_value=0.10,
        value=0.05,
        step=0.01,
        key="m7_alpha",
    )
    st.markdown("</section>", unsafe_allow_html=True)

    with st.spinner("Training the inter-block anomaly detector on live Bitcoin data..."):
        try:
            snapshot = _load_m7_snapshot(block_count)
        except Exception as exc:
            st.error(f"M7 could not load recent block intervals: {exc}")
            st.info("This module needs recent block timestamps from an Esplora-compatible public API.")
            return

    intervals_df: pd.DataFrame = snapshot["intervals_df"]
    if len(intervals_df) < 20:
        st.error("Not enough block intervals were returned to train the anomaly detector.")
        return

    split_index = max(10, min(len(intervals_df) - 5, int(len(intervals_df) * train_fraction)))
    train_df = intervals_df.iloc[:split_index].copy()
    test_df = intervals_df.iloc[split_index:].copy()
    model = _fit_exponential_detector(train_df)
    scored_df = _score_intervals(intervals_df, model, alpha)
    scored_test_df = scored_df.iloc[split_index:].copy()
    metrics = _evaluate_detector(scored_test_df, model)
    threshold_score = -math.log10(alpha)
    anomaly_count = int(scored_df["is_anomaly"].sum())
    anomaly_rate = anomaly_count / len(scored_df) * 100

    metric_cols = st.columns(6)
    metric_cols[0].metric("Training rows", f"{len(train_df)}")
    metric_cols[1].metric("Test rows", f"{len(test_df)}")
    metric_cols[2].metric("Mean interval", f"{model['mean_seconds'] / 60:.2f} min")
    metric_cols[3].metric("KS statistic", f"{metrics['ks_statistic']:.3f}")
    metric_cols[4].metric("Mean NLL", f"{metrics['mean_nll']:.2f}")
    metric_cols[5].metric("Anomaly rate", f"{anomaly_rate:.1f}%")

    top_left, top_right = st.columns([1.28, 0.72])
    with top_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Detected interval anomalies")
        timeline_fig = _build_timeline_figure(scored_df, model["mean_seconds"])
        _apply_chart_theme(timeline_fig)
        st.plotly_chart(timeline_fig, width="stretch", config=PLOT_CONFIG)
        st.caption("Red points are intervals whose two-sided exponential tail probability is below the selected threshold.")
        st.markdown("</section>", unsafe_allow_html=True)

    with top_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Model interpretation")
        st.write("Expected distribution:")
        st.code("P(T > t) = exp(-t / mean_interval)", language="text")
        st.write(f"Trained mean interval: **{model['mean_seconds'] / 60:.2f} min**")
        st.write(f"Decision threshold: **p < {alpha:.2f}**")
        st.write(f"Score threshold: **{threshold_score:.2f}**")
        st.caption(
            "Very short and very long intervals can both be unusual. The model scores both tails rather than only slow blocks."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    lower_left, lower_right = st.columns(2)
    with lower_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Score distribution")
        score_fig = _build_score_histogram(scored_df, threshold_score)
        _apply_chart_theme(score_fig)
        st.plotly_chart(score_fig, width="stretch", config=PLOT_CONFIG)
        st.caption("Higher scores mean lower probability under the trained exponential baseline.")
        st.markdown("</section>", unsafe_allow_html=True)

    with lower_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Exponential fit check")
        qq_fig = _build_qq_figure(scored_test_df, model["mean_seconds"])
        _apply_chart_theme(qq_fig)
        st.plotly_chart(qq_fig, width="stretch", config=PLOT_CONFIG)
        st.caption("If recent block intervals followed the fitted exponential model perfectly, points would follow the dotted diagonal.")
        st.markdown("</section>", unsafe_allow_html=True)

    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
    st.subheader("M4 vs M7 AI comparison")
    st.dataframe(_build_comparison_table(), width="stretch", hide_index=True)
    st.caption("M7 is intentionally a different AI approach: unsupervised detection instead of supervised prediction.")
    st.markdown("</section>", unsafe_allow_html=True)

    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
    st.subheader("Anomaly table")
    table_df = scored_df[scored_df["is_anomaly"]].copy()
    if table_df.empty:
        st.success("No intervals crossed the selected anomaly threshold.")
    else:
        table_df["timestamp"] = table_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        table_df = table_df[
            [
                "height",
                "timestamp",
                "interval_minutes",
                "tail_probability",
                "anomaly_score",
                "tx_count",
                "block_hash",
            ]
        ].rename(
            columns={
                "height": "Block height",
                "timestamp": "Timestamp",
                "interval_minutes": "Interval (min)",
                "tail_probability": "Two-sided p-value",
                "anomaly_score": "Anomaly score",
                "tx_count": "Transactions",
                "block_hash": "Block hash",
            }
        )
        st.dataframe(table_df, width="stretch", hide_index=True)
    st.markdown("</section>", unsafe_allow_html=True)
