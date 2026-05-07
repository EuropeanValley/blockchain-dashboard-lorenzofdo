# CryptoChain Analyzer Dashboard

**Hash Functions and Blockchain - Cryptography, UAX 2025-26**
**Prof. Jorge Calvo**

---

## Student Information

- **Name:** Lorenzo Ferrer De Oya
- **GitHub username:** [@lorenzofdo](https://github.com/lorenzofdo)
- **Repository:** [blockchain-dashboard-lorenzofdo](https://github.com/EuropeanValley/blockchain-dashboard-lorenzofdo)

---

## Project Title

CryptoChain Analyzer Dashboard - real-time Bitcoin cryptographic metrics with AI-powered difficulty prediction and optional security analytics.

---

## Chosen AI Approach

**Required M4 option chosen:** Predictor - interpretable regression model to predict the next Bitcoin difficulty adjustment.

**Extra M7 AI approach:** Unsupervised anomaly detector for abnormal Bitcoin inter-block times using the exponential distribution expected for Proof-of-Work mining.

**Justification:** The difficulty adjustment is a deterministic, periodic process (every 2016 blocks, about two weeks). Completed retarget periods provide real historical rows with timing ratios, difficulty changes, and previous adjustment behavior. A lightweight regression model is appropriate because it is interpretable, can be evaluated with held-out retarget periods, and is easier to explain than a black-box model.

**Evaluation metrics:** M4 uses MAE, MAPE, and visual comparison of predicted vs actual difficulty over held-out adjustment periods. Extra M7 uses KS statistic, negative log-likelihood, and anomaly rate because it is an unsupervised detector without ground-truth labels.

---

## Module Tracking

| Module | Title | Status | Last Updated |
|--------|-------|--------|--------------|
| M1 | Proof of Work Monitor | Complete | 20 Apr 2026 |
| M2 | Block Header Analyzer | Complete | 21 Apr 2026 |
| M3 | Difficulty History | Complete | 21 Apr 2026 |
| M4 | AI Component (Difficulty Predictor) | Complete | 27 Apr 2026 |
| M5 | Merkle Proof Verifier (optional extra) | Complete | 29 Apr 2026 |
| M6 | Security Score (optional extra) | Complete | 07 May 2026 |
| M7 | Second AI Approach (optional extra) | Complete | 07 May 2026 |

Status legend: Not started / In progress / Complete / Has issues

---

## Current Progress

- Dashboard modules integrated and working: M1, M2, M3, M4, and optional extra modules M5, M6, and M7 are visible in the Streamlit app.
- Real live data connected from Blockstream, mempool.space, and Blockchain.com with shared API helpers and centralized error handling.
- The Streamlit app supports dashboard auto-refresh with polling from 30 to 300 seconds, using 60 seconds as the default live refresh interval.
- M4 predictor trained on real completed retarget periods and evaluated with MAE/MAPE on held-out periods.
- M5 Merkle proof verifier rebuilds a transaction inclusion path locally and checks it against the block header Merkle root.
- M6 security score estimates hourly 51% attack cost from live Bitcoin hashrate and visualises Nakamoto confirmation-depth risk.
- M7 second AI method detects abnormal inter-block intervals and compares its unsupervised metrics with the M4 predictor.
- Final report updated in `report/FINAL_REPORT.md` and `report/FINAL_REPORT.pdf`.

---

## Next Step

- Run a final Streamlit walkthrough of M1-M7 with live APIs.
- Capture final screenshots/key metric values for the submitted PDF if needed.
- Push the extra-content commit for the 07 May session.

---

## Main Problem or Blocker

None currently.

---

## Session Log

### Session 1 - Kick-off (20 April 2026)

**Milestone 1 - GitHub Setup**

- [x] GitHub Classroom assignment accepted
- [x] Repository created: `blockchain-dashboard-lorenzofdo`
- [x] README initialized with project structure, AI choice, module tracking

**Milestone 2 - First API Call**

- [x] Script `api/blockchain_client.py` connects to Blockstream API
- [x] Prints: block height, hash, bits, nonce, tx_count for the latest block
- Observation: block hash starts with multiple leading zeros (for example `000000000000...`). This is the visible result of Proof of Work. The `bits` field encodes the compact target `T`: miners must find a nonce such that `SHA256(SHA256(header)) < T`.

**Milestone 3 - First Commit**

- [x] Code pushed to GitHub Classroom repository
- [x] At least 2 commits visible

### Session 2 - M1 Proof of Work Monitor (20 April 2026)

- [x] `modules/m1_pow_monitor.py` implemented with live dashboard visualizations
- [x] `api/blockchain_client.py` extended with the 3 APIs from the project spec
- [x] Current difficulty displayed with target derived from `bits`
- [x] Latest block hash, nonce, and transaction count shown
- [x] Estimated network hashrate derived from difficulty
- [x] Inter-block time distribution and recent interval sequence plotted
- [x] Dashboard auto-refresh integrated in `app.py`
- [x] Dashboard-style layout prioritised over landing-page style presentation

### Session 3 - M2 Block Header Analyzer (21 April 2026)

- [x] `api/blockchain_client.py` extended with local header serialization and PoW verification helpers
- [x] `modules/m2_block_header.py` rebuilds the 80-byte header for the latest block
- [x] Local verification implemented with `SHA256(SHA256(header)) < target`
- [x] Explorer hash and locally computed hash compared directly in the dashboard
- [x] Added byte-level header map and header-to-hash pipeline visualizations
- [x] Added explanation of byte reversal and little-endian handling
- [x] Added explicit `raw digest` vs `display hash` explanation

### Session 4 - M3 Difficulty History (21 April 2026)

- [x] Module status moved to complete
- [x] Prepare historical difficulty dataset over several completed retarget periods
- [x] Plot retarget events and timing ratios against the 600-second target
- [x] Connect the chart to Bitcoin's 2016-block difficulty adjustment rule
- [x] Add current epoch progress and mempool.space estimated next retarget
- [x] Add one-year Blockchain.com difficulty context
- [x] Add retarget response map comparing actual timing ratio with the next difficulty adjustment
- [x] Add Bitcoin retarget clamp explanation (`0.25x` to `4x`)
- [x] Validate live data: recent formula response and observed next adjustment matched closely

### Session 5 - M4 AI Difficulty Predictor (27 April 2026)

- [x] `modules/m4_ai_component.py` implemented as the AI component
- [x] Historical dataset built from completed 2016-block retarget periods
- [x] Interpretable regression model trained with real blockchain features
- [x] Holdout evaluation added with MAE and MAPE
- [x] Prediction, feature weights, errors, and training data integrated into the dashboard
- [x] Current next-retarget forecast compared with mempool.space reference estimate

### Session 6 - Checkpoint Review Prep (27 April 2026)

- [x] Reviewed implemented M1-M4 modules against the project brief
- [x] Centralized API request error handling in `api/blockchain_client.py`
- [x] Added `report/REPORT_OUTLINE.md` with the required final report structure
- [x] Run final Streamlit walkthrough with live APIs before the 29 April checkpoint

### Session 7 - M5 Merkle Proof Verifier (29 April 2026)

- [x] `modules/m5_merkle_proof.py` implemented as an optional cryptographic extension
- [x] Added Blockstream helpers for block transaction IDs and Electrum-style Merkle proofs
- [x] Rebuilt the transaction-to-root path locally using double SHA-256
- [x] Compared the computed Merkle root with the block header `merkle_root`
- [x] Added a Cosmograph-inspired node-link graph for the Merkle inclusion path
- [x] Integrated M5 into the Streamlit module selector

### Session 8 - Optional Extra Content M6 + M7 (07 May 2026)

- [x] `modules/m6_security_score.py` implemented as optional extra content
- [x] M6 estimates the cost in USD/hour of controlling majority hashrate using live Bitcoin difficulty-derived hashrate
- [x] M6 includes editable assumptions for electricity price, miner efficiency, hardware cost, and amortization
- [x] M6 visualises Nakamoto section 11 confirmation-depth risk for different attacker hashpower shares
- [x] `modules/m7_anomaly_detector.py` implemented as the second AI approach
- [x] M7 fits an exponential baseline to real inter-block intervals and flags low-probability anomalies
- [x] M7 evaluates the detector with KS statistic, negative log-likelihood, and anomaly rate
- [x] M7 compares the second AI method against the M4 supervised difficulty predictor
- [x] README and final report updated to state clearly that M5-M7 are optional extra modules

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
