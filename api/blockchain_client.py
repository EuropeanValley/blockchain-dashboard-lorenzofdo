"""Reusable clients and helpers for Bitcoin blockchain data sources."""

from __future__ import annotations

from typing import Any

import requests

BLOCKSTREAM_API = "https://blockstream.info/api"
MEMPOOL_API = "https://mempool.space/api"
BLOCKCHAIN_INFO_API = "https://api.blockchain.info"
DEFAULT_TIMEOUT = 20

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "CryptoChain-Analyzer/1.0"})


class BlockchainAPIError(RuntimeError):
    """Raised when a blockchain API request fails."""


def _get_json(url: str) -> Any:
    response = _SESSION.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _get_text(url: str) -> str:
    response = _SESSION.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.text.strip()


def _esplora_base(source: str) -> str:
    if source == "blockstream":
        return BLOCKSTREAM_API
    if source == "mempool":
        return MEMPOOL_API
    raise ValueError(f"Unsupported Esplora source: {source}")


def get_latest_block_hash(source: str = "blockstream") -> str:
    """Return the tip hash from Blockstream or mempool.space."""
    return _get_text(f"{_esplora_base(source)}/blocks/tip/hash")


def get_block(block_hash: str, source: str = "blockstream") -> dict[str, Any]:
    """Return one block as JSON."""
    return _get_json(f"{_esplora_base(source)}/block/{block_hash}")


def get_latest_block(source: str = "blockstream") -> dict[str, Any]:
    """Return the latest block from Blockstream or mempool.space."""
    return get_block(get_latest_block_hash(source=source), source=source)


def get_recent_blocks(limit: int = 20, source: str = "blockstream") -> list[dict[str, Any]]:
    """Return the most recent confirmed blocks, newest first."""
    if limit < 2:
        raise ValueError("limit must be at least 2")

    blocks: list[dict[str, Any]] = []
    start_height: int | None = None
    base = _esplora_base(source)

    while len(blocks) < limit:
        endpoint = f"{base}/blocks" if start_height is None else f"{base}/blocks/{start_height}"
        page = _get_json(endpoint)
        if not page:
            break
        blocks.extend(page)
        start_height = int(page[-1]["height"]) - 1
        if start_height < 0:
            break

    return blocks[:limit]


def get_mempool_difficulty_adjustment() -> dict[str, Any]:
    """Return mempool.space difficulty-adjustment data."""
    return _get_json(f"{MEMPOOL_API}/v1/difficulty-adjustment")


def get_blockchain_stats() -> dict[str, Any]:
    """Return aggregate network stats from Blockchain.com."""
    return _get_json(f"{BLOCKCHAIN_INFO_API}/stats")


def get_difficulty_history(timespan: int | str = "3months", sampled: bool = True) -> list[dict[str, Any]]:
    """Return difficulty history from Blockchain.com charts API."""
    if isinstance(timespan, int):
        if timespan <= 31:
            chart_span = "1months"
        elif timespan <= 93:
            chart_span = "3months"
        elif timespan <= 186:
            chart_span = "6months"
        else:
            chart_span = "1year"
    else:
        chart_span = timespan

    sampled_value = "true" if sampled else "false"
    payload = _get_json(
        f"{BLOCKCHAIN_INFO_API}/charts/difficulty"
        f"?timespan={chart_span}&format=json&sampled={sampled_value}"
    )
    return payload.get("values", [])


def bits_to_target(bits: int | str) -> int:
    """Decode Bitcoin compact bits into the full 256-bit target."""
    compact = int(bits, 16) if isinstance(bits, str) else int(bits)
    exponent = compact >> 24
    coefficient = compact & 0xFFFFFF
    return coefficient * (1 << (8 * (exponent - 3)))


def target_to_hex(target: int) -> str:
    """Return a 64-hex representation of a target value."""
    return f"{target:064x}"


def count_leading_zero_bits(hash_hex: str) -> int:
    """Count leading zero bits in a 256-bit hash."""
    value = int(hash_hex, 16)
    if value == 0:
        return 256
    return 256 - value.bit_length()


def estimate_hashrate_from_difficulty(difficulty: float, block_time_seconds: float = 600.0) -> float:
    """Estimate network hashrate from difficulty."""
    return float(difficulty) * (2**32) / float(block_time_seconds)
