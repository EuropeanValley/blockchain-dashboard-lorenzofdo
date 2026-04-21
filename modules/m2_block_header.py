"""Module M2: Block Header Analyzer."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import get_block, get_latest_block, target_to_hex, verify_block_pow


FIELD_LENGTHS = {
    "Version": 4,
    "Previous hash": 32,
    "Merkle root": 32,
    "Timestamp": 4,
    "Bits": 4,
    "Nonce": 4,
}

FIELD_ORDER = list(FIELD_LENGTHS.keys())
FIELD_COLORS = {
    "Version": "#5477b8",
    "Previous hash": "#0b0c0d",
    "Merkle root": "#94add6",
    "Timestamp": "#d8ff45",
    "Bits": "#f0be98",
    "Nonce": "#f46b45",
}
PLOT_BG = "rgba(255,255,255,0.84)"
PAPER_BG = "rgba(255,255,255,0)"
INK = "#0b0c0d"
MUTED = "#595b57"
PLOT_CONFIG = {"displaylogo": False, "displayModeBar": False, "responsive": True}


def _format_uint32_hex(value: int) -> str:
    return f"0x{value & 0xFFFFFFFF:08x}"


def _format_header_hex(header_hex: str, chunk_size: int = 8, line_groups: int = 5) -> str:
    chunks = [header_hex[index:index + chunk_size] for index in range(0, len(header_hex), chunk_size)]
    lines = [
        " ".join(chunks[index:index + line_groups])
        for index in range(0, len(chunks), line_groups)
    ]
    return "\n".join(lines)


def _build_field_rows(analysis: dict[str, object]) -> list[dict[str, object]]:
    header_bytes = bytes.fromhex(str(analysis["header_hex"]))
    cursor = 0
    serialized_segments: dict[str, str] = {}

    for label, byte_length in FIELD_LENGTHS.items():
        serialized_segments[label] = header_bytes[cursor:cursor + byte_length].hex()
        cursor += byte_length

    timestamp = datetime.fromtimestamp(int(analysis["timestamp"]), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return [
        {
            "Field": "Version",
            "API value": int(analysis["version"]),
            "Header bytes (little-endian)": serialized_segments["Version"],
            "Readable": _format_uint32_hex(int(analysis["version"])),
            "Endian note": "4-byte integer stored little-endian",
        },
        {
            "Field": "Previous hash",
            "API value": str(analysis["previous_hash"]),
            "Header bytes (little-endian)": serialized_segments["Previous hash"],
            "Readable": "display hash reversed by bytes",
            "Endian note": "32-byte hash inserted reversed into the header",
        },
        {
            "Field": "Merkle root",
            "API value": str(analysis["merkle_root"]),
            "Header bytes (little-endian)": serialized_segments["Merkle root"],
            "Readable": "display root reversed by bytes",
            "Endian note": "32-byte root inserted reversed into the header",
        },
        {
            "Field": "Timestamp",
            "API value": int(analysis["timestamp"]),
            "Header bytes (little-endian)": serialized_segments["Timestamp"],
            "Readable": timestamp,
            "Endian note": "Unix time packed as a 4-byte little-endian integer",
        },
        {
            "Field": "Bits",
            "API value": int(analysis["bits"]),
            "Header bytes (little-endian)": serialized_segments["Bits"],
            "Readable": _format_uint32_hex(int(analysis["bits"])),
            "Endian note": "Compact target packed as a 4-byte little-endian integer",
        },
        {
            "Field": "Nonce",
            "API value": int(analysis["nonce"]),
            "Header bytes (little-endian)": serialized_segments["Nonce"],
            "Readable": f"{int(analysis['nonce']):,}",
            "Endian note": "Miner nonce packed as a 4-byte little-endian integer",
        },
    ]


def _apply_chart_theme(fig: go.Figure, title_text: str | None = None) -> go.Figure:
    layout_kwargs = {
        "paper_bgcolor": PAPER_BG,
        "plot_bgcolor": PLOT_BG,
        "font": {"family": "Archivo, sans-serif", "color": INK, "size": 13},
        "margin": {"l": 20, "r": 20, "t": 28, "b": 20},
        "xaxis": {
            "showgrid": False,
            "zeroline": False,
            "linecolor": "rgba(11,12,13,0.15)",
            "tickfont": {"color": MUTED},
            "title_font": {"color": INK},
        },
        "yaxis": {
            "showgrid": False,
            "zeroline": False,
            "linecolor": "rgba(11,12,13,0.15)",
            "tickfont": {"color": MUTED},
            "title_font": {"color": INK},
        },
    }
    if title_text:
        layout_kwargs["title"] = {"text": title_text, "font": {"size": 18, "color": INK}, "x": 0.02}
    fig.update_layout(**layout_kwargs)
    return fig


def _build_pipeline_figure() -> go.Figure:
    labels = [
        "Version",
        "Prev hash",
        "Merkle root",
        "Timestamp",
        "Bits",
        "Nonce",
        "80-byte header",
        "SHA-256 #1",
        "SHA-256 #2",
        "Displayed hash",
        "Target test",
    ]
    node_colors = [
        FIELD_COLORS["Version"],
        FIELD_COLORS["Previous hash"],
        FIELD_COLORS["Merkle root"],
        FIELD_COLORS["Timestamp"],
        FIELD_COLORS["Bits"],
        FIELD_COLORS["Nonce"],
        "#1d2025",
        "#5477b8",
        "#94add6",
        "#0b0c0d",
        "#d8ff45",
    ]
    sources = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    targets = [6, 6, 6, 6, 6, 6, 7, 8, 9, 10]
    values = [4, 32, 32, 4, 4, 4, 80, 32, 32, 32]
    link_colors = [
        "rgba(84,119,184,0.35)",
        "rgba(11,12,13,0.25)",
        "rgba(148,173,214,0.35)",
        "rgba(216,255,69,0.35)",
        "rgba(240,190,152,0.45)",
        "rgba(244,107,69,0.35)",
        "rgba(11,12,13,0.18)",
        "rgba(84,119,184,0.22)",
        "rgba(148,173,214,0.25)",
        "rgba(216,255,69,0.25)",
    ]

    fig = go.Figure(
        go.Sankey(
            arrangement="fixed",
            node=dict(
                pad=18,
                thickness=18,
                line=dict(color="rgba(11,12,13,0.18)", width=1),
                label=labels,
                color=node_colors,
            ),
            link=dict(source=sources, target=targets, value=values, color=link_colors),
        )
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    return fig


def _build_byte_map_figure(analysis: dict[str, object]) -> go.Figure:
    header_bytes = bytes.fromhex(str(analysis["header_hex"]))
    z = []
    text = []
    colors = []
    cursor = 0

    for field_index, field_name in enumerate(FIELD_ORDER):
        byte_length = FIELD_LENGTHS[field_name]
        for byte_offset in range(byte_length):
            z.append(field_index)
            text.append(
                f"Offset {cursor}<br>"
                f"Field: {field_name}<br>"
                f"Byte: {header_bytes[cursor]:02x}"
            )
            colors.append(FIELD_COLORS[field_name])
            cursor += 1

    fig = go.Figure(
        go.Scatter(
            x=list(range(80)),
            y=[1] * 80,
            mode="markers",
            marker=dict(
                size=18,
                color=colors,
                line=dict(color="rgba(11,12,13,0.35)", width=1),
                symbol="square",
            ),
            text=text,
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        )
    )

    boundaries = []
    running = 0
    for field_name in FIELD_ORDER:
        start = running
        running += FIELD_LENGTHS[field_name]
        center = start + (FIELD_LENGTHS[field_name] - 1) / 2
        boundaries.append((center, field_name))

    for center, field_name in boundaries:
        fig.add_annotation(
            x=center,
            y=1.14,
            text=field_name,
            showarrow=False,
            font=dict(size=11, color=INK),
        )

    for divider in [4, 36, 68, 72, 76]:
        fig.add_vline(x=divider - 0.5, line_width=1, line_dash="dot", line_color="rgba(11,12,13,0.25)")

    fig.update_layout(
        xaxis_title="Byte offset in the serialized header",
        yaxis=dict(showticklabels=False, visible=False, range=[0.85, 1.22]),
        margin=dict(l=10, r=10, t=18, b=20),
    )
    return fig


@st.cache_data(ttl=60, show_spinner=False)
def _load_block_analysis(block_hash: str | None) -> tuple[dict, dict[str, object]]:
    block = get_block(block_hash) if block_hash else get_latest_block()
    analysis = verify_block_pow(block)
    return block, analysis


def render() -> None:
    """Render the M2 dashboard panel."""
    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem; margin-bottom:1rem;">', unsafe_allow_html=True)
    st.subheader("Block header analyzer")
    st.caption(
        "This module rebuilds the 80-byte Bitcoin header locally, computes "
        "`SHA256(SHA256(header))`, and checks whether the result is below the target encoded by `bits`."
    )
    block_hash = st.text_input(
        "Optional block hash override",
        placeholder="Leave empty to analyze the latest Bitcoin block",
        key="m2_hash_override",
    ).strip()
    st.markdown("</section>", unsafe_allow_html=True)

    with st.spinner("Rebuilding block header and verifying proof of work..."):
        try:
            block, analysis = _load_block_analysis(block_hash or None)
        except Exception as exc:
            st.error(f"M2 could not load block data: {exc}")
            st.info("Try the latest block or check whether the selected hash exists in the public API.")
            return

    metric_cols = st.columns(5)
    metric_cols[0].metric("Block height", f"{int(block['height']):,}")
    metric_cols[1].metric("Header size", f"{len(analysis['header_bytes'])} bytes")
    metric_cols[2].metric("PoW valid", "Yes" if analysis["pow_valid"] else "No")
    metric_cols[3].metric("Hash matches API", "Yes" if analysis["hash_matches_api"] else "No")
    metric_cols[4].metric("Leading zero bits", f"{int(analysis['leading_zero_bits'])}")

    verification_class = "background:linear-gradient(135deg, rgba(216,255,69,0.18), rgba(255,255,255,0.72));" if analysis["pow_valid"] and analysis["hash_matches_api"] else "background:linear-gradient(135deg, rgba(244,107,69,0.12), rgba(255,255,255,0.72));"
    verification_label = "PoW verified locally" if analysis["pow_valid"] and analysis["hash_matches_api"] else "Verification mismatch"
    verification_copy = (
        "The rebuilt header reproduces the explorer hash and the resulting integer is below the target."
        if analysis["pow_valid"] and analysis["hash_matches_api"]
        else "The local recomputation does not yet match the explorer data or the target comparison."
    )

    st.markdown(
        f"""
        <section class="m1-card" style="padding:1rem 1.1rem; margin:0.85rem 0 1rem; {verification_class}">
            <div class="micro-label">Local Verification</div>
            <h3 style="margin:0.15rem 0 0.35rem; font-size:1.55rem;">{verification_label}</h3>
            <p style="margin:0; color:{MUTED};">{verification_copy}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    top_left, top_right = st.columns([1.2, 0.8])

    with top_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Header fields")
        field_rows = _build_field_rows(analysis)
        st.dataframe(pd.DataFrame(field_rows), width="stretch", hide_index=True)
        st.caption(
            "Bitcoin serializes version, timestamp, bits, and nonce as 4-byte little-endian values. "
            "The previous hash and merkle root are also inserted byte-reversed into the header."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    with top_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Verification summary")
        st.write(f"Explorer display hash: `{analysis['api_hash']}`")
        st.write(f"Raw digest from `hashlib`: `{analysis['raw_digest_hex']}`")
        st.write(f"Display hash after byte reversal: `{analysis['computed_hash']}`")
        st.write(f"Target threshold: `{target_to_hex(int(analysis['target']))}`")
        st.write(f"Hash value: **{int(analysis['hash_value'])}**")
        st.write(f"Target value: **{int(analysis['target'])}**")
        st.write(f"Proof of Work check: **{int(analysis['hash_value'])} < {int(analysis['target'])}**")
        st.markdown(
            f"""
            <div class="status-row">
                <span class="status-pill">hash == api: {'yes' if analysis['hash_matches_api'] else 'no'}</span>
                <span class="status-pill">pow valid: {'yes' if analysis['pow_valid'] else 'no'}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</section>", unsafe_allow_html=True)

    bottom_left, bottom_right = st.columns(2)

    with bottom_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Serialized 80-byte header")
        st.code(_format_header_hex(str(analysis["header_hex"])), language="text")
        st.caption(
            "This is the exact byte sequence hashed locally. It contains 160 hexadecimal characters = 80 bytes."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    with bottom_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Hashing steps")
        st.write("1. Build the header bytes in Bitcoin field order.")
        st.write("2. Compute `hash1 = SHA256(header)`.")
        st.write("3. Compute `hash2 = SHA256(hash1)`.")
        st.write("4. Reverse `hash2` by bytes to obtain the displayed block hash.")
        st.write("5. Interpret the raw digest as a little-endian integer and compare it with the target.")
        st.caption(
            "The digest returned by `hashlib` is raw byte order. Bitcoin explorers display the same digest reversed by bytes."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    viz_left, viz_right = st.columns([1.1, 0.9])

    with viz_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Header-to-hash pipeline")
        pipeline_fig = _build_pipeline_figure()
        _apply_chart_theme(pipeline_fig)
        st.plotly_chart(pipeline_fig, width="stretch", config=PLOT_CONFIG)
        st.caption(
            "Cosmograph-inspired idea adapted to M2: show structure and flow, not just raw values. "
            "Here the six header fields converge into the 80-byte header, then pass through the two SHA-256 rounds."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    with viz_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("80-byte header map")
        byte_map_fig = _build_byte_map_figure(analysis)
        _apply_chart_theme(byte_map_fig)
        st.plotly_chart(byte_map_fig, width="stretch", config=PLOT_CONFIG)
        st.caption(
            "Byte-level map of the serialized header. This makes field boundaries and little-endian packing visible at a glance."
        )
        st.markdown("</section>", unsafe_allow_html=True)

    with st.expander("Why little-endian matters in M2"):
        st.markdown(
            """
            - Bitcoin serializes integers in little-endian inside the header.
            - The previous block hash and merkle root are shown in APIs in display order, but inserted into the header byte-reversed.
            - The digest returned by `hashlib` is raw bytes, so the conventional block hash shown by explorers is that digest reversed by bytes.
            """
        )
