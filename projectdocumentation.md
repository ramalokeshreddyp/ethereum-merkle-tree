# Project Documentation — Ethereum Merkle Tree Verifier

## Table of Contents

1. [Project Objective](#1-project-objective)
2. [Background & Context](#2-background--context)
3. [Technical Requirements](#3-technical-requirements)
4. [Module-by-Module Reference](#4-module-by-module-reference)
5. [Algorithm Deep Dive](#5-algorithm-deep-dive)
6. [API Reference](#6-api-reference)
7. [Testing Strategy](#7-testing-strategy)
8. [Containerization](#8-containerization)
9. [Extension Challenges](#9-extension-challenges)
10. [Troubleshooting](#10-troubleshooting)
11. [Advantages, Limitations & Trade-offs](#11-advantages-limitations--trade-offs)

---

## 1. Project Objective

Build a **binary Merkle Tree** from scratch in Python and use it to verify a real Ethereum transaction. The project demonstrates:

- Cryptographic hashing with SHA-256 and Keccak-256
- Tree-based data structures for integrity verification
- Merkle proof generation and standalone verification
- Integration with Ethereum's JSON-RPC API
- Containerized deployment with Docker

The end goal: given a block fetched from the Ethereum Mainnet, generate a cryptographic proof that a specific transaction is included in that block, and verify the proof without accessing the full block.

---

## 2. Background & Context

### What is a Merkle Tree?

A Merkle tree is a binary tree where:
- Every **leaf node** contains the hash of a data item
- Every **internal node** contains the hash of its two children concatenated
- The single top value — the **Merkle root** — is a cryptographic fingerprint of the entire dataset

**Two critical properties:**

| Property | Description |
|----------|-------------|
| **Tamper evidence** | Changing any leaf changes its hash, which propagates up and invalidates the root |
| **Efficient proofs** | Membership can be proved with only log₂(n) hashes — not the entire dataset |

### Why Ethereum Needs It

Every Ethereum block header contains a `transactionsRoot` — a Merkle root computed over all transactions in the block. This enables:

- **Light clients** to verify transaction inclusion without downloading the full blockchain
- **Cross-chain bridges** to prove events happened on the source chain
- **Block integrity** — validators cannot claim a transaction is included without it actually being there

### Ethereum vs. This Project

Ethereum uses a **Merkle Patricia Trie** (MPT), not a plain binary tree. The key differences:

| Aspect | This Project | Ethereum Mainnet |
|--------|-------------|-----------------|
| Tree type | Plain binary Merkle tree | Merkle Patricia Trie |
| Leaf hash | SHA-256 of tx hash string | Keccak-256 of RLP-encoded tx |
| Node indexing | Positional (0, 1, 2…) | Key-value (RLP-encoded index) |
| Root match | ❌ (different structure) | ✅ (Extension A gets closer) |
| Core concept | ✅ Identical | ✅ Identical |

---

## 3. Technical Requirements

### Core Requirements Fulfilled

| # | Requirement | Status | Implementation |
|---|-------------|--------|----------------|
| 1 | `MerkleTree` class with odd-leaf handling | ✅ | `part1_tree.py: MerkleTree.__init__` |
| 2 | `.root` property returning 32-byte hash | ✅ | `part1_tree.py: MerkleTree.root` |
| 3 | `get_proof(index)` → list of `{hash, position}` dicts | ✅ | `part1_tree.py: MerkleTree.get_proof` |
| 4 | Standalone `verify_proof(leaf, proof, root)` | ✅ | `part1_tree.py: verify_proof` |
| 5 | Local tests: valid / tampered leaf / tampered proof | ✅ | `tests/test_merkle.py` |
| 6 | `fetch_block(rpc_url, block_number)` | ✅ | `part2_fetch.py: fetch_block` |
| 7 | `inspect_block(block)` printing number + transactionsRoot | ✅ | `part2_fetch.py: inspect_block` |
| 8 | `hash_transaction(tx)` — SHA-256 simplified | ✅ | `part3_verify.py: hash_transaction` |
| 9 | `reconstruct_transactions_root(transactions)` | ✅ | `part3_verify.py: reconstruct_transactions_root` |
| 10 | End-to-end runnable main script | ✅ | `main.py` |

### Tech Stack

| Tool | Version | Purpose | Why Chosen |
|------|---------|---------|------------|
| Python | 3.11+ | Implementation language | Modern type hints, stdlib `hashlib` |
| `hashlib` | stdlib | SHA-256 hashing | No external dep, FIPS-compliant |
| `requests` | 2.32.3 | JSON-RPC HTTP calls | Mature, simple API |
| `python-dotenv` | 1.0.1 | `.env` config loading | 12-factor app pattern |
| `rlp` | 4.0.1 | RLP encoding (Extension A) | Ethereum-standard library |
| `pycryptodome` | 3.21.0 | Keccak-256 (Extension A) | Windows-compatible, replaces `pysha3` |
| `pytest` | 8.3.5 | Test runner | Standard Python testing tool |
| `pytest-cov` | 5.0.0 | Coverage reporting | Identifies untested paths |
| Docker | Any | Containerization | Reproducible, submission-ready |

---

## 4. Module-by-Module Reference

### 4.1 `src/part1_tree.py`

**Purpose:** Core cryptographic data structure. Zero external dependencies.

#### `sha256_pair(left: bytes, right: bytes) → bytes`
Concatenates `left + right` and returns the SHA-256 digest. Used for all internal node hashing.

```python
sha256_pair(b"\xaa" * 32, b"\xbb" * 32)  # → 32-byte digest
```

#### `sha256_leaf(data: bytes) → bytes`
SHA-256 hash of a raw data item. Applied to each leaf during `MerkleTree.__init__`.

#### `MerkleNode`
Dataclass with three fields: `hash: bytes`, `left: MerkleNode | None`, `right: MerkleNode | None`.

#### `MerkleTree.__init__(leaves: list[bytes])`
1. Hashes each item with `sha256_leaf` → builds `_leaf_hashes`
2. Creates `MerkleNode` objects for each leaf
3. Calls `_build()` to recursively construct the tree, storing the root
4. Calls `_populate_levels()` to store all levels for proof generation

#### `MerkleTree._build(nodes: list[MerkleNode]) → MerkleNode`
Recursive function:
- Base case: `len(nodes) == 1` → return the single node (root)
- If odd count: append duplicate of last node
- Pair up nodes, create parent with `sha256_pair(left.hash, right.hash)`
- Recurse on parent level

#### `MerkleTree.get_proof(index: int) → list[dict]`
For each level (leaf to root):
1. Determine if `current_index` is even (left child) or odd (right child)
2. Append sibling hash and position to proof
3. `current_index //= 2` to move up one level

Returns `[{"hash": bytes, "position": "left"|"right"}, ...]`

#### `verify_proof(leaf_data, proof, expected_root) → bool`
1. Start: `current_hash = sha256_leaf(leaf_data)`
2. For each step: combine with sibling in correct order
3. Return `current_hash == expected_root`

---

### 4.2 `src/part2_fetch.py`

**Purpose:** Ethereum JSON-RPC client. Fetches blocks and inspects headers.

#### `_rpc_call(rpc_url, method, params) → Any`
Internal helper. Sends a JSON-RPC 2.0 POST request, raises on HTTP or RPC errors, returns `result`.

#### `fetch_block(rpc_url, block_number) → dict`
Calls `eth_getBlockByNumber` with `full=True` to include complete transaction objects (not just hashes). Converts integer block numbers to hex strings per the JSON-RPC spec.

#### `inspect_block(block) → None`
Prints: block number (decimal + hex), Unix timestamp, miner/validator, tx count, gas used/limit, `transactionsRoot`, and first 5 tx hashes.

#### `fetch_transaction_by_hash(rpc_url, tx_hash) → dict`
Calls `eth_getTransactionByHash`. Returns full transaction dict.

#### `fetch_transaction_proof(rpc_url, tx_hash) → dict | None`
Calls `eth_getTransactionReceipt`. Note: `eth_getProof` is for account/storage proofs, not transaction trie proofs. Receipt confirms inclusion status.

---

### 4.3 `src/part3_verify.py`

**Purpose:** Bridges Part 1 and Part 2. Hashes, reconstructs, proves.

#### `hash_transaction(tx: dict) → bytes`
**Option A (simplified):** `sha256(tx["hash"].encode("utf-8"))` — consistent and deterministic, but will NOT produce Ethereum's actual leaf hash (which requires RLP + Keccak-256).

#### `reconstruct_transactions_root(transactions: list[dict]) → bytes`
1. Applies `hash_transaction()` to each tx → `leaf_hashes`
2. Passes `leaf_hashes` to `MerkleTree(leaf_hashes)`
3. Returns `tree.root` — the reconstructed Merkle root

**Note:** `MerkleTree` will `sha256_leaf()` the already-hashed bytes again. This double-hashing is intentional for the Option A path.

#### `verify_transactions_root(block: dict) → bool`
Calls `reconstruct_transactions_root`, compares to `block["transactionsRoot"]`. With Option A, they will NOT match (different hash function + trie structure). Both values are printed for comparison.

#### `prove_transaction_inclusion(block, tx_index) → None`
Full end-to-end proof:
1. Build `MerkleTree` over all tx hashes
2. `get_proof(tx_index)` → proof path
3. `verify_proof(leaf_data, proof, tree.root)` → assert True
4. Print proof path (truncated hashes)
5. Tamper demo: mutate sibling hash → assert False
6. Wrong leaf demo: use different tx's hash → assert False

---

### 4.4 `src/extensions.py`

#### Extension A — RLP + Keccak-256

**`keccak256(data: bytes) → bytes`**
Uses `pycryptodome.Crypto.Hash.keccak` for Windows-compatible Keccak-256.

**`rlp_encode_transaction(tx: dict) → bytes`**
Handles transaction types 0 (legacy), 1 (EIP-2930), and 2 (EIP-1559):
- Type 0: `rlp.encode([nonce, gasPrice, gas, to, value, data, v, r, s])`
- Type 1: `b"\x01" + rlp.encode([chainId, nonce, gasPrice, gas, to, value, data, accessList, v, r, s])`
- Type 2: `b"\x02" + rlp.encode([chainId, nonce, maxPriorityFee, maxFee, gas, to, value, data, accessList, v, r, s])`

**`hash_transaction_keccak(tx) → bytes`**
`keccak256(rlp_encode_transaction(tx))` — the actual leaf hash Ethereum computes.

#### Extension B — Odd Leaf Detection
Searches backwards from the latest block to find one with an odd transaction count. Proves the `last leaf duplication` logic is exercised.

#### Extension C — Light Client Simulation
`light_client_verify(block_header, tx_index, proof, leaf_data)`:
- Accepts only the block header (no full transaction list)
- Extracts `transactionsRoot` from the header
- Calls `verify_proof(leaf_data, proof, header_root_bytes)`
- Simulates what a light client actually does

#### Extension D — Historical Block Verification
Computes `latest_block_number - 1_296_000` (~6 months at 12s/block) and fetches that block. Runs `prove_transaction_inclusion` on it. Demonstrates that the Merkle root committed at that time cannot have been changed retroactively.

---

## 5. Algorithm Deep Dive

### 5.1 Tree Construction — Step by Step

```
Input:  [b"alice", b"bob", b"carol", b"dave"]

Step 1 — Hash leaves:
  H_a = sha256("alice") = 2bd806c9...
  H_b = sha256("bob")   = cd9fb1e1...
  H_c = sha256("carol") = 938db08e...
  H_d = sha256("dave")  = 5c1dab04...

Step 2 — Build internal level 1 (even count → no duplication):
  H_ab = sha256(H_a ‖ H_b)
  H_cd = sha256(H_c ‖ H_d)

Step 3 — Build root (2 nodes → no duplication):
  Root = sha256(H_ab ‖ H_cd)
```

### 5.2 Odd-Leaf Handling

```
Input: [b"tx1", b"tx2", b"tx3"]

Leaf level: [H1, H2, H3]
            └─ odd → pad → [H1, H2, H3, H3]

Level 1: [sha256(H1‖H2), sha256(H3‖H3)]
         └─ even → no pad

Root: sha256(H12 ‖ H33)
```

The duplication happens at each odd level independently, not just once at the bottom.

### 5.3 Proof Generation — Index 2 in a 4-leaf Tree

```
Levels:
  [0] leaves:  [H_a,  H_b,  H_c,  H_d]      ← tx at index 2 = H_c
  [1] internal: [H_ab,       H_cd      ]
  [2] root:    [Root                   ]

Proof for index 2:
  Level 0: index=2 is even → sibling is index 3 (right)
           proof[0] = {"hash": H_d, "position": "right"}
           current_index = 2 // 2 = 1

  Level 1: index=1 is odd → sibling is index 0 (left)
           proof[1] = {"hash": H_ab, "position": "left"}
           current_index = 1 // 2 = 0  → reached root, stop

Result: [{"hash": H_d, "position": "right"}, {"hash": H_ab, "position": "left"}]
```

### 5.4 Proof Verification — Recomputing Root

```
leaf_data = b"carol"
current = sha256("carol") = H_c

Step 1: position="right" → current = sha256(H_c ‖ H_d) = H_cd
Step 2: position="left"  → current = sha256(H_ab ‖ H_cd) = Root

Root == expected_root?  → True ✅
```

---

## 6. API Reference

### JSON-RPC Methods Used

| Method | Params | Returns | Usage |
|--------|--------|---------|-------|
| `eth_getBlockByNumber` | `[blockTag, fullTxs]` | Block object | Fetch full block with transactions |
| `eth_getTransactionByHash` | `[txHash]` | Transaction object | Single tx lookup |
| `eth_getTransactionReceipt` | `[txHash]` | Receipt object | Confirm inclusion |

### Block Object Fields Used

| Field | Type | Description |
|-------|------|-------------|
| `number` | hex string | Block number |
| `timestamp` | hex string | Unix timestamp |
| `transactionsRoot` | hex string | 32-byte Merkle root of transactions |
| `transactions` | list[dict] | Full transaction objects (when `fullTxs=true`) |
| `miner` / `feeRecipient` | hex string | Block producer address |
| `gasUsed` / `gasLimit` | hex string | Gas accounting |

### Transaction Object Fields Used

| Field | Type | Used By |
|-------|------|---------|
| `hash` | hex string | `hash_transaction()` Option A |
| `type` | hex string | `rlp_encode_transaction()` Extension A |
| `nonce` | hex string | Extension A RLP encoding |
| `gasPrice` / `maxFeePerGas` | hex string | Extension A RLP encoding |
| `gas` | hex string | Extension A RLP encoding |
| `to` | hex string | Extension A RLP encoding |
| `value` | hex string | Extension A RLP encoding |
| `input` | hex string | Extension A RLP encoding |
| `v`, `r`, `s` | hex string | Extension A RLP encoding |

---

## 7. Testing Strategy

### Test Suite Structure

```
tests/
└── test_merkle.py
    ├── TestMerkleTreeConstruction   # 7 tests
    ├── TestMerkleRoot               # 7 tests
    ├── TestProofGeneration          # 11 tests
    ├── TestVerifyProof              # 8 tests
    ├── TestHashTransaction          # 5 tests
    ├── TestReconstructTransactionsRoot  # 6 tests
    └── TestSha256Pair               # 3 tests
```

**Total: 47 test cases. All 100% offline — no RPC connection required.**

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| Construction | 7 | Valid trees, empty → ValueError |
| Root correctness | 7 | 32-byte output, manual computation, determinism |
| Proof structure | 11 | Dict keys, position values, ordering, edge cases |
| Proof verification | 8 | Valid → True, all tamper variants → False |
| Transaction hashing | 5 | Return type, determinism, missing fields |
| Root reconstruction | 6 | Matches manual build, empty → ValueError |
| Hash helper | 3 | Order matters, manual SHA-256 check |

### Key Test Cases

```python
# Tampered leaf returns False
assert verify_proof(b"mallory", proof, tree.root) is False

# Tampered proof hash returns False
tampered_proof[0] = {**proof[0], "hash": b"\x00" * 32}
assert verify_proof(b"carol", tampered_proof, tree.root) is False

# Manual root computation matches tree
h_a, h_b = sha256_leaf(b"alice"), sha256_leaf(b"bob")
h_c, h_d = sha256_leaf(b"carol"), sha256_leaf(b"dave")
expected = sha256_pair(sha256_pair(h_a, h_b), sha256_pair(h_c, h_d))
assert MerkleTree([b"alice", b"bob", b"carol", b"dave"]).root == expected
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific class
pytest tests/test_merkle.py::TestVerifyProof -v

# With coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Docker
docker compose run tests
```

---

## 8. Containerization

### Dockerfile Design

```dockerfile
FROM python:3.11-slim           # Minimal base image

RUN apt-get install gcc ...     # Build deps for pycryptodome C extension

COPY requirements.txt .         # Separate layer — cached until deps change
RUN pip install --no-cache-dir -r requirements.txt

COPY . .                        # Source code last (most frequently changed)

CMD ["python", "main.py"]       # Default: run all parts
```

### Docker Compose Services

| Service | Image | Command | Purpose |
|---------|-------|---------|---------|
| `app` | `ethereum-merkle-tree:latest` | `python main.py` | Run full pipeline |
| `tests` | `ethereum-merkle-tree:latest` | `pytest tests/ -v` | Run test suite |

Both services share the same built image and load `.env` for the `RPC_URL`.

### Common Docker Commands

```bash
# Build and run full pipeline
docker compose up --build

# Run tests only
docker compose run tests

# Run Part 1 (no RPC needed)
docker compose run app python main.py --part 1

# Run all extensions
docker compose run app python main.py --extensions a b c d

# Interactive shell
docker compose run app bash
```

---

## 9. Extension Challenges

### Extension A — RLP + Keccak-256

**Goal:** Switch from SHA-256 to proper RLP encoding + Keccak-256, making leaf hashing match what Ethereum actually computes.

**Key functions:**
- `keccak256(data)` — uses `pycryptodome` instead of `pysha3` (Windows-compatible)
- `rlp_encode_transaction(tx)` — handles Type 0, 1, 2 transactions with correct field ordering
- `hash_transaction_keccak(tx)` — `keccak256(rlp_encode_transaction(tx))`

**Important limitation:** Even with correct Keccak-256 leaf hashes, a plain binary Merkle tree will NOT match Ethereum's `transactionsRoot` because Ethereum uses a Merkle Patricia Trie (not a binary tree). The leaf hashes will be correct; the tree structure differs.

### Extension B — Odd-Leaf Block Detection

Searches backwards from the latest block (up to 100 blocks) to find one with an odd number of transactions. Then proves the last transaction in that block — exercising the odd-leaf duplication code path.

```
Block #21,234,567: 143 transactions (odd)
Last tx (index 142) proof verified ✅
Odd-leaf duplication logic confirmed ✅
```

### Extension C — Light Client Simulation

Demonstrates the core value of Merkle proofs: a light client can verify transaction inclusion using **only**:
1. The block header (specifically `transactionsRoot`)
2. The Merkle proof (list of sibling hashes)
3. The transaction being verified

No full block download required. This is how MetaMask, mobile wallets, and cross-chain bridges verify transactions.

```python
# Light client has ONLY the header — no transactions list
header_only = {k: v for k, v in block.items() if k != "transactions"}
result = light_client_verify(header_only, tx_index, proof, leaf_data)
# → True ✅ — verified with no full block access
```

### Extension D — Historical Block Verification

Fetches a block from approximately 6 months ago (calculated as `latest - 1,296,000` blocks at ~12 seconds/block). Demonstrates that the `transactionsRoot` committed in that block header is immutable — the Merkle root is a cryptographic commitment to history.

---

## 10. Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `EnvironmentError: No RPC URL` | Missing `.env` file | `cp .env.example .env` and add your key |
| `ValueError: Block not found` | Wrong block number | Use `"latest"` or a valid recent block number |
| `ImportError: pycryptodome` | Extension A not installed | `pip install pycryptodome` or check `requirements.txt` |
| `UnicodeEncodeError` on Windows | Terminal encoding | `main.py` wraps stdout with UTF-8 encoding automatically |
| Roots don't match (Part 3) | Expected behaviour (Option A) | Plain SHA-256 ≠ Ethereum's Keccak-256 + MPT. See Extension A |
| Rate limit error from RPC | Too many requests | Switch providers or add retry logic |

### Verifying Your RPC URL

```bash
curl -X POST YOUR_RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
# Should return: {"result": "0x..."}
```

### Running Only Part 1 (No Network Required)

```bash
python main.py --part 1
# OR
pytest tests/ -v
```

---

## 11. Advantages, Limitations & Trade-offs

### Advantages

| Advantage | Description |
|-----------|-------------|
| **Zero blockchain knowledge required to run** | Part 1 works entirely offline with pure Python |
| **Modular architecture** | Each part is independently importable and runnable |
| **Comprehensive test suite** | 47 offline tests cover all edge cases |
| **Educational clarity** | Plain binary tree before the complexity of Patricia Tries |
| **Docker-ready** | One-command execution in any environment |
| **Extensible** | Extension A–D progressively add Ethereum-specific complexity |
| **Windows-compatible** | `pycryptodome` instead of `pysha3` avoids compilation issues |

### Limitations

| Limitation | Description | Workaround |
|------------|-------------|------------|
| Root won't match block header | SHA-256 binary tree ≠ Keccak-256 MPT | Extension A (closer, but still not exact) |
| No full MPT implementation | Complete Patricia Trie is out of scope | Use `eth-trie` library for production |
| No retry/backoff on RPC | Single request; fails on timeout | Add `tenacity` for production |
| Simplified access lists | Extension A uses `[]` for EIP-2930/1559 access lists | Full implementation would parse `tx["accessList"]` |
| Sequential block search (Ext B) | `find_odd_tx_block` fetches up to 100 blocks serially | Parallelize with `concurrent.futures` |

### Design Trade-offs

| Decision | Trade-off Made | Rationale |
|----------|---------------|-----------|
| Double-hashing leaves | Extra hash operation | Domain separation: prevents leaf/internal node confusion |
| Store all levels in `_levels[]` | O(n) extra memory | O(log n) proof generation without tree traversal |
| Standalone `verify_proof` function | Slightly longer call signature | Mirrors real usage — verifier has no tree access |
| `pycryptodome` over `pysha3` | Larger dependency | `pysha3` fails to build on Windows without MSVC |
| SHA-256 for Option A | Doesn't match Ethereum | Validates the tree structure independent of hash function |
| Duplicate-last on odd | Slightly inflates tree | Industry standard, simplest correct approach |

---

*Documentation version: 1.0.0 — Ethereum Merkle Tree Verifier*
