# Ethereum Merkle Tree Verifier 🔗

A production-ready Python implementation of a **binary Merkle Tree** used to verify Ethereum transactions — built from scratch with cryptographic proof generation, live block fetching via JSON-RPC, and end-to-end inclusion proof verification.

---

## 📖 Overview

| Part | What it does |
|------|-------------|
| **Part 1** | Pure-Python `MerkleTree` class, proof generation, standalone verifier |
| **Part 2** | Fetches real Ethereum blocks via JSON-RPC (Alchemy / Infura) |
| **Part 3** | Reconstructs the transactions root, generates & verifies inclusion proofs |
| **Extensions** | RLP+Keccak256 hashing, odd-leaf detection, light client simulation, historical blocks |

---

## 🗂 Project Structure

```
ethereum-merkle-tree/
├── src/
│   ├── __init__.py
│   ├── part1_tree.py      # MerkleTree, get_proof(), verify_proof()
│   ├── part2_fetch.py     # fetch_block(), inspect_block()
│   ├── part3_verify.py    # hash_transaction(), prove_transaction_inclusion()
│   └── extensions.py      # Extension A–D
├── tests/
│   ├── __init__.py
│   └── test_merkle.py     # Full pytest suite (50+ tests)
├── main.py                # End-to-end runner (CLI)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## ⚙️ Prerequisites

- Python **3.11+**
- A free Ethereum RPC endpoint from [Alchemy](https://www.alchemy.com/) or [Infura](https://infura.io/)
- Docker & Docker Compose (for containerized execution)

---

## 🚀 Quick Start

### 1 — Clone & configure

```bash
git clone https://github.com/ramalokeshreddyp/ethereum-merkle-tree.git
cd ethereum-merkle-tree

# Copy the env template and add your RPC URL
cp .env.example .env
# Edit .env and set:  RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
```

### 2 — Local setup (without Docker)

```bash
# Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Part 1 only (no network required)
python main.py --part 1

# Run all parts (requires RPC_URL)
python main.py

# Run specific parts
python main.py --part 2
python main.py --part 3 --block latest --tx-index 0

# Run extension challenges
python main.py --extensions a b c d
```

### 3 — Docker (recommended for submission)

```bash
# Build and run all parts
docker compose up --build

# Run only the test suite
docker compose run tests

# Run a specific part
docker compose run app python main.py --part 1
docker compose run app python main.py --extensions a c
```

---

## 🧪 Running Tests

```bash
# Local
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=src --cov-report=term-missing

# Docker
docker compose run tests
```

All tests are offline — no RPC connection required.

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RPC_URL` | ✅ Yes (Parts 2, 3) | Ethereum JSON-RPC endpoint URL |

**Free RPC options:**

| Provider | URL Pattern |
|----------|-------------|
| Alchemy  | `https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY` |
| Infura   | `https://mainnet.infura.io/v3/YOUR_KEY` |
| Cloudflare (public) | `https://cloudflare-eth.com` |

---

## 🏗 How It Works

### Merkle Tree Construction

```
Leaves:   [sha256("alice"), sha256("bob"), sha256("carol"), sha256("dave")]

Level 1:  [sha256(H_a + H_b),              sha256(H_c + H_d)             ]

Root:     [sha256(H_ab + H_cd)]
```

- Odd number of leaves → last leaf is **duplicated** before pairing
- Proof = list of sibling hashes from leaf level to just below root

### Transaction Hashing (Option A — simplified)

```python
leaf = sha256(sha256(tx["hash"].encode("utf-8")))
```

> **Note:** This will NOT match Ethereum's actual `transactionsRoot` (which uses RLP encoding + Keccak-256 + a Merkle Patricia Trie). Use Extension A for the exact approach.

### Inclusion Proof Verification

```
Prover:   sends {leaf_data, [sibling_1, sibling_2, …], expected_root}
Verifier: recomputes root from leaf_data + siblings
          checks computed_root == expected_root  → True/False
```

No access to the full tree needed — logarithmic space.

---

## 🧩 Extension Challenges

| Extension | Description | Command |
|-----------|-------------|---------|
| **A** | RLP encoding + Keccak-256 (accurate Ethereum hashing) | `--extensions a` |
| **B** | Finds a block with odd tx count; verifies odd-leaf duplication | `--extensions b` |
| **C** | Light client simulation — verifies using only block header + proof | `--extensions c` |
| **D** | Fetches a block from ~6 months ago; verifies historical transaction | `--extensions d` |

```bash
# Run all extensions
python main.py --extensions a b c d
```

---

## 📐 CLI Reference

```
usage: main.py [-h] [--part {1,2,3}] [--block BLOCK] [--tx-index TX_INDEX]
               [--extensions EXT [EXT ...]]

options:
  --part {1,2,3}          Run only one part (default: all)
  --block BLOCK           Block number or 'latest' (default: latest)
  --tx-index TX_INDEX     Transaction index for proof (default: 0)
  --extensions a b c d   Extension challenges to run
```

---

## 🔍 Key Concepts

| Concept | Explanation |
|---------|-------------|
| **Leaf node** | `sha256(sha256(raw_data))` — double hash prevents length-extension attacks |
| **Internal node** | `sha256(left_hash + right_hash)` |
| **Merkle root** | Single 32-byte fingerprint of the entire dataset |
| **Merkle proof** | ~log₂(n) sibling hashes — sufficient to recompute root |
| **transactionsRoot** | Field in every Ethereum block header committing all transactions |
| **RLP** | Recursive Length Prefix — Ethereum's binary serialisation format |
| **Keccak-256** | Ethereum's hash function (≠ SHA3-256) |

---

## 🔒 Security Notes

- **No private keys, wallets, or signing** — all operations are read-only
- **No gas spent** — only `eth_getBlockByNumber` / `eth_getTransactionByHash` calls
- `.env` is gitignored — never commit your API key

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `requests` | 2.32.3 | JSON-RPC HTTP calls |
| `python-dotenv` | 1.0.1 | Load `.env` config |
| `rlp` | 4.0.1 | RLP encoding (Extension A) |
| `pysha3` → `pycryptodome` | 3.21.0 | Keccak-256 (Extension A, Windows-compatible) |
| `pytest` | 8.3.5 | Test runner |
| `pytest-cov` | 5.0.0 | Coverage reporting |

---

## 🧠 Key Takeaway

> The `transactionsRoot` in every Ethereum block header is a **cryptographic commitment** — a single 32-byte value that locks in every transaction. Change any transaction, and the root changes. Your Merkle tree implementation is the same data structure — conceptually — that secures billions of dollars of on-chain value.

---

## 📄 License

MIT
