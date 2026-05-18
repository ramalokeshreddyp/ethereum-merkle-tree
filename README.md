# 🔗 Ethereum Merkle Tree Verifier

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Ethereum](https://img.shields.io/badge/Ethereum-Mainnet-627EEA?style=for-the-badge&logo=ethereum&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-Passing-4CAF50?style=for-the-badge&logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**A production-grade Python implementation of a binary Merkle Tree for verifying real Ethereum transactions — built from scratch using cryptographic hashing, live JSON-RPC block fetching, and end-to-end inclusion proof verification.**

[Overview](#-overview) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [How It Works](#-how-it-works) • [Testing](#-testing) • [Extensions](#-extension-challenges)

</div>

---

## 📖 Overview

Every Ethereum block header contains a single 32-byte value — the **`transactionsRoot`** — that is a cryptographic fingerprint of every transaction in the block. This project builds the data structure that generates and verifies that fingerprint: a **binary Merkle Tree**.

| Part | Module | Description |
|------|--------|-------------|
| **Part 1** | `src/part1_tree.py` | Pure-Python `MerkleTree` class, proof generation, standalone verifier |
| **Part 2** | `src/part2_fetch.py` | Fetches real Ethereum blocks via JSON-RPC (Alchemy / Infura) |
| **Part 3** | `src/part3_verify.py` | Reconstructs transactions root, generates & verifies inclusion proofs |
| **Extensions** | `src/extensions.py` | RLP+Keccak-256, odd-leaf detection, light client simulation, historical blocks |

---

## 🏗 Architecture

### System Overview

```mermaid
graph TB
    subgraph INPUT["📥 Input Layer"]
        A[Raw Data / Transactions]
        B[Ethereum RPC Endpoint]
    end

    subgraph CORE["⚙️ Core Engine — Part 1"]
        C[sha256_leaf\nHash each item]
        D[MerkleNode\nTree node dataclass]
        E[MerkleTree._build\nRecursive pairing]
        F[Merkle Root\n32-byte fingerprint]
        G[get_proof\nSibling hash list]
        H[verify_proof\nStandalone verifier]
    end

    subgraph FETCH["🌐 Fetch Layer — Part 2"]
        I[fetch_block\neth_getBlockByNumber]
        J[inspect_block\nHeader fields printer]
    end

    subgraph VERIFY["✅ Verify Layer — Part 3"]
        K[hash_transaction\nSHA-256 of tx hash]
        L[reconstruct_transactions_root\nBuild tree over txs]
        M[prove_transaction_inclusion\nEnd-to-end proof]
    end

    subgraph EXT["🔬 Extensions"]
        N[Ext A: RLP + Keccak-256]
        O[Ext B: Odd-leaf blocks]
        P[Ext C: Light client sim]
        Q[Ext D: Historical blocks]
    end

    A --> C --> D --> E --> F
    E --> G --> H
    B --> I --> J
    I --> K --> L --> M
    F --> M
    M --> N & O & P & Q

    style INPUT fill:#1a1a2e,color:#e0e0e0,stroke:#627EEA
    style CORE fill:#16213e,color:#e0e0e0,stroke:#4CAF50
    style FETCH fill:#0f3460,color:#e0e0e0,stroke:#2196F3
    style VERIFY fill:#1a1a2e,color:#e0e0e0,stroke:#FF9800
    style EXT fill:#16213e,color:#e0e0e0,stroke:#9C27B0
```

### Merkle Tree Construction Flow

```mermaid
flowchart LR
    subgraph LEAVES["Leaf Level"]
        L0["H(alice)"]
        L1["H(bob)"]
        L2["H(carol)"]
        L3["H(dave)"]
    end

    subgraph MID["Internal Level"]
        M0["H(H_alice ∥ H_bob)"]
        M1["H(H_carol ∥ H_dave)"]
    end

    subgraph ROOT["Root"]
        R["Merkle Root\nH(H_ab ∥ H_cd)"]
    end

    L0 & L1 --> M0
    L2 & L3 --> M1
    M0 & M1 --> R

    style LEAVES fill:#0d4f3c,color:#a5d6a7,stroke:#4CAF50
    style MID fill:#1a237e,color:#bbdefb,stroke:#2196F3
    style ROOT fill:#4a1942,color:#f8bbd0,stroke:#E91E63
```

### Proof Verification Flow

```mermaid
sequenceDiagram
    participant P as Prover (Full Node)
    participant V as Verifier (Light Client)
    participant B as Block Header

    P->>P: Build MerkleTree over all txs
    P->>P: get_proof(tx_index)
    P->>V: leaf_data + proof_path + block_number
    V->>B: Read transactionsRoot
    B-->>V: 0xabc...def (32 bytes)
    V->>V: hash(leaf_data) → current_hash
    loop For each sibling in proof
        V->>V: current_hash = hash(current ∥ sibling)\nor hash(sibling ∥ current)
    end
    V->>V: computed_root == transactionsRoot?
    V-->>P: ✅ VALID or ❌ INVALID
```

### Execution Flow (main.py)

```mermaid
flowchart TD
    START([▶ python main.py]) --> ARGS{Parse CLI args}
    ARGS -->|--part 1| P1[Run Part 1\nUnit Tests]
    ARGS -->|--part 2| P2[Fetch Block\nvia RPC]
    ARGS -->|--part 3| P3[Prove Inclusion\nEnd-to-End]
    ARGS -->|all parts| ALL[Run 1 → 2 → 3\nSequentially]
    ARGS -->|--extensions| EXT[Run A/B/C/D]

    P1 --> TEST1{All assertions\npassed?}
    TEST1 -->|✅ Yes| DONE1[Print PASSED]
    TEST1 -->|❌ No| FAIL[AssertionError\nExit 1]

    P2 --> ENV{RPC_URL set?}
    ENV -->|No| ERR[Print error\nExit 1]
    ENV -->|Yes| RPC[eth_getBlockByNumber\nfull=true]
    RPC --> INSPECT[inspect_block\nPrint header fields]

    P3 --> HASH[hash_transaction\nfor each tx]
    HASH --> BUILD[MerkleTree.build\nleaf hashes]
    BUILD --> PROOF[get_proof\ntx_index]
    PROOF --> VERIFY[verify_proof\nvs. reconstructed root]
    VERIFY --> TAMPER[Tamper demo\nbreak proof → False]
    TAMPER --> DONE3[✅ End-to-End PASSED]

    ALL --> P1
    P1 --> P2
    P2 --> P3
    P3 --> EXT

    style START fill:#627EEA,color:#fff
    style DONE1 fill:#4CAF50,color:#fff
    style DONE3 fill:#4CAF50,color:#fff
    style FAIL fill:#F44336,color:#fff
    style ERR fill:#FF9800,color:#fff
```

---

## 🗂 Project Structure

```
ethereum-merkle-tree/
├── src/
│   ├── __init__.py
│   ├── part1_tree.py       # MerkleNode, MerkleTree, verify_proof()
│   ├── part2_fetch.py      # fetch_block(), inspect_block(), RPC helpers
│   ├── part3_verify.py     # hash_transaction(), prove_transaction_inclusion()
│   └── extensions.py       # Extension A (RLP+Keccak), B, C, D
├── tests/
│   ├── __init__.py
│   └── test_merkle.py      # Full pytest suite (50+ tests, 100% offline)
├── main.py                 # CLI entry point — orchestrates all parts
├── requirements.txt        # Pinned Python dependencies
├── Dockerfile              # python:3.11-slim container
├── docker-compose.yml      # Services: app + tests
├── .env.example            # Environment variable template
├── README.md
├── architecture.md
└── projectdocumentation.md
```

---

## ⚙️ Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Uses `list[type]` syntax |
| Docker + Compose | Any recent | For containerized execution |
| Ethereum RPC URL | — | Free tier from Alchemy or Infura |

---

## 🚀 Quick Start

### 1 — Clone & Configure

```bash
git clone https://github.com/ramalokeshreddyp/ethereum-merkle-tree.git
cd ethereum-merkle-tree

# Copy env template and add your RPC URL
cp .env.example .env
# Edit .env:  RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
```

### 2 — Local Setup (without Docker)

```bash
# Create virtual environment
python -m venv .venv

# Activate — Windows
.venv\Scripts\activate
# Activate — macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Part 1 only (no network required)
python main.py --part 1

# Run all parts (requires RPC_URL in .env)
python main.py

# Run a specific block and transaction index
python main.py --part 3 --block latest --tx-index 0

# Run extension challenges
python main.py --extensions a b c d
```

### 3 — Docker (recommended)

```bash
# Build image and run all parts
docker compose up --build

# Run only the test suite
docker compose run tests

# Run specific parts interactively
docker compose run app python main.py --part 1
docker compose run app python main.py --extensions a c
```

---

## 🔬 How It Works

### Step 1 — Leaf Hashing

Each raw data item (or transaction hash) is SHA-256 hashed to form a leaf:

```python
leaf_hash = hashlib.sha256(data).digest()  # 32 bytes
```

### Step 2 — Tree Construction (bottom-up)

```
Leaves:    [H(alice)   H(bob)    H(carol)   H(dave)]
                  ↘ ↙                    ↘ ↙
Level 1:   [H(H_alice‖H_bob)    H(H_carol‖H_dave)]
                         ↘         ↙
Root:              [H(H_ab ‖ H_cd)]
```

- **Odd leaves** → last leaf is **duplicated** before pairing (standard convention)
- Recursion terminates when a single root node remains

### Step 3 — Proof Generation

For leaf at index `i`, the proof is the ordered list of **sibling hashes** from leaf level up to just below the root:

```python
proof = tree.get_proof(2)
# → [{"hash": b"...", "position": "left"}, {"hash": b"...", "position": "right"}]
```

### Step 4 — Standalone Verification

No tree access needed — only the leaf data, proof, and expected root:

```python
assert verify_proof(b"carol", proof, tree.root)       # True  ✅
assert not verify_proof(b"mallory", proof, tree.root)  # False ❌
```

### Transaction Hashing (Option A — Simplified)

```python
leaf = sha256(tx["hash"].encode("utf-8"))
# sha256_leaf() then hashes again internally
```

> **Note:** Ethereum's actual `transactionsRoot` uses **RLP encoding + Keccak-256 + Merkle Patricia Trie**. Option A validates the tree logic; see Extension A for the exact approach.

---

## 🧪 Testing

```bash
# Run the full test suite (offline, no RPC needed)
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=src --cov-report=term-missing

# Run a specific test class
pytest tests/test_merkle.py::TestVerifyProof -v

# Docker
docker compose run tests
```

### Test Coverage Summary

| Test Class | What is covered |
|------------|----------------|
| `TestMerkleTreeConstruction` | Build 1/2/3/4/5/100-leaf trees, empty raises `ValueError` |
| `TestMerkleRoot` | 32-byte output, determinism, manual root verification |
| `TestProofGeneration` | Structure, ordering, `left`/`right` positions, out-of-range |
| `TestVerifyProof` | Valid → True, tampered leaf → False, tampered proof → False |
| `TestHashTransaction` | Returns 32 bytes, deterministic, handles missing fields |
| `TestReconstructTransactionsRoot` | Matches manual build, empty raises, determinism |
| `TestSha256Pair` | Order matters, 32-byte output, manual SHA-256 check |

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RPC_URL` | ✅ Parts 2 & 3 | Ethereum JSON-RPC endpoint URL |

**Free RPC Providers:**

| Provider | URL Pattern |
|----------|-------------|
| Alchemy | `https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY` |
| Infura | `https://mainnet.infura.io/v3/YOUR_PROJECT_ID` |
| Cloudflare (public) | `https://cloudflare-eth.com` |

---

## 🧩 Extension Challenges

| Extension | Description | CLI Flag |
|-----------|-------------|----------|
| **A — RLP + Keccak-256** | Accurate Ethereum leaf hashing using `rlp` + `pycryptodome` | `--extensions a` |
| **B — Odd-Leaf Detection** | Finds a block with odd tx count; proves odd-leaf duplication logic | `--extensions b` |
| **C — Light Client Sim** | Verifies inclusion using only the block header + proof (no full block) | `--extensions c` |
| **D — Historical Block** | Fetches a block from ~6 months ago; verifies a transaction in history | `--extensions d` |

```bash
# Run all four extensions
python main.py --extensions a b c d
```

---

## 📐 CLI Reference

```
usage: main.py [-h] [--part {1,2,3}] [--block BLOCK]
               [--tx-index TX_INDEX] [--extensions EXT [EXT ...]]

options:
  -h, --help              show this help message and exit
  --part {1,2,3}          Run only one part (default: all)
  --block BLOCK           Block number or 'latest' (default: latest)
  --tx-index TX_INDEX     Transaction index for proof (default: 0)
  --extensions a b c d    Extension challenges to run
```

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `requests` | 2.32.3 | JSON-RPC HTTP calls to Ethereum node |
| `python-dotenv` | 1.0.1 | Load `.env` configuration |
| `rlp` | 4.0.1 | RLP encoding (Extension A) |
| `pycryptodome` | 3.21.0 | Keccak-256 hash (Extension A, Windows-compatible) |
| `pytest` | 8.3.5 | Test runner |
| `pytest-cov` | 5.0.0 | Test coverage reporting |

---

## 🔑 Key Concepts

| Concept | Explanation |
|---------|-------------|
| **Leaf node** | `sha256(raw_data)` — bottom of the tree |
| **Internal node** | `sha256(left_hash ‖ right_hash)` |
| **Merkle root** | Single 32-byte cryptographic fingerprint |
| **Merkle proof** | ~log₂(n) sibling hashes — logarithmic space |
| **transactionsRoot** | Ethereum block header field committing all transactions |
| **RLP** | Recursive Length Prefix — Ethereum's binary serialisation format |
| **Keccak-256** | Ethereum's hash function (≠ SHA3-256 / SHA-256) |
| **MPT** | Merkle Patricia Trie — Ethereum's actual trie structure |

---

## 🔒 Security Notes

- **No private keys, wallets, or signing** — all operations are read-only
- **No gas spent** — only `eth_getBlockByNumber` / `eth_getTransactionByHash` RPC calls
- `.env` is `.gitignore`d — never commit your API key
- RLP + Keccak hashing done with `pycryptodome` (not `pysha3`) for Windows compatibility

---

## 🧠 Key Takeaway

> The `transactionsRoot` in every Ethereum block header is a **cryptographic commitment** — a single 32-byte value that locks in every transaction in the block. Change any transaction and the root changes. Forge a root and the block's proof-of-stake signature becomes invalid.
>
> Your Merkle tree implementation is the **same data structure — conceptually — that secures billions of dollars of on-chain value.** The difference between your implementation and Ethereum's is encoding details and trie structure, not the underlying idea.

---

## 📄 License

MIT © 2025
