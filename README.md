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
| M1 | Proof of Work Monitor | 🔲 Not started | — |
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

## Current Progress

- Repository set up and connected to GitHub Classroom.
- README structured for weekly tracking and professor feedback.
- First API call working: fetches live Bitcoin block data from `blockstream.info`.
- Project structure initialized following the template.

---

## Next Step

Implement **M1 (Proof of Work Monitor)** in Streamlit:

- Fetch and display current difficulty with visual representation as leading-zero threshold.
- Plot inter-block time distribution (expected: exponential with λ = 1/600).
- Estimate current network hash rate from difficulty.

---

## Main Problem / Blocker

_None currently.* Evaluating whether to use Streamlit (simpler) or Dash (more flexible for real-time WebSocket updates from mempool.space).

---

## External References

- Nakamoto, S. (2008). *Bitcoin: A Peer-to-Peer Electronic Cash System.* <https://bitcoin.org/bitcoin.pdf>
- Blockstream API docs: <https://github.com/Blockstream/esplora/blob/master/API.md>
- Mempool.space API docs: <https://mempool.space/docs/api/rest>
