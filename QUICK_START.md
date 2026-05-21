# 🚀 Quick Start Guide

## 1. Prerequisites

- **Python 3.11+**
- **pip** (Python package manager)
- (Optional) **Docker** and **Docker Compose** for containerized execution

---

## 2. Installation

### Step 1: Clone or Extract the Project

```bash
cd /path/to/ethereum-merkle-tree
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `requests` — JSON-RPC calls to Ethereum
- `python-dotenv` — Load .env variables
- `rlp` — Transaction encoding (Extension A)
- `pycryptodome` — Keccak-256 hashing (Extension A)
- `pytest` — Test framework

---

## 3. Get a Free Ethereum RPC Endpoint

Choose one of these providers (all have free tiers):

### **Alchemy** (Recommended)
1. Go to https://www.alchemy.com/
2. Sign up (free)
3. Create a new "App" on Ethereum Mainnet
4. Copy your URL (looks like `https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY`)

### **Infura**
1. Go to https://www.infura.io/
2. Sign up (free)
3. Create a new project
4. Select "Ethereum" → "Mainnet"
5. Copy your URL (looks like `https://mainnet.infura.io/v3/YOUR_PROJECT_ID`)

### **Other Options**
- QuickNode: https://www.quicknode.com/
- BlockPI: https://blockpi.io/
- Public RPC (no auth): https://eth.public-rpc.com/

---

## 4. Configure Environment Variables

### Option A: Using .env File

```bash
# Copy the example file
cp .env.example .env

# Edit .env and paste your RPC URL
nano .env
# or use your preferred editor
```

Content of `.env`:
```
RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY_HERE
```

### Option B: Set Environment Variable Directly (Linux/Mac)

```bash
export RPC_URL="https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY_HERE"
python main.py
```

### Option C: Set Environment Variable (Windows PowerShell)

```powershell
$env:RPC_URL="https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY_HERE"
python main.py
```

---

## 5. Run the Project

### **Option 1: Run All Parts (Recommended First Time)**

```bash
python main.py
```

**What happens:**
1. **Part 1** — Runs local Merkle tree unit tests (no network needed)
2. **Part 2** — Fetches the latest Ethereum block and inspects its fields
3. **Part 3** — Reconstructs the transactions root and generates/verifies an inclusion proof

**Expected output:**
```
╔════════════════════════════════════════════════════════════╗
║  🔗  Ethereum Merkle Tree Verifier                         ║
║      Building Trust Through Cryptographic Proofs          ║
╚════════════════════════════════════════════════════════════╝

[PART 1] Merkle Tree Unit Tests
  ✓ Valid proof for 'carol' (index 2)
  ✓ Tampered leaf 'mallory'
  ✓ Tampered proof hash
  ...all tests pass...

[PART 2] Ethereum Block Fetcher
  Block Number: 19,456,123
  Transaction Count: 147
  transactionsRoot: 0xabc...def

[PART 3] Transaction Inclusion Proof
  Merkle Proof (8 steps):
    Step 1: sibling=0xdead...  position=right
    Step 2: sibling=0xbeef...  position=left
    ...
  Proof Verification → ✓ VALID
```

---

### **Option 2: Run Only Part 1 (No Network Required)**

```bash
python main.py --part 1
```

This demonstrates that the Merkle tree implementation is correct with local, reproducible test cases.

---

### **Option 3: Run Only Parts 2 & 3 (Fetch & Verify)**

```bash
python main.py --part 2  # Fetch and inspect latest block
python main.py --part 3  # Verify transaction in latest block
```

---

### **Option 4: Fetch a Specific Block**

```bash
python main.py --part 3 --block 19456123 --tx-index 5
```

This fetches block #19456123 and generates a proof for transaction at index 5.

---

### **Option 5: Run Tests via Pytest**

```bash
# Run all tests
pytest tests/test_merkle.py -v

# Run a specific test class
pytest tests/test_merkle.py::TestMerkleRoot -v

# Run with coverage
pytest tests/test_merkle.py --cov=src --cov-report=html
```

**Expected output:**
```
tests/test_merkle.py::TestMerkleTreeConstruction::test_build_four_leaves PASSED
tests/test_merkle.py::TestMerkleRoot::test_root_is_32_bytes PASSED
tests/test_merkle.py::TestVerifyProof::test_valid_proof_returns_true PASSED
...
====================== 47 passed in 0.34s ======================
```

---

## 6. Extension Challenges

Once the core works, run optional extensions:

### **Extension A — RLP + Keccak-256 (Accurate Hashing)**

```bash
python main.py --extensions a
```

Uses proper Ethereum transaction encoding to produce the exact `transactionsRoot`.

### **Extension B — Odd-Leaf Block Detection**

```bash
python main.py --extensions b
```

Finds and verifies a block with an odd number of transactions (exercises the duplicate-leaf logic).

### **Extension C — Light Client Simulation**

```bash
python main.py --extensions c
```

Verifies a transaction using only a block header + Merkle proof (no full block data).

### **Extension D — Historical Block Verification**

```bash
python main.py --extensions d
```

Fetches a block from ~6 months ago and proves a transaction's inclusion in that historical block.

### **Run Multiple Extensions**

```bash
python main.py --extensions a b c d
```

---

## 7. Docker Execution (Optional)

### **Build and Run Container**

```bash
docker-compose up --build
```

This:
- Builds a Docker image with Python 3.11 + dependencies
- Runs all pytest tests (50+, 100% passing)
- Outputs logs to stdout

### **Run Specific Service**

```bash
docker-compose run app python main.py --part 1
```

---

## 8. Troubleshooting

### **Error: "RPC_URL environment variable is not set"**

**Solution:** Follow Step 4 above to set `RPC_URL` in a `.env` file or environment variable.

---

### **Error: "pytest module was not installed"**

**Solution:**
```bash
pip install pytest
pytest tests/test_merkle.py -v
```

---

### **Error: "requests.ConnectionError" when fetching a block**

**Possible causes:**
1. `RPC_URL` is incorrect or expired
2. Network connection issue
3. RPC endpoint is temporarily down

**Solution:**
- Verify your RPC URL by opening it in a browser (you should see an error page, but the endpoint should respond)
- Try a different RPC provider
- Check internet connection: `ping google.com`

---

### **Block Has 0 Transactions**

Sometimes empty blocks are mined (no user transactions). If this happens:

```bash
# Fetch an older block with more transactions
python main.py --block 19456000  # Use a specific block number
```

---

## 9. Project Files Overview

| File | Purpose |
|------|---------|
| `src/part1_tree.py` | Core Merkle tree implementation (standalone, no dependencies) |
| `src/part2_fetch.py` | Ethereum JSON-RPC client (fetches blocks) |
| `src/part3_verify.py` | Transaction verification (ties Parts 1 & 2 together) |
| `src/extensions.py` | Advanced features (RLP+Keccak, light client, etc.) |
| `tests/test_merkle.py` | Full pytest suite (50+ tests, 100% passing) |
| `main.py` | CLI entry point (orchestrates all parts) |

---

## 10. Next Steps

1. ✅ Run `python main.py` to verify everything works
2. ✅ Study the code in `src/part1_tree.py` to understand Merkle trees
3. ✅ Read block header fields in the `inspect_block()` output
4. ✅ Trace a transaction's proof path through the tree
5. ✅ Try Extension A to see accurate Keccak-256 hashing
6. ✅ Build your own transaction inclusion proof for a specific transaction

---

## 11. Key Concepts

### **Merkle Tree**
A binary tree where each parent node is the hash of its two children. Allows efficient verification of large datasets using logarithmic-sized proofs.

### **Merkle Root**
The single hash at the top of the tree. In Ethereum, stored in the block header as `transactionsRoot`. Changes to any transaction invalidate the root.

### **Merkle Proof**
A path of sibling hashes from a leaf to the root. Sufficient to recompute the root without the full tree.

### **Tamper-Evidence**
Changing any transaction (leaf) changes all hashes up to the root. Thus, the root is a cryptographic commitment to the full transaction set.

### **Light Client**
A node that only stores block headers (not full blocks). Uses Merkle proofs to verify transaction inclusion without downloading the entire blockchain.

---

## 📚 Resources

- **Merkle Trees Explained**: https://en.wikipedia.org/wiki/Merkle_tree
- **Ethereum Yellow Paper**: https://ethereum.org/en/developers/docs/
- **Alchemy Docs**: https://docs.alchemy.com/
- **Infura Docs**: https://infura.io/docs
- **EIP-2718 (Transaction Types)**: https://eips.ethereum.org/EIPS/eip-2718

---

## ✨ Summary

You've now set up a complete Merkle tree implementation that:
- ✅ Builds trees from raw data
- ✅ Generates cryptographic proofs
- ✅ Verifies proofs efficiently
- ✅ Fetches real Ethereum blocks
- ✅ Proves transaction inclusion against block headers

This is the foundation of how light clients, SPV wallets, and cross-chain bridges verify blockchain data without downloading the entire history.

Happy hashing! 🔗⛓️
