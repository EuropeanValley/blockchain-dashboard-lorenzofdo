# CryptoChain Analyzer Dashboard

### Hash Functions and Blockchain — Cryptography, UAX 2025–26

**Prof. Jorge Calvo**

---

## Student Information

| Field | Detail |
|-------|--------|
| **Name** | Lorenzo Ferrer De Oya |
| **GitHub username** | [@lorenzofdo](https://github.com/lorenzofdo) |
| **Repository** | [blockchain-dashboard-lorenzofdo](https://github.com/EuropeanValley/blockchain-dashboard-lorenzofdo) |

---

## Project Title

**CryptoChain Analyzer Dashboard** — Real-time Bitcoin cryptographic metrics with AI-powered difficulty prediction.

---

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Chosen AI Approach (M4)

**Predictor** — Time-series model to predict the next Bitcoin difficulty adjustment.

**Justification:** The difficulty adjustment is a deterministic, periodic process (every 2016 blocks, ~2 weeks). Historical adjustment values form a time series with learnable patterns tied to hash rate growth trends. A regression or Prophet model trained on past adjustments can forecast the next value with measurable error (MAE). This is more meaningful than anomaly detection for this dataset size and more interpretable than a black-box LSTM.

**Planned evaluation metrics:** MAE, MAPE, and visual comparison of predicted vs actual difficulty over held-out adjustment periods.

---

## Module Status

| Module | Title | Status | Last Updated |
|--------|-------|--------|--------------|
| M1 | Proof of Work Monitor | ✅ Complete | 20 Apr 2026 |
| M2 | Block Header Analyzer | 🔲 Not started | — |
| M3 | Difficulty History | 🔲 Not started | — |
| M4 | AI Component (Difficulty Predictor) | 🔲 Not started | — |
| M5 | Merkle Proof Verifier *(optional)* | 🔲 Not started | — |
| M6 | Security Score *(optional)* | 🔲 Not started | — |
| M7 | Second AI Approach *(optional)* | 🔲 Not started | — |

> Status legend: 🔲 Not started · 🔄 In progress · ✅ Complete · ⚠️ Has issues

---

## Session Log

### Session 1 — Kick-off (20 April 2026)

**Milestone 1 · GitHub Setup**

- [x] GitHub Classroom assignment accepted
- [x] Repository created: `blockchain-dashboard-lorenzofdo`
- [x] README initialized with project structure, AI choice, module tracking

**Milestone 2 · First API Call**

- [x] Script `api/blockchain_client.py` connects to Blockstream API
- [x] Prints: block height, hash, bits, nonce, tx_count for the latest block
- Observation: block hash starts with multiple leading zeros (e.g. `000000000000...`) — this is the visible result of Proof of Work. The `bits` field encodes the compact target T: miners must find a nonce such that SHA256(SHA256(header)) < T (a 256-bit threshold).

**Milestone 3 · First Commit**

- [x] Code pushed to GitHub Classroom repository
- [x] At least 2 commits visible

---

### Session 2 — M1 Proof of Work Monitor (20 April 2026)

- [x] `modules/m1_pow_monitor.py` implemented with full visual logic
- [x] `api/blockchain_client.py` extended with all 3 APIs from the project spec
- [x] Current difficulty displayed with target derived from `bits` field
- [x] Latest block hash and nonce shown
- [x] Network hash rate estimated from difficulty
- [x] Inter-block time histogram and time series plotted (expected: exponential distribution, λ = 1/600 s)
- [x] Automatic refresh integrated in `app.py`
- Sources used:
  - **Blockstream Esplora**: latest block + recent block times
  - **mempool.space**: current adjustment cycle data
  - **Blockchain.com Charts API**: historical difficulty context (30 data points)
- Verified live: block 945923, hash prefix `0000000000000000`, 30 historical difficulty points returned

---

## Current Progress

- M1 complete: PoW Monitor showing live difficulty, block time distribution, and hash rate estimate using all 3 APIs from the spec.
- Dashboard runs with `streamlit run app.py` and refreshes automatically.
- Project structure clean: `api/`, `modules/`, `app.py`, `.gitignore` all in place.

---

## Next Step

Implement **M2 (Block Header Analyzer)**:

- Parse the full 80-byte structure of the latest block header (version, prev_hash, merkle_root, timestamp, bits, nonce).
- Verify PoW locally using `hashlib`: SHA256(SHA256(header)) < target.
- Count leading zero bits in the resulting hash.
- Handle little-endian byte order correctly when parsing header fields.

---

## Main Problem / Blocker

_None currently._

---

## External References

- Nakamoto, S. (2008). *Bitcoin: A Peer-to-Peer Electronic Cash System.* <https://bitcoin.org/bitcoin.pdf>
- Blockstream Esplora API: <https://github.com/Blockstream/esplora/blob/master/API.md>
- Mempool.space REST API: <https://mempool.space/docs/api/rest>
- Blockchain.com Charts API: <https://www.blockchain.com/en/api/charts_api>
