"""Module M6: Bitcoin security score and 51% attack cost estimator."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import (
    estimate_hashrate_from_difficulty,
    get_blockchain_stats,
    get_latest_block,
)


PLOT_BG = "rgba(255,255,255,0.84)"
PAPER_BG = "rgba(255,255,255,0)"
INK = "#0b0c0d"
MUTED = "#595b57"
ACCENT = "#d8ff45"
COOL = "#5477b8"
HOT = "#f46b45"
PLOT_CONFIG = {"displaylogo": False, "displayModeBar": False, "responsive": True}


def _format_hashrate(hashrate_hps: float) -> str:
    units = ["H/s", "kH/s", "MH/s", "GH/s", "TH/s", "PH/s", "EH/s", "ZH/s"]
    value = float(hashrate_hps)
    unit_index = 0

    while value >= 1000 and unit_index < len(units) - 1:
        value /= 1000
        unit_index += 1

    return f"{value:,.2f} {units[unit_index]}"


def _format_usd(value: float) -> str:
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:,.2f}K"
    return f"${value:,.2f}"


def _format_compact_number(value: float) -> str:
    units = ["", "K", "M", "B", "T", "P"]
    number = float(value)
    unit_index = 0

    while abs(number) >= 1000 and unit_index < len(units) - 1:
        number /= 1000
        unit_index += 1

    suffix = units[unit_index]
    return f"{number:,.2f}{suffix}" if suffix else f"{number:,.0f}"


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


def _nakamoto_double_spend_probability(confirmations: int, attacker_share: float) -> float:
    """Return the Nakamoto section 11 catch-up probability for q < 0.5."""
    z = int(confirmations)
    q = float(attacker_share)

    if z <= 0:
        return 1.0
    if q <= 0:
        return 0.0
    if q >= 0.5:
        return 1.0

    p = 1.0 - q
    lambda_value = z * (q / p)
    poisson_probability = math.exp(-lambda_value)
    cumulative = 0.0

    for k in range(z + 1):
        cumulative += poisson_probability * (1 - (q / p) ** (z - k))
        if k < z:
            poisson_probability *= lambda_value / (k + 1)

    return max(0.0, min(1.0, 1.0 - cumulative))


def _attacker_hashrate_for_share(honest_hashrate_hps: float, desired_share: float) -> float:
    """Hashrate needed so attacker_share = attacker / (attacker + honest)."""
    share = min(max(float(desired_share), 0.01), 0.99)
    return honest_hashrate_hps * share / (1.0 - share)


def _estimate_attack_cost(
    attacker_hashrate_hps: float,
    electricity_usd_kwh: float,
    miner_efficiency_j_th: float,
    hardware_usd_per_th: float,
    amortization_years: float,
    utilization: float,
) -> dict[str, float]:
    attacker_ths = attacker_hashrate_hps / 1e12
    power_watts = attacker_ths * miner_efficiency_j_th
    energy_kwh_per_hour = power_watts / 1000
    energy_usd_hour = energy_kwh_per_hour * electricity_usd_kwh
    amortization_hours = max(amortization_years * 365 * 24 * utilization, 1)
    hardware_usd_hour = (attacker_ths * hardware_usd_per_th) / amortization_hours

    return {
        "attacker_ths": attacker_ths,
        "power_watts": power_watts,
        "energy_kwh_per_hour": energy_kwh_per_hour,
        "energy_usd_hour": energy_usd_hour,
        "hardware_usd_hour": hardware_usd_hour,
        "total_usd_hour": energy_usd_hour + hardware_usd_hour,
    }


@st.cache_data(ttl=60, show_spinner=False)
def _load_m6_snapshot() -> dict[str, object]:
    latest_block = get_latest_block()
    blockchain_stats = get_blockchain_stats()
    return {
        "latest_block": latest_block,
        "blockchain_stats": blockchain_stats,
    }


def _build_cost_breakdown_figure(costs: dict[str, float]) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=["Electricity", "Hardware amortization"],
            y=[costs["energy_usd_hour"], costs["hardware_usd_hour"]],
            marker_color=[COOL, HOT],
            hovertemplate="%{x}<br>%{y:$,.0f} per hour<extra></extra>",
        )
    )
    fig.update_layout(xaxis_title="Cost component", yaxis_title="USD per hour")
    return fig


def _build_confirmation_probability_figure(max_confirmations: int) -> go.Figure:
    confirmations = list(range(0, max_confirmations + 1))
    fig = go.Figure()

    for q, color in [(0.10, COOL), (0.25, "#7f8f73"), (0.40, HOT), (0.49, INK)]:
        probabilities = [max(_nakamoto_double_spend_probability(z, q), 1e-12) for z in confirmations]
        fig.add_trace(
            go.Scatter(
                x=confirmations,
                y=probabilities,
                mode="lines+markers",
                line=dict(color=color, width=2.5),
                marker=dict(size=6),
                name=f"q = {q:.0%}",
                hovertemplate="Confirmations %{x}<br>Catch-up probability %{y:.6f}<extra></extra>",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=confirmations,
            y=[1.0] * len(confirmations),
            mode="lines",
            line=dict(color=ACCENT, width=3, dash="dash"),
            name="q >= 50%",
            hovertemplate="A majority attacker eventually catches up<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Confirmation depth",
        yaxis_title="Attacker catch-up probability",
        yaxis_type="log",
        yaxis_range=[-8, 0.05],
    )
    return fig


def _build_sensitivity_figure(
    honest_hashrate_hps: float,
    electricity_usd_kwh: float,
    miner_efficiency_j_th: float,
    hardware_usd_per_th: float,
    amortization_years: float,
    utilization: float,
) -> go.Figure:
    rows: list[dict[str, float]] = []
    for share_pct in range(10, 56, 5):
        share = share_pct / 100
        attacker_hashrate = _attacker_hashrate_for_share(honest_hashrate_hps, share)
        costs = _estimate_attack_cost(
            attacker_hashrate,
            electricity_usd_kwh,
            miner_efficiency_j_th,
            hardware_usd_per_th,
            amortization_years,
            utilization,
        )
        rows.append(
            {
                "Share": share_pct,
                "Cost": costs["total_usd_hour"],
                "Energy": costs["energy_usd_hour"],
                "Hardware": costs["hardware_usd_hour"],
            }
        )

    df = pd.DataFrame(rows)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Share"],
            y=df["Cost"],
            mode="lines+markers",
            line=dict(color=INK, width=3),
            marker=dict(size=9, color=ACCENT, line=dict(color=INK, width=1)),
            customdata=df[["Energy", "Hardware"]],
            hovertemplate=(
                "Attacker share %{x}%<br>"
                "Total %{y:$,.0f}/h<br>"
                "Energy %{customdata[0]:$,.0f}/h<br>"
                "Hardware %{customdata[1]:$,.0f}/h<extra></extra>"
            ),
        )
    )
    fig.add_vline(x=50, line_color=HOT, line_dash="dash", annotation_text="majority threshold")
    fig.update_layout(xaxis_title="Desired attacker share of total hashrate (%)", yaxis_title="USD per hour")
    return fig


def render() -> None:
    """Render the M6 security score module."""
    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem; margin-bottom:1rem;">', unsafe_allow_html=True)
    st.subheader("Security score and 51% attack cost")
    st.caption(
        "Optional M6 estimates the hourly cost of majority hashrate using live Bitcoin difficulty and shows how confirmation depth changes double-spend risk."
    )
    controls = st.columns(3)
    desired_share_pct = controls[0].slider(
        "Attacker share of total hashrate (%)",
        min_value=51,
        max_value=60,
        value=51,
        step=1,
        key="m6_attacker_share",
    )
    electricity_usd_kwh = controls[1].slider(
        "Electricity price (USD/kWh)",
        min_value=0.02,
        max_value=0.20,
        value=0.07,
        step=0.01,
        key="m6_electricity",
    )
    max_confirmations = controls[2].slider(
        "Confirmation depth range",
        min_value=6,
        max_value=30,
        value=12,
        step=3,
        key="m6_confirmations",
    )

    assumption_cols = st.columns(3)
    miner_efficiency_j_th = assumption_cols[0].slider(
        "Miner efficiency (J/TH)",
        min_value=12.0,
        max_value=40.0,
        value=17.5,
        step=0.5,
        key="m6_efficiency",
    )
    hardware_usd_per_th = assumption_cols[1].slider(
        "Hardware cost (USD/TH)",
        min_value=3.0,
        max_value=40.0,
        value=12.0,
        step=1.0,
        key="m6_hardware_cost",
    )
    amortization_years = assumption_cols[2].slider(
        "Hardware amortization (years)",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.5,
        key="m6_amortization",
    )
    st.markdown("</section>", unsafe_allow_html=True)

    with st.spinner("Loading live Bitcoin security data..."):
        try:
            snapshot = _load_m6_snapshot()
        except Exception as exc:
            st.error(f"M6 could not load live network data: {exc}")
            st.info("This module uses live difficulty from Blockstream and aggregate stats from Blockchain.com.")
            return

    latest_block: dict = snapshot["latest_block"]
    blockchain_stats: dict = snapshot["blockchain_stats"]
    network_hashrate_hps = estimate_hashrate_from_difficulty(float(latest_block["difficulty"]))
    desired_share = desired_share_pct / 100
    attacker_hashrate_hps = _attacker_hashrate_for_share(network_hashrate_hps, desired_share)
    costs = _estimate_attack_cost(
        attacker_hashrate_hps,
        electricity_usd_kwh,
        miner_efficiency_j_th,
        hardware_usd_per_th,
        amortization_years,
        utilization=0.95,
    )
    latest_time = datetime.fromtimestamp(int(latest_block["timestamp"]), tz=timezone.utc)
    market_price = blockchain_stats.get("market_price_usd")

    score = max(0, min(100, 100 - (desired_share_pct - 51) * 4))

    metric_cols = st.columns(6)
    metric_cols[0].metric("Latest block", f"{int(latest_block['height']):,}")
    metric_cols[1].metric("Difficulty", _format_compact_number(float(latest_block["difficulty"])))
    metric_cols[2].metric("Network hashrate", _format_hashrate(network_hashrate_hps))
    metric_cols[3].metric("Attacker hashrate", _format_hashrate(attacker_hashrate_hps))
    metric_cols[4].metric("Estimated cost", f"{_format_usd(costs['total_usd_hour'])}/h")
    metric_cols[5].metric("Security score", f"{score}/100")

    top_left, top_right = st.columns([1.18, 0.82])
    with top_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Cost breakdown")
        cost_fig = _build_cost_breakdown_figure(costs)
        _apply_chart_theme(cost_fig)
        st.plotly_chart(cost_fig, width="stretch", config=PLOT_CONFIG)
        st.caption("This is an operational estimate from live hashrate plus editable hardware and electricity assumptions.")
        st.markdown("</section>", unsafe_allow_html=True)

    with top_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Live calculation")
        st.write(f"Block time: **{latest_time.strftime('%Y-%m-%d %H:%M:%S UTC')}**")
        st.write(f"Current block hash: `{latest_block['id']}`")
        st.write(f"Desired attacker share: **{desired_share_pct}%**")
        st.write(f"Electricity-only cost: **{_format_usd(costs['energy_usd_hour'])}/h**")
        st.write(f"Hardware amortization: **{_format_usd(costs['hardware_usd_hour'])}/h**")
        st.write(f"Power draw: **{costs['power_watts'] / 1e9:,.2f} GW**")
        if market_price is not None:
            st.write(f"Blockchain.com BTC price context: **${float(market_price):,.2f}**")
        st.markdown("</section>", unsafe_allow_html=True)

    lower_left, lower_right = st.columns(2)
    with lower_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Confirmation-depth risk")
        probability_fig = _build_confirmation_probability_figure(max_confirmations)
        _apply_chart_theme(probability_fig)
        st.plotly_chart(probability_fig, width="stretch", config=PLOT_CONFIG)
        st.caption(
            "Nakamoto section 11: for q < 50%, the probability of catching up drops sharply as confirmations increase. For q >= 50%, it tends to 1."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    with lower_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Cost sensitivity")
        sensitivity_fig = _build_sensitivity_figure(
            network_hashrate_hps,
            electricity_usd_kwh,
            miner_efficiency_j_th,
            hardware_usd_per_th,
            amortization_years,
            utilization=0.95,
        )
        _apply_chart_theme(sensitivity_fig)
        st.plotly_chart(sensitivity_fig, width="stretch", config=PLOT_CONFIG)
        st.caption("The curve rises quickly because majority control requires more hashrate than the current honest network.")
        st.markdown("</section>", unsafe_allow_html=True)

    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
    st.subheader("Model assumptions")
    st.code(
        "network_hashrate = difficulty * 2^32 / 600\n"
        "attacker_hashrate = honest_hashrate * q / (1 - q)\n"
        "energy_cost_per_hour = TH/s * J/TH / 1000 * USD_per_kWh",
        language="text",
    )
    st.caption(
        "This is not a claim that such hashrate is rentable on demand. It is a transparent lower-bound style estimate tied to live Bitcoin mining difficulty."
    )
    st.markdown("</section>", unsafe_allow_html=True)
