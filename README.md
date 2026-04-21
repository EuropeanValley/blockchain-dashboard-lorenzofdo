# CryptoChain Analyzer Dashboard

**Hash Functions and Blockchain — Cryptography, UAX 2025–26**  
**Prof. Jorge Calvo**

---

## Student Information

- **Name:** Lorenzo Ferrer De Oya
- **GitHub username:** [@lorenzofdo](https://github.com/lorenzofdo)
- **Repository:** [blockchain-dashboard-lorenzofdo](https://github.com/EuropeanValley/blockchain-dashboard-lorenzofdo)

---

## Project Title

CryptoChain Analyzer Dashboard — Real-time Bitcoin cryptographic metrics with AI-powered difficulty prediction.

---

## Chosen AI Approach

**Option chosen:** Predictor — time-series model to predict the next Bitcoin difficulty adjustment.

**Justification:** The difficulty adjustment is a deterministic, periodic process (every 2016 blocks, ~2 weeks). Historical adjustment values form a time series with learnable patterns tied to hash rate growth trends. A regression or Prophet model trained on past adjustments can forecast the next value with measurable error (MAE). This is more meaningful than anomaly detection for this dataset size and more interpretable than a black-box LSTM.

**Planned evaluation metrics:** MAE, MAPE, and visual comparison of predicted vs actual difficulty over held-out adjustment periods.

---

## Module Tracking

| Module | Title | Status | Last Updated |
|--------|-------|--------|--------------|
| M1 | Proof of Work Monitor | ✅ Complete | 20 Apr 2026 |
| M2 | Block Header Analyzer | 🔄 In progress | 20 Apr 2026 |
| M3 | Difficulty History | 🔲 Not started | — |
| M4 | AI Component (Difficulty Predictor) | 🔲 Not started | — |
| M5 | Merkle Proof Verifier *(optional)* | 🔲 Not started | — |
| M6 | Security Score *(optional)* | 🔲 Not started | — |
| M7 | Second AI Approach *(optional)* | 🔲 Not started | — |

> Status legend: 🔲 Not started · 🔄 In progress · ✅ Complete · ⚠️ Has issues

---

## Current Progress

- M1 complete: dashboard with live Bitcoin Proof-of-Work metrics using public APIs.
- Real data connected from Blockstream, mempool.space, and Blockchain.com.
- Visual dashboard running in Streamlit with charts for difficulty, block timing, target threshold, and network hashrate.
- M2 in progress: latest block header is rebuilt locally, double-SHA256 is checked against the API hash, and PoW verification is already visible in the dashboard.

---

## Next Step

Implement M2 (Block Header Analyzer):

- Parse the full 80-byte structure of the latest block header.
- Rebuild the header bytes with correct little-endian ordering.
- Verify PoW locally using `hashlib`: `SHA256(SHA256(header)) < target`.
- Count leading zero bits in the resulting hash and show the verification in the dashboard.

---

## Main Problem or Blocker

*None currently.*

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
- Observation: block hash starts with multiple leading zeros (e.g. `000000000000...`) — this is the visible result of Proof of Work. The `bits` field encodes the compact target `T`: miners must find a nonce such that `SHA256(SHA256(header)) < T` (a 256-bit threshold).

**Milestone 3 · First Commit**

- [x] Code pushed to GitHub Classroom repository
- [x] At least 2 commits visible

### Session 2 — M1 Proof of Work Monitor (20 April 2026)

- [x] `modules/m1_pow_monitor.py` implemented with live dashboard visualizations
- [x] `api/blockchain_client.py` extended with the 3 APIs from the project spec
- [x] Current difficulty displayed with target derived from `bits`
- [x] Latest block hash, nonce, and transaction count shown
- [x] Estimated network hashrate derived from difficulty
- [x] Inter-block time distribution and recent interval sequence plotted
- [x] Dashboard auto-refresh integrated in `app.py`
- [x] Dashboard-style layout prioritised over landing-page style presentation

### Session 3 — M2 Block Header Analyzer (20 April 2026)

- [x] `api/blockchain_client.py` extended with local header serialization and PoW verification helpers
- [x] `modules/m2_block_header.py` now rebuilds the 80-byte header for the latest block
- [x] Local verification implemented with `SHA256(SHA256(header)) < target`
- [x] Explorer hash and locally computed hash compared directly in the dashboard
- [x] Added byte-level header map and header-to-hash pipeline visualizations
- [x] Added explanation of byte reversal and little-endian handling

---

## External References

- Nakamoto, S. (2008). *Bitcoin: A Peer-to-Peer Electronic Cash System.* <https://bitcoin.org/bitcoin.pdf>
- Blockstream Esplora API: <https://github.com/Blockstream/esplora/blob/master/API.md>
- Mempool.space API: <https://mempool.space/docs/api/rest>
- Blockchain.com Charts API: <https://www.blockchain.com/en/api/charts_api>

---

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```
