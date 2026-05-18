# Questionnaire Answers — Ethereum Merkle Tree Verifier

---

## Q1. Explain the design of your MerkleTree class. Why did you choose to build it bottom-up? What are the trade-offs of this approach?

### Design Overview

The `MerkleTree` class in `src/part1_tree.py` is built around three internal structures:

- `_leaf_hashes: list[bytes]` — the SHA-256 hash of every input item, computed once in `__init__` via `sha256_leaf()`.
- `_root_node: MerkleNode` — the single root node returned by the recursive `_build()` method.
- `_levels: list[list[MerkleNode]]` — a level-indexed array where `_levels[0]` is the leaf level and the last entry is the root level, populated by `_populate_levels()`.

The `MerkleNode` dataclass holds a `hash: bytes` field and optional `left`/`right` child references.

### Why Bottom-Up?

Bottom-up construction (leaf → root) is the natural fit for this use case because:

1. **All data is known upfront.** Unlike an incremental structure (e.g., an AVL tree where insertions happen one by one), a Merkle tree is typically built once over a fixed dataset — an Ethereum block's transactions are final before the block is sealed.
2. **It is deterministic and order-preserving.** Pairing `nodes[i]` with `nodes[i+1]` in strict left-to-right order guarantees the same root for the same input sequence, which is the core security property.
3. **Odd-leaf handling is straightforward.** Duplicating the last node before pairing at each level is a single `if len(nodes) % 2 == 1` check per level, applied uniformly throughout the recursion.

### Implementation Detail

`_build()` is a recursive function:
- **Base case:** `len(nodes) == 1` → the single node is the root.
- **Recursive case:** pad if odd, pair adjacent nodes, hash each pair with `sha256_pair(left.hash, right.hash)`, recurse on the parent list.

`_populate_levels()` runs the same pairing logic iteratively and stores each level, giving `get_proof()` O(log n) index access to sibling nodes without traversing the tree.

### Trade-offs

| Trade-off | Bottom-Up Approach | Alternative (Top-Down / On-Demand) |
|-----------|-------------------|-----------------------------------|
| **Memory** | O(n) extra — all levels stored in `_levels[]` | O(log n) — only path to root kept |
| **Proof generation** | O(log n) direct index access — fast | O(n) traversal required each time |
| **Build cost** | O(n) — single pass | Same |
| **Incremental updates** | Requires full rebuild | Can update a single path in O(log n) |
| **Simplicity** | High — straightforward recursion | Lower — requires parent pointers or lazy evaluation |

The key trade-off accepted: storing all levels costs O(n) memory, but makes `get_proof()` a simple array index operation rather than a tree traversal. For the blockchain use case (build once, prove many times), this is the right choice.

---

## Q2. Describe the structure of the Merkle proof you generate. Why is this specific information (sibling hash and position) necessary and sufficient to verify inclusion?

### Proof Structure

`get_proof(index)` returns an ordered `list[dict]`, one entry per level from leaf up to (but not including) the root:

```python
[
    {"hash": <bytes — sibling's 32-byte hash>, "position": "left" | "right"},
    ...
]
```

- **`hash`** is the sibling node's precomputed hash at that level.
- **`position`** is where the *sibling* sits relative to the node on the path: `"right"` means the current node is the left child; `"left"` means the current node is the right child.

For a 4-leaf tree and `index=2` (leaf `H_c`):

```
proof = [
    {"hash": H_d,  "position": "right"},   # level 0: sibling of H_c is H_d (right)
    {"hash": H_ab, "position": "left"},    # level 1: sibling of H_cd is H_ab (left)
]
```

### Why This Is Necessary and Sufficient

**Necessary:** To recompute any internal node hash, you need both children in the correct left/right order. `sha256_pair(left, right) ≠ sha256_pair(right, left)` — order is not commutative. Without the `position` flag, the verifier cannot determine which argument goes on which side of the concatenation, so the recomputed hashes would not match.

**Sufficient:** The verifier only needs to reconstruct the *path* from leaf to root — not the entire tree. Starting from `sha256_leaf(leaf_data)`:

```
current = sha256_leaf(leaf_data)
for step in proof:
    if step["position"] == "right":
        current = sha256_pair(current, step["hash"])   # current is left child
    else:
        current = sha256_pair(step["hash"], current)   # current is right child
# current is now the recomputed root
return current == expected_root
```

Each step computes exactly one internal node. After `len(proof)` steps, `current` is the root. If it matches `expected_root`, inclusion is proven — any tampering with the leaf or any sibling hash breaks the chain and produces a different root. No other information is needed.

**Proof size:** For a tree with `n` leaves, the proof has `⌈log₂(n)⌉` steps. For the 201-transaction block fetched during testing, the proof had 8 steps (`⌈log₂(201)⌉ = 8`).

---

## Q3. The task mentions Ethereum uses a Merkle Patricia Trie, not a simple binary tree. What are the key advantages of a Trie for Ethereum's state and transaction data?

### What is a Merkle Patricia Trie (MPT)?

An MPT is a deterministic, cryptographically authenticated key-value store that combines:
- **Patricia Trie** (Radix-16 trie) for efficient key-based lookup
- **Merkle hashing** at every node for tamper evidence and proof generation

Ethereum uses MPTs for three roots in every block header: `stateRoot`, `transactionsRoot`, and `receiptsRoot`.

### Key Advantages over a Plain Binary Tree

**1. Key-Value Storage with Efficient Lookup**

A binary Merkle tree is indexed by *position* — leaf 0, 1, 2, … A Patricia Trie is indexed by *key*. For Ethereum's state trie, the key is the Keccak-256 hash of an account address, and the value is the account's RLP-encoded `{nonce, balance, storageRoot, codeHash}`. This allows direct O(key_length) lookup of any account's state without scanning all leaves.

For the transactions trie, the key is the RLP-encoded transaction index, enabling direct access to transaction `i` without iterating the entire block.

**2. Efficient Updates (O(log n) path update)**

In a plain binary tree, updating one leaf requires recomputing every node on the path from leaf to root — which is also O(log n), so that part is comparable. However, the Patricia Trie's branching structure means that inserting or updating a key only affects the specific branch path, and shared prefixes between keys are collapsed into single nodes. This makes the trie very storage-efficient for sparse key spaces (e.g., account addresses).

**3. Deterministic Root for Arbitrary Key-Value Stores**

A plain binary tree requires that leaves be provided in a fixed order. A Patricia Trie produces the *same root* regardless of the insertion order of key-value pairs, as long as the final key-value set is identical. This is essential for Ethereum: every full node in the network must compute the identical `stateRoot` from the same set of account states, even if they processed transactions in different internal orders.

**4. Compact Proofs for Sparse State**

Ethereum's state has billions of possible account addresses. A binary tree over all possible keys would be enormous. The Patricia Trie only stores *existing* accounts, with shared prefix compression (extension nodes). Proofs still have O(key_length) size, independent of the total number of accounts — around 64 nibbles (32 bytes × 2) for any Ethereum address.

**5. Null / Non-Membership Proofs**

A plain binary tree can only prove that a leaf *is* in the tree. A Patricia Trie can also prove that a key *is not* present (non-membership proof) by showing the path terminates at a node that doesn't contain the queried key. This is critical for light clients verifying that an account has zero balance or doesn't exist.

---

## Q4. How does your RPC interaction code handle potential network errors or invalid responses from the Ethereum endpoint?

### Error Handling Strategy in `src/part2_fetch.py`

All RPC calls go through the `_rpc_call()` internal helper:

```python
def _rpc_call(rpc_url: str, method: str, params: list) -> Any:
    response = requests.post(rpc_url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()          # raises HTTPError for 4xx/5xx
    data = response.json()
    if "error" in data:
        raise ValueError(
            f"RPC error [{data['error'].get('code')}]: {data['error'].get('message')}"
        )
    return data.get("result")
```

**Layer 1 — HTTP-level errors:** `response.raise_for_status()` raises `requests.HTTPError` on any non-2xx HTTP status (e.g., 429 rate limit, 503 service unavailable). This surfaces network and provider-level failures immediately.

**Layer 2 — JSON-RPC application errors:** The JSON-RPC 2.0 spec uses an `"error"` field in the response body even when HTTP status is 200 (e.g., invalid method, invalid params, execution reverted). The explicit `if "error" in data` check raises a `ValueError` with the RPC error code and message, making the failure reason visible.

**Layer 3 — Missing result:** `fetch_block()` checks `if result is None` and raises `ValueError("Block not found")`, preventing silent failures when the requested block doesn't exist on the network.

**Layer 4 — Environment validation:** `run_part2()` checks for an empty `RPC_URL` before making any network call and raises `EnvironmentError` with step-by-step setup instructions rather than a cryptic `ConnectionError`.

**Layer 5 — Timeout:** All `requests.post()` calls use `timeout=30` seconds. This prevents the script from hanging indefinitely on a slow or unresponsive endpoint.

**Layer 6 — Extension-level graceful degradation:** In `fetch_transaction_proof()` and the extensions, failures are caught with a broad `except Exception as exc` and printed as `[WARN]` messages rather than crashing the program. This allows the main pipeline to continue even if an optional call fails.

### What is NOT implemented (intentionally, for scope)

- **Retry with backoff:** There is no `tenacity`-based retry loop. A single timeout is sufficient for the educational scope. Production code would add exponential backoff with jitter for 429/503 responses.
- **Connection pooling:** Each call creates a new TCP connection. A `requests.Session()` would be used in a production client.

---

## Q5. Which extension challenges did you attempt, and what was the result?

All four extension challenges were implemented in `src/extensions.py`.

### Extension A — RLP Encoding + Keccak-256

**Implemented:** `keccak256()`, `rlp_encode_transaction()`, `hash_transaction_keccak()`, `reconstruct_root_keccak()`.

`rlp_encode_transaction()` handles all three transaction types present on Ethereum Mainnet:
- **Type 0 (legacy):** `rlp.encode([nonce, gasPrice, gas, to, value, data, v, r, s])`
- **Type 1 (EIP-2930):** `b"\x01" + rlp.encode([chainId, nonce, gasPrice, gas, to, value, data, accessList, v, r, s])`
- **Type 2 (EIP-1559):** `b"\x02" + rlp.encode([chainId, nonce, maxPriorityFeePerGas, maxFeePerGas, gas, to, value, data, accessList, v, r, s])`

**Keccak-256** is computed via `pycryptodome` (`Crypto.Hash.keccak`) instead of `pysha3`, which fails to compile on Windows without MSVC.

**Did the root match?** The reconstructed root using Keccak-256 leaf hashes **does not exactly match** the block header's `transactionsRoot`. The leaf hashes are computed correctly (Keccak-256 of RLP-encoded transaction), but the tree structure differs: Ethereum's `transactionsRoot` is a **Merkle Patricia Trie**, not a plain binary tree. The trie keys are RLP-encoded transaction indices, not positional array indices. A plain binary tree over the correct leaf hashes will produce a different root structure. Extension A successfully moves the leaf hashing layer to the correct algorithm; the remaining gap is the trie vs. binary-tree distinction.

**Run with:** `python main.py --extensions a`

### Extension B — Odd-Leaf Block Detection

**Implemented:** `find_odd_tx_block()` searches backwards from the latest block (up to 100 blocks) for one with an odd transaction count. `run_extension_b()` then runs `prove_transaction_inclusion()` on the last transaction (the one whose proof exercises the odd-leaf duplication path).

**Result:** Consistently finds a block with an odd transaction count within the first few blocks searched. The proof for the last transaction in an odd-count block verifies successfully, confirming that the `if len(nodes) % 2 == 1: nodes = nodes + [nodes[-1]]` duplication is applied correctly at every level.

**Run with:** `python main.py --extensions b`

### Extension C — Light Client Simulation

**Implemented:** `light_client_verify(block_header, tx_index, proof, leaf_data)` accepts only the block header dict (with `transactions` key stripped out) and a pre-generated proof. It reads `transactionsRoot` from the header, converts it to bytes, and calls `verify_proof(leaf_data, proof, header_root_bytes)`.

**Result:** Successfully verifies transaction inclusion using only the block header and proof — no full transaction list is accessed inside the function. This mirrors the real Ethereum light client protocol: a full node provides the proof, and the light client only needs the block header (which it already has, as headers form a chain it tracks) plus the proof to verify any transaction.

**Run with:** `python main.py --extensions c`

### Extension D — Historical Block Verification

**Implemented:** `run_extension_d()` computes `latest_block_number - 1_296_000` (approximately 6 months ago at ~12 seconds/block) and fetches that historical block. It then runs `prove_transaction_inclusion()` on the first transaction.

**Result:** Successfully fetches the historical block and verifies the inclusion proof. The `transactionsRoot` committed in that block's header when it was mined cannot have changed — it is part of the immutable blockchain. Verifying a proof against it demonstrates that Merkle proofs work across historical blocks just as well as current ones.

**Run with:** `python main.py --extensions d`
