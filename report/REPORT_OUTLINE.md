# CryptoChain Analyzer Dashboard - Final Report Outline

## 1. Cryptographic Metrics

Explain how the dashboard uses real Bitcoin data to connect the course concepts to live network behavior.

- M1 Proof of Work Monitor: current difficulty, compact `bits`, target threshold, leading zero bits, recent block intervals, and estimated network hashrate.
- M2 Block Header Analyzer: 80-byte header fields, little-endian serialization, double SHA-256, local proof-of-work verification, and target comparison.
- M3 Difficulty History: 2016-block retarget periods, actual time vs target time, difficulty changes, and the consensus clamp.
- M5 Merkle Proof Verifier: transaction inclusion proof, sibling hash path, double SHA-256 reconstruction, node-link visualization inspired by Cosmograph, and comparison with the block header Merkle root.

## 2. AI Component

Chosen approach: difficulty-adjustment predictor.

- Model: interpretable linear regression trained on completed Bitcoin retarget periods.
- Training data: real block timestamps and difficulty values from completed 2016-block epochs.
- Features: log difficulty, actual/target timing ratio, formula response, previous adjustment, and observed average block interval.
- Evaluation: holdout periods with MAE and MAPE.
- Limitation: the current-cycle prediction depends on the mempool.space estimate until the retarget period is complete.

## 3. External References

- Satoshi Nakamoto, "Bitcoin: A Peer-to-Peer Electronic Cash System."
- Blockstream Esplora API documentation.
- mempool.space REST API documentation.
- Blockchain.com Charts API documentation.

## 4. Screenshots To Add

- M1 dashboard with live Proof-of-Work metrics.
- M2 local block verification result.
- M3 difficulty history and retarget response map.
- M4 holdout prediction/evaluation view.
- M5 Merkle proof verification result.

## 5. Final Checks Before PDF Export

- Confirm the dashboard runs with `pip install -r requirements.txt` and `streamlit run app.py`.
- Confirm README module statuses match the real state of the project.
- Include the final exported PDF inside this `report/` folder before the deadline.
