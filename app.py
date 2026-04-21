"""Streamlit entry point for the CryptoChain Analyzer dashboard."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from modules.m1_pow_monitor import render as render_m1
from modules.m2_block_header import render as render_m2
from modules.m3_difficulty_history import render as render_m3


def _auto_refresh(interval_seconds: int) -> None:
    components.html(
        f"""
        <script>
        setTimeout(function () {{
            window.parent.location.reload();
        }}, {interval_seconds * 1000});
        </script>
        """,
        height=0,
    )


def _inject_global_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800;900&family=Cormorant+Garamond:wght@500;600&display=swap');

        :root {
            --bg: #ebe6de;
            --panel: rgba(255, 255, 255, 0.72);
            --panel-strong: rgba(255, 255, 255, 0.88);
            --ink: #0b0c0d;
            --muted: #585952;
            --line: rgba(11, 12, 13, 0.14);
            --accent: #d8ff45;
            --accent-soft: #9bb3d9;
            --shadow: 0 18px 55px rgba(11, 12, 13, 0.07);
        }

        html, body, [class*="css"] {
            font-family: 'Archivo', sans-serif;
            color: var(--ink);
        }

        .stApp,
        .stApp p,
        .stApp span,
        .stApp label,
        .stApp li,
        .stApp div,
        .stApp h1,
        .stApp h2,
        .stApp h3,
        .stApp h4,
        .stApp h5,
        .stApp h6 {
            color: var(--ink) !important;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(216, 255, 69, 0.15), transparent 30%),
                radial-gradient(circle at 90% 0%, rgba(155, 179, 217, 0.22), transparent 24%),
                linear-gradient(180deg, #ece8e1 0%, #e8e3da 45%, #ece8e1 100%);
        }

        .main .block-container {
            max-width: 1460px;
            padding-top: 1.2rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: rgba(248, 246, 241, 0.88);
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] * {
            color: var(--ink) !important;
        }

        [data-testid="stMarkdownContainer"] *,
        [data-testid="stText"] *,
        [data-testid="stCaptionContainer"] *,
        [data-testid="stMetricLabel"] *,
        [data-testid="stMetricValue"] * {
            color: var(--ink) !important;
        }

        [data-testid="stMetric"] {
            background: var(--panel);
            border: 1px solid rgba(11, 12, 13, 0.1);
            border-radius: 1.1rem;
            padding: 0.95rem 1rem;
            box-shadow: var(--shadow);
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.5rem;
            font-weight: 800;
            line-height: 1;
        }

        .stApp code:not(pre code) {
            background: rgba(11, 12, 13, 0.92);
            color: #f5f2ea !important;
            border-radius: 0.42rem;
            padding: 0.12rem 0.38rem;
        }

        [data-testid="stCodeBlock"],
        .stCode,
        .stCodeBlock {
            background: rgba(16, 18, 22, 0.97) !important;
            border-radius: 1rem !important;
            border: 1px solid rgba(245, 242, 234, 0.08);
        }

        [data-testid="stCodeBlock"] *,
        .stCode *,
        .stCodeBlock *,
        pre code {
            color: #f5f2ea !important;
        }

        pre code {
            background: transparent !important;
            padding: 0 !important;
            border-radius: 0 !important;
        }

        .module-placeholder,
        .m1-card {
            background: var(--panel);
            border: 1px solid rgba(11, 12, 13, 0.1);
            border-radius: 1.4rem;
            box-shadow: var(--shadow);
            backdrop-filter: blur(8px);
        }

        .micro-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            color: var(--muted);
        }

        .placeholder-copy {
            margin: 0;
            font-family: 'Cormorant Garamond', serif;
            font-size: 1.02rem;
            line-height: 1.02;
        }

        .status-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.6rem;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            border: 1px solid rgba(11, 12, 13, 0.12);
            border-radius: 999px;
            padding: 0.42rem 0.72rem;
            background: var(--panel-strong);
            font-size: 0.72rem;
            letter-spacing: 0.11em;
            text-transform: uppercase;
        }

        .module-placeholder {
            padding: 1.2rem 1.3rem;
            min-height: 17rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .module-placeholder.dark {
            background: linear-gradient(180deg, rgba(12, 12, 14, 0.98), rgba(26, 27, 30, 0.98));
            color: #f5f2ea;
            border-color: rgba(245, 242, 234, 0.08);
        }

        .module-placeholder.dark * {
            color: #f5f2ea !important;
        }

        .hash-block,
        .hash-block *,
        .module-placeholder.dark,
        .module-placeholder.dark *,
        [data-testid="stCodeBlock"] *,
        .stCode *,
        .stCodeBlock *,
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary *,
        [data-testid="stExpander"] details > div,
        [data-testid="stExpander"] details > div * {
            color: #f5f2ea !important;
            -webkit-text-fill-color: #f5f2ea !important;
        }

        .placeholder-title {
            margin: 0.2rem 0 0.45rem;
            font-size: clamp(2rem, 4vw, 3.6rem);
            line-height: 0.92;
            letter-spacing: -0.05em;
            text-transform: uppercase;
        }

        .placeholder-index {
            font-size: 2.1rem;
            font-weight: 800;
            letter-spacing: -0.05em;
        }

        [data-testid="stExpander"] details {
            background: rgba(16, 18, 22, 0.96);
            border-radius: 1rem;
            border: 1px solid rgba(245, 242, 234, 0.08);
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_placeholder(module_number: str, title: str, copy: str, dark: bool = False) -> None:
    dark_class = " dark" if dark else ""
    st.markdown(
        f"""
        <section class="module-placeholder{dark_class}">
            <div>
                <div class="micro-label">Module {module_number}</div>
                <h2 class="placeholder-title">{title}</h2>
                <p class="placeholder-copy">{copy}</p>
            </div>
            <div class="placeholder-index">{module_number} / 04</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="CryptoChain Analyzer", layout="wide")
_inject_global_styles()

with st.sidebar:
    st.header("Dashboard Controls")
    selected_module = st.radio(
        "Module",
        [
            "M1 Mining Dashboard",
            "M2 Block Header Analyzer",
            "M3 Difficulty History",
            "M4 AI Component",
        ],
        index=0,
    )
    auto_refresh_enabled = st.toggle("Auto-refresh", value=True)
    refresh_seconds = st.slider(
        "Refresh every (seconds)",
        min_value=30,
        max_value=300,
        value=60,
        step=30,
    )
    st.caption("Dashboard mode. M1 opens directly with live charts.")

if auto_refresh_enabled:
    _auto_refresh(refresh_seconds)

if selected_module == "M1 Mining Dashboard":
    render_m1()
elif selected_module == "M2 Block Header Analyzer":
    render_m2()
elif selected_module == "M3 Difficulty History":
    render_m3()
else:
    _render_placeholder(
        "04",
        "AI Component",
        "This module will forecast the next Bitcoin difficulty adjustment and later compare predicted versus observed values with explicit evaluation metrics.",
    )
