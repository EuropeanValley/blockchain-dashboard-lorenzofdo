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

**Option chosen:** Predictor — interpretable regression model to predict the next Bitcoin difficulty adjustment.

**Justification:** The difficulty adjustment is a deterministic, periodic process (every 2016 blocks, ~2 weeks). Completed retarget periods provide real historical rows with timing ratios, difficulty changes, and previous adjustment behavior. A lightweight regression model is appropriate because it is interpretable, can be evaluated with held-out retarget periods, and is easier to explain than a black-box model.

**Evaluation metrics:** MAE, MAPE, and visual comparison of predicted vs actual difficulty over held-out adjustment periods.

---

## Module Tracking

| Module | Title | Status | Last Updated |
|--------|-------|--------|--------------|
| M1 | Proof of Work Monitor | ✅ Complete | 20 Apr 2026 |
| M2 | Block Header Analyzer | ✅ Complete | 21 Apr 2026 |
| M3 | Difficulty History | ✅ Complete | 21 Apr 2026 |
| M4 | AI Component (Difficulty Predictor) | ✅ Complete | 27 Apr 2026 |
| M5 | Merkle Proof Verifier *(optional)* | ✅ Complete | 29 Apr 2026 |
| M6 | Security Score *(optional)* | 🔲 Not started | — |
| M7 | Second AI Approach *(optional)* | 🔲 Not started | — |

> Status legend: 🔲 Not started · 🔄 In progress · ✅ Complete · ⚠️ Has issues

---

## Current Progress

- Dashboard modules integrated and working: M1, M2, M3, M4, and optional M5 are visible in the Streamlit app.
- Real live data connected from Blockstream, mempool.space, and Blockchain.com with shared API helpers and centralized error handling.
- M4 predictor trained on real completed retarget periods and evaluated with MAE/MAPE on held-out periods.
- M5 Merkle proof verifier rebuilds a transaction inclusion path locally and checks it against the block header Merkle root.
- Final report outline started in `report/REPORT_OUTLINE.md`.

---

## Next Step

Next checkpoint actions:

- Run a final Streamlit walkthrough of M1, M2, M3, M4, and M5 with live APIs.
- Capture screenshots and key metric values for the final report.
- Decide whether to attempt another optional module (M6 or M7) after the checkpoint.
- Continue the final report draft using the completed module outputs.

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

### Session 3 — M2 Block Header Analyzer (21 April 2026)

- [x] `api/blockchain_client.py` extended with local header serialization and PoW verification helpers
- [x] `modules/m2_block_header.py` rebuilds the 80-byte header for the latest block
- [x] Local verification implemented with `SHA256(SHA256(header)) < target`
- [x] Explorer hash and locally computed hash compared directly in the dashboard
- [x] Added byte-level header map and header-to-hash pipeline visualizations
- [x] Added explanation of byte reversal and little-endian handling
- [x] Added explicit `raw digest` vs `display hash` explanation

### Session 4 — M3 Difficulty History (21 April 2026)

- [x] Module status moved to complete
- [x] Prepare historical difficulty dataset over several completed retarget periods
- [x] Plot retarget events and timing ratios against the 600-second target
- [x] Connect the chart to Bitcoin’s 2016-block difficulty adjustment rule
- [x] Add current epoch progress and mempool.space estimated next retarget
- [x] Add one-year Blockchain.com difficulty context
- [x] Add retarget response map comparing actual timing ratio with the next difficulty adjustment
- [x] Add Bitcoin retarget clamp explanation (`0.25x` to `4x`)
- [x] Validate live data: recent formula response and observed next adjustment matched closely

### Session 5 — M4 AI Difficulty Predictor (27 April 2026)

- [x] `modules/m4_ai_component.py` implemented as the AI component
- [x] Historical dataset built from completed 2016-block retarget periods
- [x] Interpretable regression model trained with real blockchain features
- [x] Holdout evaluation added with MAE and MAPE
- [x] Prediction, feature weights, errors, and training data integrated into the dashboard
- [x] Current next-retarget forecast compared with mempool.space reference estimate

### Session 6 — Checkpoint Review Prep (27 April 2026)

- [x] Reviewed implemented M1-M4 modules against the project brief
- [x] Centralized API request error handling in `api/blockchain_client.py`
- [x] Added `report/REPORT_OUTLINE.md` with the required final report structure
- [x] Run final Streamlit walkthrough with live APIs before the 29 April checkpoint

### Session 7 — M5 Merkle Proof Verifier (29 April 2026)

- [x] `modules/m5_merkle_proof.py` implemented as an optional cryptographic extension
- [x] Added Blockstream helpers for block transaction IDs and Electrum-style Merkle proofs
- [x] Rebuilt the transaction-to-root path locally using double SHA-256
- [x] Compared the computed Merkle root with the block header `merkle_root`
- [x] Added a Cosmograph-inspired node-link graph for the Merkle inclusion path
- [x] Integrated M5 into the Streamlit module selector

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

---
