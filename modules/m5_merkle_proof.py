"""Module M5: Merkle proof verifier."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import (
    double_sha256,
    get_block,
    get_block_txids,
    get_latest_block,
    get_tx_merkle_proof,
)


PLOT_BG = "rgba(255,255,255,0.84)"
PAPER_BG = "rgba(255,255,255,0)"
INK = "#0b0c0d"
MUTED = "#595b57"
ACCENT = "#d8ff45"
COOL = "#5477b8"
HOT = "#f46b45"
PLOT_CONFIG = {"displaylogo": False, "displayModeBar": False, "responsive": True}


def _short_hash(value: str, chars: int = 10) -> str:
    return f"{value[:chars]}...{value[-chars:]}"


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
        "showlegend": False,
    }
    if title_text:
        layout_kwargs["title"] = {"text": title_text, "font": {"size": 18, "color": INK}, "x": 0.02}
    fig.update_layout(**layout_kwargs)
    return fig


@st.cache_data(ttl=60, show_spinner=False)
def _load_block_context(block_hash: str | None) -> dict[str, object]:
    block = get_block(block_hash) if block_hash else get_latest_block()
    txids = get_block_txids(str(block["id"]))
    return {"block": block, "txids": txids}


@st.cache_data(ttl=600, show_spinner=False)
def _load_merkle_proof(txid: str) -> dict[str, object]:
    return get_tx_merkle_proof(txid)


def _verify_merkle_proof(txid: str, proof: dict[str, object], expected_root: str) -> dict[str, object]:
    current_hash = bytes.fromhex(txid)[::-1]
    position = int(proof["pos"])
    rows: list[dict[str, object]] = []

    for level, sibling_hash in enumerate(proof.get("merkle", []), start=1):
        sibling_bytes = bytes.fromhex(str(sibling_hash))[::-1]
        direction = "right" if position % 2 == 0 else "left"

        if direction == "right":
            payload = current_hash + sibling_bytes
        else:
            payload = sibling_bytes + current_hash

        parent_hash = double_sha256(payload)
        rows.append(
            {
                "Level": level,
                "Current hash": current_hash[::-1].hex(),
                "Sibling side": direction,
                "Sibling hash": str(sibling_hash),
                "Parent hash": parent_hash[::-1].hex(),
                "Position before": position,
                "Position after": position // 2,
            }
        )
        current_hash = parent_hash
        position //= 2

    computed_root = current_hash[::-1].hex()
    return {
        "computed_root": computed_root,
        "matches": computed_root == expected_root,
        "steps_df": pd.DataFrame(rows),
    }


def _build_merkle_path_figure(steps_df: pd.DataFrame, txid: str, merkle_root: str) -> go.Figure:
    labels = [_short_hash(txid)] + [_short_hash(value) for value in steps_df["Parent hash"].tolist()]
    y_values = list(range(len(labels)))
    colors = [ACCENT] + [COOL if side == "right" else HOT for side in steps_df["Sibling side"].tolist()]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[0] * len(labels),
            y=y_values,
            mode="lines+markers+text",
            line=dict(color="rgba(11,12,13,0.25)", width=3),
            marker=dict(size=22, color=colors, line=dict(color=INK, width=1)),
            text=labels,
            textposition="middle right",
            customdata=labels,
            hovertemplate="Path hash %{customdata}<extra></extra>",
        )
    )

    for index, row in steps_df.iterrows():
        side_x = 0.52 if row["Sibling side"] == "right" else -0.52
        fig.add_trace(
            go.Scatter(
                x=[side_x],
                y=[index],
                mode="markers+text",
                marker=dict(
                    size=18,
                    color=COOL if row["Sibling side"] == "right" else HOT,
                    line=dict(color=INK, width=1),
                ),
                text=[_short_hash(str(row["Sibling hash"]), chars=8)],
                textposition="middle right" if side_x > 0 else "middle left",
                hovertemplate=f"Sibling {row['Sibling side']}<br>{row['Sibling hash']}<extra></extra>",
            )
        )
        fig.add_shape(
            type="line",
            x0=0,
            y0=index,
            x1=side_x,
            y1=index,
            line=dict(color="rgba(11,12,13,0.18)", width=2, dash="dot"),
        )

    fig.add_annotation(
        x=0,
        y=len(labels) - 1,
        text=f"Merkle root: {_short_hash(merkle_root)}",
        showarrow=False,
        yshift=30,
        font=dict(color=INK, size=13),
    )
    fig.update_layout(
        xaxis=dict(visible=False, range=[-1.25, 1.35]),
        yaxis=dict(visible=False, autorange="reversed"),
        height=max(420, len(labels) * 42),
    )
    return fig


def _build_merkle_network_figure(steps_df: pd.DataFrame, txid: str, merkle_root: str) -> go.Figure:
    """Build a Cosmograph-inspired node-link view of the Merkle proof path."""
    nodes: list[dict[str, object]] = [
        {
            "id": "leaf",
            "kind": "Selected tx",
            "hash": txid,
            "x": 0.0,
            "y": 0.0,
            "size": 30,
            "color": ACCENT,
        }
    ]
    edges: list[dict[str, object]] = []

    previous_node_id = "leaf"
    previous_hash = txid

    for index, row in steps_df.iterrows():
        level = int(row["Level"])
        sibling_side = str(row["Sibling side"])
        sibling_x = 1.05 if sibling_side == "right" else -1.05
        parent_id = f"parent-{level}"
        sibling_id = f"sibling-{level}"
        parent_hash = str(row["Parent hash"])

        nodes.append(
            {
                "id": sibling_id,
                "kind": f"Sibling ({sibling_side})",
                "hash": str(row["Sibling hash"]),
                "x": sibling_x,
                "y": level - 0.36,
                "size": max(17, 26 - level * 0.45),
                "color": COOL if sibling_side == "right" else HOT,
            }
        )
        nodes.append(
            {
                "id": parent_id,
                "kind": "Computed parent" if level < len(steps_df) else "Computed root",
                "hash": parent_hash,
                "x": 0.0,
                "y": level,
                "size": max(18, 30 - level * 0.55),
                "color": INK if parent_hash == merkle_root else "#7f8f73",
            }
        )
        edges.extend(
            [
                {
                    "source": previous_node_id,
                    "target": parent_id,
                    "source_hash": previous_hash,
                    "target_hash": parent_hash,
                    "kind": "path",
                },
                {
                    "source": sibling_id,
                    "target": parent_id,
                    "source_hash": str(row["Sibling hash"]),
                    "target_hash": parent_hash,
                    "kind": "sibling",
                },
            ]
        )
        previous_node_id = parent_id
        previous_hash = parent_hash

    node_lookup = {str(node["id"]): node for node in nodes}
    fig = go.Figure()

    for edge in edges:
        source = node_lookup[str(edge["source"])]
        target = node_lookup[str(edge["target"])]
        is_path = edge["kind"] == "path"
        fig.add_trace(
            go.Scatter(
                x=[source["x"], target["x"]],
                y=[source["y"], target["y"]],
                mode="lines",
                line=dict(
                    color="rgba(11,12,13,0.34)" if is_path else "rgba(84,119,184,0.26)",
                    width=3.2 if is_path else 2,
                    dash="solid" if is_path else "dot",
                ),
                customdata=[[edge["source_hash"], edge["target_hash"]], [edge["source_hash"], edge["target_hash"]]],
                hovertemplate=(
                    "Input %{customdata[0]}<br>"
                    "Parent %{customdata[1]}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    node_df = pd.DataFrame(nodes)
    node_df["label"] = node_df["hash"].map(lambda value: _short_hash(str(value), chars=8))
    node_df["hover"] = node_df.apply(
        lambda row: f"{row['kind']}<br>{row['hash']}",
        axis=1,
    )

    fig.add_trace(
        go.Scatter(
            x=node_df["x"],
            y=node_df["y"],
            mode="markers+text",
            marker=dict(
                size=node_df["size"],
                color=node_df["color"],
                line=dict(color=INK, width=1.4),
                opacity=0.96,
            ),
            text=node_df["label"],
            textposition=[
                "middle right" if float(row["x"]) >= 0 else "middle left"
                for _, row in node_df.iterrows()
            ],
            customdata=node_df[["hover", "kind"]],
            hovertemplate="%{customdata[0]}<extra></extra>",
            showlegend=False,
        )
    )

    fig.add_annotation(
        x=0,
        y=float(node_df["y"].max()) + 0.55,
        text="Merkle root reached",
        showarrow=False,
        font=dict(color=INK, size=14),
    )
    fig.update_layout(
        xaxis=dict(visible=False, range=[-1.8, 2.0]),
        yaxis=dict(visible=False, range=[-0.6, float(node_df["y"].max()) + 0.95]),
        height=max(520, len(steps_df) * 48),
    )
    return fig


def render() -> None:
    """Render the M5 Merkle proof verifier."""
    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem; margin-bottom:1rem;">', unsafe_allow_html=True)
    st.subheader("Merkle proof verifier")
    st.caption(
        "This optional module verifies that a real transaction belongs to a Bitcoin block by rebuilding its Merkle path with double SHA-256."
    )
    block_hash = st.text_input(
        "Optional block hash override",
        placeholder="Leave empty to use the latest Bitcoin block",
        key="m5_block_hash_override",
    ).strip()
    st.markdown("</section>", unsafe_allow_html=True)

    with st.spinner("Loading block transactions and Merkle proof data..."):
        try:
            context = _load_block_context(block_hash or None)
        except Exception as exc:
            st.error(f"M5 could not load block data: {exc}")
            st.info("Try the latest block or check whether the selected block hash exists in the public API.")
            return

    block: dict = context["block"]
    txids: list[str] = context["txids"]

    if not txids:
        st.error("The selected block did not return any transaction IDs.")
        return

    default_index = min(max(len(txids) // 2, 0), len(txids) - 1)
    tx_index = st.slider(
        "Transaction index inside the block",
        min_value=0,
        max_value=len(txids) - 1,
        value=default_index,
        step=1,
        key=f"m5_tx_index_{block['id']}",
    )
    selected_txid = txids[tx_index]

    with st.spinner("Verifying Merkle branch locally..."):
        try:
            proof = _load_merkle_proof(selected_txid)
            verification = _verify_merkle_proof(selected_txid, proof, str(block["merkle_root"]))
        except Exception as exc:
            st.error(f"M5 could not verify the Merkle proof: {exc}")
            st.info("The verifier uses Blockstream's Electrum-style Merkle proof endpoint and recomputes the path locally.")
            return

    proof_height = int(proof.get("block_height", -1))
    block_time = datetime.fromtimestamp(int(block["timestamp"]), tz=timezone.utc)
    steps_df: pd.DataFrame = verification["steps_df"]

    metric_cols = st.columns(5)
    metric_cols[0].metric("Block height", f"{int(block['height']):,}")
    metric_cols[1].metric("Transactions", f"{len(txids):,}")
    metric_cols[2].metric("Selected index", f"{tx_index:,}")
    metric_cols[3].metric("Proof depth", f"{len(steps_df)}")
    metric_cols[4].metric("Root match", "Yes" if verification["matches"] else "No")

    status_style = (
        "background:linear-gradient(135deg, rgba(216,255,69,0.18), rgba(255,255,255,0.72));"
        if verification["matches"]
        else "background:linear-gradient(135deg, rgba(244,107,69,0.12), rgba(255,255,255,0.72));"
    )
    st.markdown(
        f"""
        <section class="m1-card" style="padding:1rem 1.1rem; margin:0.85rem 0 1rem; {status_style}">
            <div class="micro-label">Merkle Inclusion</div>
            <h3 style="margin:0.15rem 0 0.35rem; font-size:1.55rem;">
                {'Transaction inclusion verified' if verification['matches'] else 'Merkle root mismatch'}
            </h3>
            <p style="margin:0; color:{MUTED};">
                The locally computed root is compared with the block header Merkle root.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
    st.subheader("Merkle inclusion graph")
    network_fig = _build_merkle_network_figure(steps_df, selected_txid, str(block["merkle_root"]))
    _apply_chart_theme(network_fig)
    st.plotly_chart(network_fig, width="stretch", config=PLOT_CONFIG)
    st.caption(
        "Cosmograph-inspired network view: the selected transaction and each sibling hash converge level by level into the computed Merkle root."
    )
    st.markdown("</section>", unsafe_allow_html=True)

    top_left, top_right = st.columns([1.08, 0.92])

    with top_left:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Merkle path map")
        path_fig = _build_merkle_path_figure(steps_df, selected_txid, str(block["merkle_root"]))
        _apply_chart_theme(path_fig)
        st.plotly_chart(path_fig, width="stretch", config=PLOT_CONFIG)
        st.caption("Each level hashes the current path node with one sibling from the proof branch.")
        st.markdown("</section>", unsafe_allow_html=True)

    with top_right:
        st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
        st.subheader("Verification summary")
        st.write(f"Block hash: `{block['id']}`")
        st.write(f"Block time: **{block_time.strftime('%Y-%m-%d %H:%M:%S UTC')}**")
        st.write(f"Selected txid: `{selected_txid}`")
        st.write(f"Proof block height: **{proof_height:,}**")
        st.write(f"Header Merkle root: `{block['merkle_root']}`")
        st.write(f"Computed Merkle root: `{verification['computed_root']}`")
        st.markdown(
            f"""
            <div class="status-row">
                <span class="status-pill">proof height: {'match' if proof_height == int(block['height']) else 'mismatch'}</span>
                <span class="status-pill">root match: {'yes' if verification['matches'] else 'no'}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</section>", unsafe_allow_html=True)

    st.markdown('<section class="m1-card" style="padding:1rem 1.1rem;">', unsafe_allow_html=True)
    st.subheader("Step-by-step hash reconstruction")
    table_df = steps_df.copy()
    for column in ["Current hash", "Sibling hash", "Parent hash"]:
        table_df[column] = table_df[column].map(lambda value: _short_hash(str(value), chars=14))
    st.dataframe(table_df, width="stretch", hide_index=True)
    st.caption(
        "Bitcoin transaction hashes are displayed byte-reversed. The verifier converts each displayed hash to internal byte order, hashes the pair, then reverses the parent back for display."
    )
    st.markdown("</section>", unsafe_allow_html=True)

    with st.expander("Why this proves inclusion"):
        st.markdown(
            """
            - A block header contains one Merkle root, not every transaction.
            - The proof gives only the sibling hashes needed to climb from one transaction to that root.
            - At each level, the left/right position decides the concatenation order.
            - If the final computed root equals the header's `merkle_root`, the selected transaction is included in that block.
            """
        )
