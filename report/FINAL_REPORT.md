# CryptoChain Analyzer Dashboard - Final Report

**Hash Functions and Blockchain - Cryptography, UAX 2025-26**  
**Student:** Lorenzo Ferrer De Oya  
**Repository:** `blockchain-dashboard-lorenzofdo`

## 1. Cryptographic metrics displayed and their meaning

The dashboard was designed as a live cryptography tool rather than as a financial Bitcoin tracker. Each module displays a different part of Bitcoin's consensus machinery using public blockchain data from Blockstream Esplora, mempool.space, and Blockchain.com.

**M1 - Proof of Work Monitor** focuses on the mining threshold and on recent block production. It displays the current difficulty, the compact `bits` field, the target derived from `bits`, the latest block hash, the nonce, leading-zero bits, recent inter-block times, and an estimated network hash rate. These metrics explain the meaning of Proof of Work in practice: miners repeatedly hash candidate headers until the resulting double-SHA256 digest is numerically lower than the target. The `bits` field is important because it encodes this target in compact form inside the header. Difficulty measures how small the target is compared with Bitcoin's reference difficulty, while leading-zero bits provide a visible intuition for why valid hashes look rare. The inter-block interval plots also show that blocks do not arrive every 10 minutes exactly; instead, they fluctuate around the 600-second target because mining is probabilistic.

**M2 - Block Header Analyzer** verifies a real block locally. The module rebuilds the 80-byte Bitcoin block header from its six fields: version, previous block hash, Merkle root, timestamp, bits, and nonce. It then computes `SHA256(SHA256(header))` with Python `hashlib`, compares the locally reconstructed display hash with the explorer hash, and checks whether the resulting integer is below the target derived from `bits`. This is the most direct cryptographic proof in the dashboard because it demonstrates that block validity can be checked independently from the API. A live verification snapshot taken on **May 4, 2026** confirmed the process for block height **947,865**: the locally computed hash matched the API hash, the Proof-of-Work check returned true, and the block showed **78 leading-zero bits**.

**M3 - Difficulty History** explains how Bitcoin keeps the average block interval near 10 minutes. Bitcoin retargets difficulty every 2016 blocks. For each completed retarget period, the dashboard computes the real elapsed time, the ratio `actual_period_time / target_period_time`, the observed average block interval, and the difficulty change applied at the next retarget. It also shows the Bitcoin consensus clamp, which limits one retarget step to a factor between `0.25x` and `4x`. This matters because the protocol must remain stable even when hash power changes abruptly. In a live snapshot on **May 4, 2026**, the most recent completed period had an actual-to-target ratio of **1.023576**, which implied an expected next adjustment of **-2.303256%**; the observed next change was **-2.303085%**. The near-perfect match showed that the dashboard's retarget calculations were aligned with Bitcoin consensus behavior.

**M5 - Merkle Proof Verifier** adds a second cryptographic verification path. Instead of validating mining, it validates transaction inclusion. The module takes a real transaction from a block, loads its Electrum-style Merkle proof, reconstructs the sibling-hash path with double SHA-256, and checks whether the computed Merkle root equals the `merkle_root` stored in the block header. This proves that a transaction belongs to a block without downloading every transaction in the block. The Merkle path graph and the step-by-step table make the left/right concatenation order visible, which is essential for understanding why the proof is valid.

Together, these metrics show the main cryptographic layers of the project: hash-based mining thresholds (M1), full local block-header verification (M2), consensus difficulty adjustment over time (M3), and Merkle inclusion proofs for transactions (M5).

## 2. AI model chosen, why it was chosen, and evaluation results

The AI component implemented in **M4** is an **interpretable linear regression model** that predicts the **next Bitcoin difficulty adjustment**. This choice was deliberate. The prediction target is not price or market behavior but a consensus variable that depends on completed 2016-block periods. The input rows are therefore structured, relatively small in number, and directly connected to protocol rules. An interpretable regression model is more appropriate than a black-box neural network because the course focuses on explainability and on linking data analysis back to cryptographic protocol behavior.

The training dataset is built from completed retarget periods. For each row, the dashboard extracts features that are meaningful for the next adjustment: log difficulty, the actual-versus-target timing ratio, the formula-based expected adjustment, the previous retarget change, and the observed average block interval. The label is the actual difficulty change applied at the following retarget. This keeps the model grounded in real blockchain history rather than in synthetic data.

The model is evaluated on held-out retarget periods using **MAE** and **MAPE**, as requested in the project outline. A live evaluation snapshot taken on **May 4, 2026** with **24 completed periods** and **5 holdout periods** produced the following results:

- **Training rows:** 19
- **Holdout rows:** 5
- **MAE:** 388,873,762.46 difficulty units
- **MAPE:** 0.000281%
- **Baseline MAE from the raw formula response:** 687,342,053.88 difficulty units

These results are meaningful in two ways. First, the absolute percentage error is extremely small because Bitcoin difficulty values are numerically huge, so even large absolute deviations correspond to tiny relative errors. Second, the learned model improved over a simple baseline that uses only the direct formula response from the current timing ratio. The dashboard outputs both the **predicted percentage adjustment** and the resulting **predicted difficulty value** for the next retarget. For the current live cycle, that forecast is guided by the current mempool.space timing estimate used as an input feature rather than being a fully closed historical forecast. On the same snapshot date, the model predicted a next change of **+3.402125%**, while the mempool.space reference estimate was **+3.401763%**. This close agreement suggests that the chosen features capture the core dynamics of the current adjustment cycle while keeping the model simple and interpretable.

The main limitation is that the model operates on a relatively small number of completed retarget periods and is intentionally lightweight. That is acceptable for this project because the goal is not to outperform specialized forecasting systems, but to demonstrate a justified AI approach, evaluate it properly, and integrate it into the dashboard in a way that remains easy to explain.

## 3. External references

The project relies on both primary technical references and live public API documentation:

- Nakamoto, S. (2008). *Bitcoin: A Peer-to-Peer Electronic Cash System.* https://bitcoin.org/bitcoin.pdf
- Blockstream Esplora API documentation. https://github.com/Blockstream/esplora/blob/master/API.md
- mempool.space REST API documentation. https://mempool.space/docs/api/rest
- Blockchain.com Charts API documentation. https://www.blockchain.com/en/api/charts_api

The whitepaper was especially important for the interpretation of Proof of Work, block chaining, and the role of the Merkle root in the block header. The public API references were necessary to connect those concepts to live network data in the dashboard.
