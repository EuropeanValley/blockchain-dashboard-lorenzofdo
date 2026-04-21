"""Module M3: Difficulty History."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import (
    get_block_at_height,
    get_difficulty_history,
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


def _format_days(seconds: float) -> str:
    return f"{seconds / 86_400:.2f} days"


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


def _build_epoch_dataframe(periods: int) -> pd.DataFrame:
    latest_block = get_latest_block()
    latest_height = int(latest_block["height"])
    current_epoch_start = latest_height - (latest_height % RETARGET_BLOCKS)
    last_complete_epoch_start = current_epoch_start - RETARGET_BLOCKS
    first_epoch_start = max(0, last_complete_epoch_start - (periods - 1) * RETARGET_BLOCKS)

    rows: list[dict[str, object]] = []
    previous_difficulty: float | None = None

    for epoch_start in range(first_epoch_start, last_complete_epoch_start + 1, RETARGET_BLOCKS):
        epoch_end = epoch_start + RETARGET_BLOCKS - 1
        start_block = get_block_at_height(epoch_start)
        end_block = get_block_at_height(epoch_end)

        start_ts = int(start_block["timestamp"])
        end_ts = int(end_block["timestamp"])
        actual_seconds = end_ts - start_ts
        consensus_ratio = actual_seconds / TARGET_PERIOD_SECONDS
        observed_avg_interval_seconds = actual_seconds / RETARGET_INTERVALS
        difficulty = float(start_block["difficulty"])
        difficulty_change_pct = (
            ((difficulty / previous_difficulty) - 1) * 100 if previous_difficulty else 0.0
        )
        difficulty_change_for_chart = (
            ((difficulty / previous_difficulty) - 1) * 100 if previous_difficulty else None
        )
        expected_adjustment_factor = _clamp_adjustment_factor(1 / consensus_ratio)
        expected_next_change_pct = (expected_adjustment_factor - 1) * 100

        rows.append(
            {
                "epoch_start": epoch_start,
                "epoch_end": epoch_end,
                "retarget_height": epoch_start,
                "start_date": datetime.fromtimestamp(start_ts, tz=timezone.utc),
                "end_date": datetime.fromtimestamp(end_ts, tz=timezone.utc),
                "difficulty": difficulty,
                "difficulty_change_pct": difficulty_change_pct,
                "difficulty_change_for_chart": difficulty_change_for_chart,
                "actual_seconds": actual_seconds,
                "actual_days": actual_seconds / 86_400,
                "actual_ratio": consensus_ratio,
                "observed_avg_block_minutes": observed_avg_interval_seconds / 60,
                "avg_block_minutes": observed_avg_interval_seconds / 60,
                "expected_adjustment_factor": expected_adjustment_factor,
                "expected_next_change_pct": expected_next_change_pct,
                "speed_label": "slower than target" if consensus_ratio > 1 else "faster than target",
            }
        )
        previous_difficulty = difficulty

    epoch_df = pd.DataFrame(rows)
    if not epoch_df.empty:
        current_epoch_block = get_block_at_height(current_epoch_start)
        current_difficulty = float(current_epoch_block["difficulty"])
        epoch_df["next_difficulty_change_pct"] = epoch_df["difficulty_change_pct"].shift(-1)
        epoch_df.loc[epoch_df.index[-1], "next_difficulty_change_pct"] = (
            (current_difficulty / float(epoch_df.iloc[-1]["difficulty"])) - 1
        ) * 100
        epoch_df["next_retarget_height"] = epoch_df["epoch_start"] + RETARGET_BLOCKS

    return epoch_df


@st.cache_data(ttl=600, show_spinner=False)
def _load_m3_snapshot(periods: int) -> dict[str, object]:
    epoch_df = _build_epoch_dataframe(periods)
    difficulty_history = get_difficulty_history("1year")
    mempool_adjustment = get_mempool_difficulty_adjustment()
    latest_block = get_latest_block()
    return {
        "epoch_df": epoch_df,
        "difficulty_history": difficulty_history,
        "mempool_adjustment": mempool_adjustment,
        "latest_block": latest_block,
    }


def _build_difficulty_figure(epoch_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=epoch_df["start_date"],
            y=epoch_df["difficulty"],
            mode="lines+markers",
            line=dict(color=INK, width=3),
            marker=dict(
                size=epoch_df["actual_ratio"].sub(1).abs().mul(90).add(9),
                color=epoch_df["actual_ratio"],
                colorscale=[COOL, "#f2efe9", HOT],
                cmin=0.92,
                cmax=1.08,
                line=dict(color=INK, width=1),
                colorbar=dict(
                    title=dict(text="Actual / target time", font=dict(color=INK)),
                    tickfont=dict(color=MUTED),
                ),
            ),
            customdata=epoch_df[["epoch_start", "epoch_end", "actual_days", "actual_ratio", "difficulty_change_pct"]],
            hovertemplate=(
                "Retarget height %{customdata[0]}<br>"
                "Period %{customdata[0]}-%{customdata[1]}<br>"
                "Difficulty %{y:,.0f}<br>"
                "Actual time %{customdata[2]:.2f} days<br>"
                "Actual / target %{customdata[3]:.3f}<br>"
                "Difficulty change %{customdata[4]:+.2f}%<extra></extra>"
            ),
            name="Difficulty at retarget",
        )
    )

    for _, row in epoch_df.iterrows():
        fig.add_vline(
            x=row["start_date"],
            line_width=1,
            line_dash="dot",
            line_color="rgba(11,12,13,0.18)",
        )

    fig.update_layout(xaxis_title="Retarget date", yaxis_title="Difficulty")
    return fig


def _build_ratio_figure(epoch_df: pd.DataFrame) -> go.Figure:
    colors = [HOT if value > 1 else COOL for value in epoch_df["actual_ratio"]]
    fig = go.Figure(
        go.Bar(
            x=epoch_df["retarget_height"].astype(str),
            y=epoch_df["actual_ratio"],
            marker_color=colors,
            customdata=epoch_df[["actual_days", "avg_block_minutes", "speed_label"]],
            hovertemplate=(
                "Retarget height %{x}<br>"
                "Actual / target %{y:.3f}<br>"
                "Actual duration %{customdata[0]:.2f} days<br>"
                "Avg block time %{customdata[1]:.2f} min<br>"
                "%{customdata[2]}<extra></extra>"
            ),
            name="Timing ratio",
        )
    )
    fig.add_hline(
        y=1,
        line_dash="dash",
        line_color=ACCENT,
        annotation_text="target = 1.00",
        annotation_position="top right",
    )
    fig.update_layout(xaxis_title="Retarget height", yaxis_title="Actual period time / target")
    return fig


def _build_change_figure(epoch_df: pd.DataFrame) -> go.Figure:
    if "difficulty_change_for_chart" not in epoch_df.columns:
        epoch_df = epoch_df.copy()
        epoch_df["difficulty_change_for_chart"] = epoch_df["difficulty_change_pct"]
        if not epoch_df.empty:
            epoch_df.loc[epoch_df.index[0], "difficulty_change_for_chart"] = None
    if "expected_next_change_pct" not in epoch_df.columns:
        epoch_df = epoch_df.copy()
        epoch_df["expected_next_change_pct"] = epoch_df["actual_ratio"].apply(
            lambda ratio: (_clamp_adjustment_factor(1 / ratio) - 1) * 100
        )

    change_df = epoch_df.dropna(subset=["difficulty_change_for_chart"]).copy()
    if change_df.empty:
        return go.Figure()

    colors = [HOT if value > 0 else COOL for value in change_df["difficulty_change_for_chart"]]
    fig = go.Figure(
        go.Bar(
            x=change_df["retarget_height"].astype(str),
            y=change_df["difficulty_change_for_chart"],
            marker_color=colors,
            customdata=change_df[["difficulty", "actual_ratio", "expected_next_change_pct"]],
            hovertemplate=(
                "Retarget height %{x}<br>"
                "Difficulty change %{y:+.2f}%<br>"
                "Difficulty %{customdata[0]:,.0f}<br>"
                "Actual / target %{customdata[1]:.3f}<br>"
                "Expected next response %{customdata[2]:+.2f}%<extra></extra>"
            ),
            name="Difficulty change",
        )
    )
    fig.add_hline(y=0, line_color=INK, line_width=1)
    fig.update_layout(xaxis_title="Retarget height", yaxis_title="Difficulty change (%)")
    return fig


def _build_history_context_figure(history_values: list[dict]) -> go.Figure:
    history_df = pd.DataFrame(history_values)
    if history_df.empty:
        return go.Figure()

    history_df["date"] = pd.to_datetime(history_df["x"], unit="s", utc=True)
    history_df["difficulty"] = history_df["y"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=history_df["date"],
            y=history_df["difficulty"],
            mode="lines",
            line=dict(color=INK, width=3),
            fill="tozeroy",
            fillcolor="rgba(148,173,214,0.18)",
            name="Blockchain.com difficulty",
            hovertemplate="%{x}<br>Difficulty %{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(showlegend=False, xaxis_title="Date", yaxis_title="Difficulty")
    return fig


def _build_epoch_strip_figure(epoch_df: pd.DataFrame) -> go.Figure:
    colors = [HOT if value > 1 else COOL for value in epoch_df["actual_ratio"]]
    fig = go.Figure(
        go.Scatter(
            x=epoch_df["retarget_height"],
            y=[1] * len(epoch_df),
            mode="markers",
            marker=dict(
                size=epoch_df["actual_ratio"].sub(1).abs().mul(220).add(22),
                color=colors,
                line=dict(color=INK, width=1),
                symbol="square",
            ),
            customdata=epoch_df[["actual_ratio", "avg_block_minutes", "difficulty_change_pct"]],
            hovertemplate=(
                "Retarget height %{x}<br>"
                "Actual / target %{customdata[0]:.3f}<br>"
                "Avg block time %{customdata[1]:.2f} min<br>"
                "Difficulty change %{customdata[2]:+.2f}%<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig.update_layout(
        xaxis_title="Retarget height",
        yaxis=dict(showticklabels=False, visible=False, range=[0.85, 1.15]),
        margin=dict(l=10, r=10, t=15, b=20),
    )
    return fig


def _build_response_figure(epoch_df: pd.DataFrame) -> go.Figure:
    if "next_difficulty_change_pct" not in epoch_df.columns:
        epoch_df = epoch_df.copy()
        epoch_df["next_difficulty_change_pct"] = epoch_df["difficulty_change_pct"].shift(-1)
    if "expected_next_change_pct" not in epoch_df.columns:
        epoch_df = epoch_df.copy()
        epoch_df["expected_next_change_pct"] = epoch_df["actual_ratio"].apply(
            lambda ratio: (_clamp_adjustment_factor(1 / ratio) - 1) * 100
        )
    if "next_retarget_height" not in epoch_df.columns:
        epoch_df = epoch_df.copy()
        epoch_df["next_retarget_height"] = epoch_df["epoch_start"] + RETARGET_BLOCKS
    if "observed_avg_block_minutes" not in epoch_df.columns:
        epoch_df = epoch_df.copy()
        epoch_df["observed_avg_block_minutes"] = epoch_df.get(
            "avg_block_minutes",
            (epoch_df["actual_seconds"] / RETARGET_INTERVALS) / 60,
        )

    response_df = epoch_df.dropna(subset=["next_difficulty_change_pct"]).copy()
    if response_df.empty:
        return go.Figure()

    colors = [HOT if value > 1 else COOL for value in response_df["actual_ratio"]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=response_df["actual_ratio"],
            y=response_df["next_difficulty_change_pct"],
            mode="markers+text",
            marker=dict(
                size=response_df["difficulty"].rank(pct=True).mul(24).add(12),
                color=colors,
                line=dict(color=INK, width=1),
            ),
            text=response_df["retarget_height"].astype(str),
            textposition="top center",
            customdata=response_df[
                [
                    "epoch_start",
                    "epoch_end",
                    "next_retarget_height",
                    "observed_avg_block_minutes",
                    "expected_next_change_pct",
                ]
            ],
            hovertemplate=(
                "Measured period %{customdata[0]}-%{customdata[1]}<br>"
                "Next retarget height %{customdata[2]}<br>"
                "Actual / target %{x:.3f}<br>"
                "Avg block time %{customdata[3]:.2f} min<br>"
                "Expected change %{customdata[4]:+.2f}%<br>"
                "Observed next change %{y:+.2f}%<extra></extra>"
            ),
            name="Observed next retarget",
        )
    )

    min_ratio = max(0.88, float(response_df["actual_ratio"].min()) - 0.02)
    max_ratio = min(1.12, float(response_df["actual_ratio"].max()) + 0.02)
    curve_x = [min_ratio + (max_ratio - min_ratio) * index / 80 for index in range(81)]
    curve_y = [(_clamp_adjustment_factor(1 / value) - 1) * 100 for value in curve_x]
    fig.add_trace(
        go.Scatter(
            x=curve_x,
            y=curve_y,
            mode="lines",
            line=dict(color=INK, width=2, dash="dot"),
            name="Ideal formula response",
            hovertemplate="Ratio %{x:.3f}<br>Expected change %{y:+.2f}%<extra></extra>",
        )
    )

    fig.add_vline(
        x=1,
        line_dash="dash",
        line_color=ACCENT,
        annotation_text="target timing",
        annotation_position="top right",
    )
    fig.add_hline(y=0, line_color="rgba(11,12,13,0.32)", line_width=1)
    fig.update_layout(
        xaxis_title="Actual period time / target period time",
        yaxis_title="Next difficulty change (%)",
    )
    return fig


def render() -> None:
    """Render the M3 dashboard panel."""
    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem; margin-bottom:1rem;">', unsafe_allow_html=True)
    st.subheader("Difficulty history")
    st.caption(
        "This module studies Bitcoin difficulty across 2016-block retarget periods. "
        "Each period compares real elapsed block time against the protocol target of 600 seconds per block."
    )
    periods = st.slider(
        "Completed retarget periods to analyze",
        min_value=4,
        max_value=12,
        value=8,
        step=1,
        key="m3_periods",
    )
    st.markdown("</section>", unsafe_allow_html=True)

    with st.spinner("Loading difficulty periods from live Bitcoin block data..."):
        try:
            snapshot = _load_m3_snapshot(periods)
        except Exception as exc:
            st.error(f"M3 could not load difficulty history: {exc}")
            st.info("This module uses real block timestamps and difficulty values from public APIs.")
            return

    epoch_df: pd.DataFrame = snapshot["epoch_df"]
    history_values: list[dict] = snapshot["difficulty_history"]
    mempool_adjustment: dict = snapshot["mempool_adjustment"]
    latest_block: dict = snapshot["latest_block"]

    if "difficulty_change_for_chart" not in epoch_df.columns:
        epoch_df["difficulty_change_for_chart"] = epoch_df["difficulty_change_pct"]
        if not epoch_df.empty:
            epoch_df.loc[epoch_df.index[0], "difficulty_change_for_chart"] = None
    if "observed_avg_block_minutes" not in epoch_df.columns:
        epoch_df["observed_avg_block_minutes"] = (epoch_df["actual_seconds"] / RETARGET_INTERVALS) / 60
    if "expected_next_change_pct" not in epoch_df.columns:
        epoch_df["expected_next_change_pct"] = epoch_df["actual_ratio"].apply(
            lambda ratio: (_clamp_adjustment_factor(1 / ratio) - 1) * 100
        )
    if "next_retarget_height" not in epoch_df.columns:
        epoch_df["next_retarget_height"] = epoch_df["epoch_start"] + RETARGET_BLOCKS
    if "next_difficulty_change_pct" not in epoch_df.columns:
        current_difficulty = float(latest_block["difficulty"])
        epoch_df["next_difficulty_change_pct"] = epoch_df["difficulty_change_pct"].shift(-1)
        if not epoch_df.empty:
            epoch_df.loc[epoch_df.index[-1], "next_difficulty_change_pct"] = (
                (current_difficulty / float(epoch_df.iloc[-1]["difficulty"])) - 1
            ) * 100

    latest_height = int(latest_block["height"])
    current_epoch_progress = latest_height % RETARGET_BLOCKS
    remaining_blocks = mempool_adjustment.get("remainingBlocks", RETARGET_BLOCKS - current_epoch_progress)
    estimated_retarget = (
        mempool_adjustment.get("difficultyChange")
        or mempool_adjustment.get("estimatedRetargetPercentage")
        or 0.0
    )
    latest_period = epoch_df.iloc[-1]

    metric_cols = st.columns(5)
    metric_cols[0].metric("Latest height", f"{latest_height:,}")
    metric_cols[1].metric("Current epoch", f"{current_epoch_progress:,} / {RETARGET_BLOCKS}")
    metric_cols[2].metric("Blocks to retarget", f"{int(remaining_blocks):,}")
    metric_cols[3].metric("Last period ratio", f"{float(latest_period['actual_ratio']):.3f}")
    metric_cols[4].metric("Est. next retarget", f"{float(estimated_retarget):+.2f}%")

    top_left, top_right = st.columns([1.25, 0.75])

    with top_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Difficulty at retarget events")
        difficulty_fig = _build_difficulty_figure(epoch_df)
        _apply_chart_theme(difficulty_fig)
        st.plotly_chart(difficulty_fig, width="stretch", config=PLOT_CONFIG)
        st.caption(
            "Each marker is a real retarget boundary. Marker size and color show how far the previous 2016-block period was from the two-week target."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    with top_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Retarget formula link")
        st.write(f"Blocks per period: **{RETARGET_BLOCKS:,}**")
        st.write(f"Target block time: **{TARGET_BLOCK_SECONDS} s**")
        st.write(f"Target period time: **{_format_days(TARGET_PERIOD_SECONDS)}**")
        st.write(f"Consensus clamp: **{MIN_ADJUSTMENT_FACTOR}x to {MAX_ADJUSTMENT_FACTOR}x**")
        st.write("Ratio shown:")
        st.code("actual_period_time / (2016 * 600)", language="text")
        st.write(
            "If blocks arrive faster than expected, the ratio is below `1`, "
            "so the formula tends to increase difficulty. Bitcoin also clamps extreme adjustments."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    mid_left, mid_right = st.columns(2)

    with mid_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Actual time vs target")
        ratio_fig = _build_ratio_figure(epoch_df)
        _apply_chart_theme(ratio_fig)
        st.plotly_chart(ratio_fig, width="stretch", config=PLOT_CONFIG)
        st.caption("Bars above 1 mean the 2016-block period was slower than target; bars below 1 mean faster mining.")
        st.markdown("</section>", unsafe_allow_html=True)

    with mid_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Difficulty adjustment movement")
        change_fig = _build_change_figure(epoch_df)
        _apply_chart_theme(change_fig)
        st.plotly_chart(change_fig, width="stretch", config=PLOT_CONFIG)
        st.caption("Percent change in difficulty at each retarget boundary compared with the previous completed period.")
        st.markdown("</section>", unsafe_allow_html=True)

    lower_left, lower_right = st.columns([0.9, 1.1])

    with lower_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Retarget rhythm strip")
        strip_fig = _build_epoch_strip_figure(epoch_df)
        _apply_chart_theme(strip_fig)
        st.plotly_chart(strip_fig, width="stretch", config=PLOT_CONFIG)
        st.caption(
            "Compact visual scan of the periods: blue means faster-than-target periods, red means slower-than-target periods."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    with lower_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("One-year context")
        history_fig = _build_history_context_figure(history_values)
        if history_fig.data:
            _apply_chart_theme(history_fig)
            st.plotly_chart(history_fig, width="stretch", config=PLOT_CONFIG)
        else:
            st.warning("Blockchain.com did not return historical difficulty context.")
        st.caption("Broader historical context from Blockchain.com Charts API.")
        st.markdown("</section>", unsafe_allow_html=True)

    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
    st.subheader("Retarget response map")
    response_fig = _build_response_figure(epoch_df)
    _apply_chart_theme(response_fig)
    st.plotly_chart(response_fig, width="stretch", config=PLOT_CONFIG)
    st.caption(
        "This chart links theory to data: the x-axis is how fast a completed 2016-block period was, "
        "and the y-axis is the difficulty change applied at the next retarget. The dotted curve is the ideal formula response."
    )
    st.markdown("</section>", unsafe_allow_html=True)

    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
    st.subheader("Completed retarget periods")
    table_df = epoch_df[
        [
            "epoch_start",
            "epoch_end",
            "start_date",
            "difficulty",
            "difficulty_change_for_chart",
            "expected_next_change_pct",
            "next_difficulty_change_pct",
            "actual_days",
            "actual_ratio",
            "observed_avg_block_minutes",
        ]
    ].copy()
    table_df["start_date"] = table_df["start_date"].dt.strftime("%Y-%m-%d")
    table_df = table_df.rename(
        columns={
            "epoch_start": "Start height",
            "epoch_end": "End height",
            "start_date": "Retarget date",
            "difficulty": "Difficulty",
            "difficulty_change_for_chart": "Applied difficulty change (%)",
            "expected_next_change_pct": "Formula response for next (%)",
            "next_difficulty_change_pct": "Observed next change (%)",
            "actual_days": "Actual period days",
            "actual_ratio": "Actual / target",
            "observed_avg_block_minutes": "Observed avg interval (min)",
        }
    )
    st.dataframe(table_df, width="stretch", hide_index=True)
    st.caption(
        "The timing ratio uses real timestamps from the first and last blocks in each completed retarget period."
    )
    st.markdown("</section>", unsafe_allow_html=True)
