"""Module M1: Proof of Work Monitor."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import (
    bits_to_target,
    count_leading_zero_bits,
    estimate_hashrate_from_difficulty,
    get_blockchain_stats,
    get_difficulty_history,
    get_latest_block,
    get_latest_block_hash,
    get_mempool_difficulty_adjustment,
    get_recent_blocks,
    target_to_hex,
)


PLOT_BG = "rgba(255,255,255,0.84)"
PAPER_BG = "rgba(255,255,255,0)"
INK = "#0b0c0d"
MUTED = "#595b57"
ACCENT = "#d8ff45"
ACCENT_SOFT = "#94add6"
HOT = "#f46b45"
COOL = "#5477b8"
PLOT_CONFIG = {"displaylogo": False, "displayModeBar": False, "responsive": True}


def _format_hashrate(hashrate_hps: float) -> str:
    units = ["H/s", "kH/s", "MH/s", "GH/s", "TH/s", "PH/s", "EH/s", "ZH/s"]
    value = float(hashrate_hps)
    unit_index = 0

    while value >= 1000 and unit_index < len(units) - 1:
        value /= 1000
        unit_index += 1

    return f"{value:,.2f} {units[unit_index]}"


def _format_compact_number(value: float) -> str:
    units = ["", "K", "M", "B", "T", "P"]
    number = float(value)
    unit_index = 0

    while abs(number) >= 1000 and unit_index < len(units) - 1:
        number /= 1000
        unit_index += 1

    suffix = units[unit_index]
    return f"{number:,.2f}{suffix}" if suffix else f"{number:,.0f}"


def _safe_get(mapping: dict, *keys: str):
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _build_intervals_dataframe(blocks: list[dict]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for newer, older in zip(blocks, blocks[1:]):
        interval_seconds = int(newer["timestamp"]) - int(older["timestamp"])
        rows.append(
            {
                "height": int(newer["height"]),
                "block_hash": newer["id"],
                "timestamp": datetime.fromtimestamp(int(newer["timestamp"]), tz=timezone.utc),
                "interval_seconds": interval_seconds,
                "interval_minutes": interval_seconds / 60,
                "interval_deviation": interval_seconds - 600,
                "abs_deviation": abs(interval_seconds - 600),
                "tx_count": int(newer.get("tx_count", 0)),
                "size": int(newer.get("size", 0)),
                "weight": int(newer.get("weight", 0)),
            }
        )

    df = pd.DataFrame(rows)
    return df.sort_values("height").reset_index(drop=True)


def _build_heatmap_figure(intervals_df: pd.DataFrame) -> go.Figure:
    records = intervals_df.to_dict("records")
    columns = 10
    rows = math.ceil(len(records) / columns)

    z = [[None for _ in range(columns)] for _ in range(rows)]
    customdata = [[None for _ in range(columns)] for _ in range(rows)]

    for idx, record in enumerate(records):
        row = rows - 1 - (idx // columns)
        col = idx % columns
        z[row][col] = record["interval_minutes"]
        customdata[row][col] = [record["height"], record["tx_count"], record["interval_deviation"]]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            customdata=customdata,
            colorscale=[
                [0.0, "#4d6fb0"],
                [0.45, "#b8c7dd"],
                [0.5, "#f2efe9"],
                [0.75, "#efb082"],
                [1.0, "#e36b47"],
            ],
            zmid=10,
            colorbar=dict(
                title=dict(text="Minutes", font=dict(color=INK)),
                tickfont=dict(color=MUTED),
            ),
            hovertemplate=(
                "Block %{customdata[0]}<br>"
                "Interval %{z:.2f} min<br>"
                "Deviation %{customdata[2]} s<br>"
                "Transactions %{customdata[1]}<extra></extra>"
            ),
        )
    )
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    return fig


def _build_constellation_figure(intervals_df: pd.DataFrame) -> go.Figure:
    df = intervals_df.copy().reset_index(drop=True)
    count = len(df)
    angles = [2 * math.pi * index / max(count, 1) for index in range(count)]
    base_radius = 1.0
    radii = [base_radius + min(row / 18.0, 1.8) for row in df["interval_minutes"]]

    df["x"] = [radius * math.cos(angle) for radius, angle in zip(radii, angles)]
    df["y"] = [radius * math.sin(angle) for radius, angle in zip(radii, angles)]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["x"],
            y=df["y"],
            mode="lines",
            line=dict(color="rgba(11,12,13,0.18)", width=1.2),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["x"],
            y=df["y"],
            mode="markers",
            marker=dict(
                size=df["tx_count"].clip(lower=1).pow(0.5) * 1.5,
                color=df["interval_deviation"],
                colorscale=[COOL, "#d8dee8", "#f2efe9", "#f0be98", HOT],
                line=dict(width=1, color=INK),
                colorbar=dict(
                    title=dict(text="Deviation (s)", font=dict(color=INK)),
                    tickfont=dict(color=MUTED),
                ),
            ),
            customdata=df[["height", "interval_minutes", "tx_count", "interval_deviation"]],
            hovertemplate=(
                "Block %{customdata[0]}<br>"
                "Interval %{customdata[1]:.2f} min<br>"
                "Transactions %{customdata[2]}<br>"
                "Deviation %{customdata[3]} s<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False, visible=False, scaleanchor="x")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    return fig


def _build_indicator_figure(adjustment_estimate: float, avg_interval_minutes: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=adjustment_estimate,
            number={"suffix": "%", "font": {"size": 30, "color": INK}},
            delta={"reference": 0, "relative": False, "valueformat": ".2f", "position": "top"},
            title={"text": "Estimated next retarget", "font": {"size": 15, "color": INK}},
            gauge={
                "axis": {"range": [-20, 20], "tickcolor": MUTED},
                "bar": {"color": INK},
                "bgcolor": "rgba(255,255,255,0)",
                "steps": [
                    {"range": [-20, -5], "color": "#bfd1ef"},
                    {"range": [-5, 5], "color": "#eef3df"},
                    {"range": [5, 20], "color": "#f0be98"},
                ],
                "threshold": {"line": {"color": ACCENT, "width": 5}, "value": 0},
            },
            domain={"x": [0.0, 0.48], "y": [0.0, 1.0]},
        )
    )
    fig.add_trace(
        go.Indicator(
            mode="number+gauge",
            value=avg_interval_minutes,
            number={"suffix": " min", "font": {"size": 26, "color": INK}},
            title={"text": "Mean recent interval", "font": {"size": 15, "color": INK}},
            gauge={
                "shape": "bullet",
                "axis": {"range": [0, 20], "tickcolor": MUTED},
                "bar": {"color": COOL},
                "bgcolor": "rgba(255,255,255,0)",
                "steps": [
                    {"range": [0, 8], "color": "#c8d6eb"},
                    {"range": [8, 12], "color": "#eef3df"},
                    {"range": [12, 20], "color": "#f0be98"},
                ],
                "threshold": {"line": {"color": ACCENT, "width": 5}, "value": 10},
            },
            domain={"x": [0.55, 1.0], "y": [0.12, 0.88]},
        )
    )
    return fig


def _build_sequence_figure(intervals_df: pd.DataFrame) -> go.Figure:
    df = intervals_df.copy()
    df["rolling_mean"] = df["interval_minutes"].rolling(window=5, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["height"],
            y=df["interval_minutes"],
            mode="lines+markers",
            line=dict(color=INK, width=2.6),
            marker=dict(size=7, color=ACCENT_SOFT, line=dict(color=INK, width=1)),
            name="Observed interval",
            customdata=df[["tx_count", "interval_deviation"]],
            hovertemplate=(
                "Block %{x}<br>"
                "Interval %{y:.2f} min<br>"
                "Transactions %{customdata[0]}<br>"
                "Deviation %{customdata[1]} s<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["height"],
            y=df["rolling_mean"],
            mode="lines",
            line=dict(color=COOL, width=2, dash="dot"),
            name="Rolling mean (5 blocks)",
            hovertemplate="Rolling mean %{y:.2f} min<extra></extra>",
        )
    )
    fig.add_hline(
        y=10,
        line_dash="dash",
        line_color=ACCENT,
        annotation_text="10-minute target",
        annotation_position="top right",
    )
    fig.update_layout(showlegend=True, xaxis_title="Block height", yaxis_title="Minutes")
    return fig


def _apply_chart_theme(fig: go.Figure, title_text: str | None = None) -> go.Figure:
    layout_kwargs = {
        "paper_bgcolor": PAPER_BG,
        "plot_bgcolor": PLOT_BG,
        "font": {"family": "Archivo, sans-serif", "color": INK, "size": 13},
        "margin": {"l": 20, "r": 20, "t": 24, "b": 20},
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


@st.cache_data(ttl=60, show_spinner=False)
def _load_m1_snapshot(block_window: int) -> dict[str, object]:
    latest_block = get_latest_block(source="blockstream")
    recent_blocks = get_recent_blocks(limit=block_window + 1, source="blockstream")
    mempool_tip_hash = get_latest_block_hash(source="mempool")
    mempool_adjustment = get_mempool_difficulty_adjustment()
    blockchain_stats = get_blockchain_stats()
    difficulty_history = get_difficulty_history("3months")

    return {
        "latest_block": latest_block,
        "recent_blocks": recent_blocks,
        "mempool_tip_hash": mempool_tip_hash,
        "mempool_adjustment": mempool_adjustment,
        "blockchain_stats": blockchain_stats,
        "difficulty_history": difficulty_history,
    }


def render() -> None:
    """Render the M1 panel."""
    block_window = st.slider(
        "Recent block intervals to analyze",
        min_value=20,
        max_value=120,
        value=50,
        step=10,
        key="m1_block_window",
    )

    with st.spinner("Loading live Bitcoin mining data..."):
        try:
            snapshot = _load_m1_snapshot(block_window)
        except Exception as exc:
            st.error(f"M1 could not load live data: {exc}")
            st.info(
                "Check the network connection or the public API status. "
                "This dashboard only renders real public blockchain data."
            )
            return

    latest_block = snapshot["latest_block"]
    recent_blocks = snapshot["recent_blocks"]
    mempool_tip_hash = snapshot["mempool_tip_hash"]
    mempool_adjustment = snapshot["mempool_adjustment"]
    blockchain_stats = snapshot["blockchain_stats"]
    difficulty_history = snapshot["difficulty_history"]

    target = bits_to_target(latest_block["bits"])
    target_hex = target_to_hex(target)
    target_share = target / ((1 << 256) - 1)
    leading_zero_hex_digits = len(target_hex) - len(target_hex.lstrip("0"))
    leading_zero_bits = count_leading_zero_bits(latest_block["id"])
    estimated_hashrate = estimate_hashrate_from_difficulty(latest_block["difficulty"])
    intervals_df = _build_intervals_dataframe(recent_blocks)

    current_height = int(latest_block["height"])
    current_time = datetime.fromtimestamp(int(latest_block["timestamp"]), tz=timezone.utc)
    tip_match = latest_block["id"] == mempool_tip_hash
    avg_interval = float(intervals_df["interval_seconds"].mean())
    std_interval = float(intervals_df["interval_seconds"].std(ddof=0))
    cv_interval = std_interval / avg_interval if avg_interval else 0.0

    remaining_blocks = _safe_get(mempool_adjustment, "remainingBlocks", "remaining_blocks")
    adjustment_estimate = float(
        _safe_get(
            mempool_adjustment,
            "difficultyChange",
            "estimatedRetargetPercentage",
            "estimated_retarget_percentage",
        )
        or 0.0
    )
    time_avg = _safe_get(mempool_adjustment, "timeAvg", "time_avg", "averageTime", "avgBlockTime")
    blockchain_minutes = _safe_get(blockchain_stats, "minutes_between_blocks")

    metric_cols = st.columns(6)
    metric_cols[0].metric("Latest block", f"{current_height:,}")
    metric_cols[1].metric("Difficulty", _format_compact_number(latest_block["difficulty"]))
    metric_cols[2].metric("Estimated hashrate", _format_hashrate(estimated_hashrate))
    metric_cols[3].metric("Leading zero bits", f"{leading_zero_bits}")
    metric_cols[4].metric("Blocks to retarget", f"{remaining_blocks}" if remaining_blocks is not None else "n/a")
    metric_cols[5].metric("Estimated retarget", f"{adjustment_estimate:+.2f}%")

    top_left, top_right = st.columns([1.45, 1.0])

    with top_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Block constellation")
        constellation_fig = _build_constellation_figure(intervals_df)
        _apply_chart_theme(constellation_fig)
        st.plotly_chart(constellation_fig, width="stretch", config=PLOT_CONFIG)
        st.caption(
            "A Cosmograph-inspired view: each node is a real recent block, connected in sequence, "
            "sized by transaction count and colored by how far its interval deviates from 600 seconds."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    with top_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Latest block + target")
        st.write(f"Height: **{current_height:,}**")
        st.write(f"Hash: `{latest_block['id']}`")
        st.write(f"Nonce: **{latest_block['nonce']:,}**")
        st.write(f"Transactions: **{latest_block['tx_count']:,}**")
        st.write(f"Mined at: **{current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}**")
        st.write(f"Tip consensus: **{'Match' if tip_match else 'Mismatch'}**")
        st.write(f"Compact `bits`: **{latest_block['bits']}**")
        st.write(f"Target share of SHA-256 space: **{target_share:.3e}**")
        st.write(f"Leading zero hex digits implied: **{leading_zero_hex_digits}**")
        st.markdown(f'<div class="hash-block">{target_hex}</div>', unsafe_allow_html=True)
        st.caption(
            "Any valid block hash must be numerically below this 256-bit target. "
            "That is the proof-of-work threshold encoded in `bits`."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    mid_left, mid_right = st.columns(2)

    with mid_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Mining pressure indicators")
        indicator_fig = _build_indicator_figure(adjustment_estimate, avg_interval / 60)
        indicator_fig = _apply_chart_theme(indicator_fig)
        indicator_fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False)
        indicator_fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
        st.plotly_chart(indicator_fig, width="stretch", config=PLOT_CONFIG)
        st.caption(
            "Retarget pressure and observed recent tempo in one compact control panel."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    with mid_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Inter-block time distribution")
        hist_fig = px.histogram(
            intervals_df,
            x="interval_minutes",
            nbins=min(24, max(10, block_window // 3)),
            labels={"interval_minutes": "Minutes"},
        )
        hist_fig.update_traces(marker_color=INK, marker_line_color="rgba(11,12,13,0)", opacity=0.92)
        hist_fig.add_vline(
            x=10,
            line_dash="dash",
            line_color=ACCENT,
            annotation_text="10-minute target",
            annotation_position="top right",
        )
        hist_fig.update_layout(showlegend=False, xaxis_title="Minutes", yaxis_title="Block count")
        _apply_chart_theme(hist_fig)
        st.plotly_chart(hist_fig, width="stretch", config=PLOT_CONFIG)
        st.caption(
            "Histogram of real recent block intervals. The expected baseline is exponential."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    lower_left, lower_right = st.columns(2)

    with lower_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Mining tempo map")
        scatter_fig = px.scatter(
            intervals_df,
            x="height",
            y="interval_minutes",
            size="tx_count",
            color="interval_deviation",
            color_continuous_scale=[COOL, "#d8dee8", "#f2efe9", "#f0be98", HOT],
            hover_data={
                "height": True,
                "interval_minutes": ":.2f",
                "interval_deviation": True,
                "tx_count": True,
                "timestamp": True,
            },
            labels={
                "height": "Block height",
                "interval_minutes": "Minutes",
                "interval_deviation": "Deviation (s)",
                "tx_count": "Tx count",
            },
        )
        scatter_fig.update_traces(
            marker=dict(line=dict(width=0.9, color=INK), sizemin=6),
            selector=dict(mode="markers"),
        )
        scatter_fig.add_hline(
            y=10,
            line_dash="dash",
            line_color=ACCENT,
            annotation_text="10-minute target",
            annotation_position="top right",
        )
        scatter_fig.update_layout(showlegend=False, xaxis_title="Block height", yaxis_title="Minutes")
        _apply_chart_theme(scatter_fig)
        st.plotly_chart(scatter_fig, width="stretch", config=PLOT_CONFIG)
        st.caption(
            "Timeline scatter: each point is a real block, colored by interval deviation and sized by transaction count."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    with lower_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Block rhythm heatmap")
        heatmap_fig = _build_heatmap_figure(intervals_df)
        _apply_chart_theme(heatmap_fig)
        st.plotly_chart(heatmap_fig, width="stretch", config=PLOT_CONFIG)
        st.caption(
            "Dense recent-block rhythm view to spot clusters, hot zones, and outliers at a glance."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    bottom_left, bottom_right = st.columns([1.15, 0.85])

    with bottom_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Difficulty context")
        history_df = pd.DataFrame(difficulty_history)
        if not history_df.empty:
            history_df["date"] = pd.to_datetime(history_df["x"], unit="s", utc=True)
            history_df["difficulty"] = history_df["y"]
            history_fig = go.Figure()
            history_fig.add_trace(
                go.Scatter(
                    x=history_df["date"],
                    y=history_df["difficulty"],
                    mode="lines",
                    line=dict(color=INK, width=3),
                    fill="tozeroy",
                    fillcolor="rgba(148,173,214,0.20)",
                    name="Difficulty",
                )
            )
            history_fig.update_layout(showlegend=False, xaxis_title="Date", yaxis_title="Difficulty")
            _apply_chart_theme(history_fig)
            st.plotly_chart(history_fig, width="stretch", config=PLOT_CONFIG)
        else:
            st.warning("Blockchain.com did not return difficulty history data.")

        st.caption("Short historical difficulty context from Blockchain.com.")
        st.markdown("</section>", unsafe_allow_html=True)

    with bottom_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Recent interval sequence")
        sequence_fig = _build_sequence_figure(intervals_df)
        _apply_chart_theme(sequence_fig)
        st.plotly_chart(sequence_fig, width="stretch", config=PLOT_CONFIG)
        if blockchain_minutes is not None:
            st.write(f"Blockchain.com aggregate `minutes_between_blocks`: **{float(blockchain_minutes):.2f} min**")
        if time_avg is not None:
            st.write(f"mempool.space current-epoch average block time: **{float(time_avg) / 60:.2f} min**")
        st.caption(
            "This brings back the classic sequential view: useful for reading short-term drift, volatility, and sudden outliers block by block."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    with st.expander("Why these APIs and charts are here"):
        st.markdown(
            """
            - `Blockstream Esplora`: current block, recent blocks, timestamps, transaction counts, and the live proof-of-work surface for this dashboard.
            - `mempool.space`: current difficulty-adjustment cycle and retarget estimate.
            - `Blockchain.com Charts API`: historical difficulty context.
            - Visual design choice: the dense scatter/heatmap approach is inspired by tools like Cosmograph, which emphasize filtering, outliers, and temporal structure.
            """
        )

    if target_share > 0:
        expected_hex_zeroes = math.log(1 / target_share, 16)
        st.caption(
            f"Interpretation: the current target leaves about {target_share:.3e} of the 2^256 hash space as valid outputs. "
            f"That corresponds to roughly {expected_hex_zeroes:.2f} leading zero hex digits on average, while this specific block shows {leading_zero_bits} leading zero bits."
        )
