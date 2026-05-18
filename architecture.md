# Architecture — Ethereum Merkle Tree Verifier

## 1. System Overview

This project implements a **binary Merkle Tree** in Python to verify Ethereum transaction inclusion. The architecture is divided into three independently runnable parts plus an extensions layer, all orchestrated through a single CLI entry point.

```mermaid
graph LR
    subgraph CLI["CLI Layer"]
        M[main.py\nArgparse orchestrator]
    end

    subgraph CORE["Core Layer"]
        P1[part1_tree.py\nMerkleTree • verify_proof]
        P2[part2_fetch.py\nRPC client • inspector]
        P3[part3_verify.py\nHash • Reconstruct • Prove]
        EX[extensions.py\nA B C D]
    end

    subgraph INFRA["Infrastructure"]
        ENV[.env / RPC_URL]
        ETH[Ethereum Mainnet\nJSON-RPC Node]
        DOC[Docker\nDockerfile + compose]
        TST[tests/\npytest suite]
    end

    M --> P1 & P2 & P3 & EX
    P2 --> ETH
    ENV --> P2
    DOC --> M
    TST --> P1 & P3

    style CLI fill:#263238,color:#eceff1,stroke:#607d8b
    style CORE fill:#1a237e,color:#e3f2fd,stroke:#3f51b5
    style INFRA fill:#1b5e20,color:#e8f5e9,stroke:#4caf50
```

---

## 2. Module Architecture

### 2.1 Part 1 — `src/part1_tree.py`

The foundational module. No external imports — uses only Python's `hashlib`.

```mermaid
classDiagram
    class MerkleNode {
        +bytes hash
        +MerkleNode left
        +MerkleNode right
    }

    class MerkleTree {
        -list~bytes~ _leaf_hashes
        -MerkleNode _root_node
        -list~list~MerkleNode~~ _levels
        +__init__(leaves: list~bytes~)
        +_build(nodes) MerkleNode
        +_populate_levels(leaf_nodes) None
        +root bytes
        +get_proof(index) list~dict~
    }

    class verify_proof {
        <<function>>
        +leaf_data bytes
        +proof list~dict~
        +expected_root bytes
        +returns bool
    }

    MerkleTree "1" *-- "n" MerkleNode : contains
    MerkleTree ..> verify_proof : used by
```

**Key design decisions:**

| Decision | Rationale |
|----------|-----------|
| Separate `_build()` and `_populate_levels()` | `_build()` creates the root; `_levels[]` array enables O(log n) proof generation without tree traversal |
| Duplicate last leaf on odd count | Standard Bitcoin/Ethereum educational convention |
| `verify_proof` is standalone | Verifier should need no access to the full tree — mirrors real light client behaviour |
| Double hashing (`sha256_leaf` then `sha256_pair`) | Leaf domain separation prevents second pre-image attacks |

### 2.2 Part 2 — `src/part2_fetch.py`

JSON-RPC client for Ethereum Mainnet.

```mermaid
sequenceDiagram
    participant App as main.py
    participant F as part2_fetch
    participant RPC as Ethereum Node

    App->>F: fetch_block(rpc_url, "latest")
    F->>RPC: POST eth_getBlockByNumber\n["latest", true]
    RPC-->>F: {number, transactionsRoot,\ntransactions: [...full tx objects]}
    F-->>App: block dict

    App->>F: inspect_block(block)
    F->>F: Parse hex fields to decimal
    F-->>App: Printed block summary
```

**Error handling strategy:**

- HTTP errors → `requests.HTTPError` (raised by `.raise_for_status()`)
- RPC-level errors → `ValueError` with code + message
- Missing block → `ValueError("Block not found")`
- Missing env var → `EnvironmentError` with setup instructions

### 2.3 Part 3 — `src/part3_verify.py`

Bridges Parts 1 and 2. Hashes transactions → builds tree → generates + verifies proofs.

```mermaid
flowchart TD
    A[transactions: list~dict~] --> B[hash_transaction\nSHA-256 of tx.hash string]
    B --> C[leaf_hashes: list~bytes~]
    C --> D[MerkleTree\nleaf_hashes]
    D --> E[reconstructed_root: bytes]
    D --> F[get_proof\ntx_index]
    F --> G[proof: list~dict~]
    E & G --> H[verify_proof\nleaf_data, proof, root]
    H --> I{match?}
    I -->|True| J[✅ Inclusion Confirmed]
    I -->|False| K[❌ Tamper Detected]

    style J fill:#1b5e20,color:#c8e6c9
    style K fill:#b71c1c,color:#ffcdd2
```

### 2.4 Extensions — `src/extensions.py`

| Extension | Key Function | Dependencies |
|-----------|-------------|--------------|
| **A — RLP + Keccak** | `hash_transaction_keccak(tx)` | `rlp`, `pycryptodome` |
| **B — Odd Leaf** | `find_odd_tx_block(rpc_url)` | `part2_fetch` |
| **C — Light Client** | `light_client_verify(header, idx, proof, leaf)` | `part1_tree` |
| **D — Historical** | `run_extension_d(rpc_url)` | `part2_fetch`, `part3_verify` |

---

## 3. Data Flow

### 3.1 Tree Construction Data Flow

```mermaid
flowchart LR
    RAW["Raw bytes\nb'alice', b'bob'..."] -->|sha256_leaf| LEAF["Leaf hashes\n32 bytes each"]
    LEAF -->|Pair & hash| L1["Level 1 hashes"]
    L1 -->|Pair & hash| L2["Level 2 hashes"]
    L2 -->|...| ROOT["Merkle Root\n32 bytes"]

    LEAF -->|stored in _levels[0]| LVLS["_levels array\n[leaves, L1, L2, ..., root]"]
    L1 -->|stored in _levels[1]| LVLS
    ROOT -->|stored in _root_node| RN["_root_node\nMerkleNode"]

    style ROOT fill:#4a148c,color:#e1bee7
    style RN fill:#4a148c,color:#e1bee7
```

### 3.2 Proof Generation Data Flow

```mermaid
flowchart TD
    IDX[tx_index = 2] --> CURR[current_index = 2]
    CURR --> L0["_levels[0] — leaf level\nidx=2 is even → sibling=3 (right)"]
    L0 --> PROOF1["proof[0] = {hash: _levels[0][3].hash, position: 'right'}"]
    PROOF1 --> UP1["current_index = 2 // 2 = 1"]
    UP1 --> L1["_levels[1] — internal level\nidx=1 is odd → sibling=0 (left)"]
    L1 --> PROOF2["proof[1] = {hash: _levels[1][0].hash, position: 'left'}"]
    PROOF2 --> UP2["current_index = 1 // 2 = 0\n(reached root level — stop)"]
    UP2 --> DONE["proof = [step0, step1]"]

    style DONE fill:#0d47a1,color:#bbdefb
```

### 3.3 Proof Verification Data Flow

```mermaid
flowchart LR
    LD["leaf_data: b'carol'"] -->|sha256_leaf| CH["current_hash"]
    CH -->|step.position == 'right'| C1["sha256_pair(current, sibling)"]
    C1 -->|step.position == 'left'| C2["sha256_pair(sibling, current)"]
    C2 --> COMP["computed_root"]
    COMP --> CMP{"== expected_root?"}
    CMP -->|Yes| TRUE["return True ✅"]
    CMP -->|No| FALSE["return False ❌"]

    style TRUE fill:#2e7d32,color:#fff
    style FALSE fill:#c62828,color:#fff
```

---

## 4. Cryptographic Design

### Hash Function Selection

| Layer | Hash Function | Why |
|-------|--------------|-----|
| Leaf hashing | SHA-256 (hashlib) | Standard library, deterministic, collision-resistant |
| Internal nodes | SHA-256 of concatenation | Binds children together cryptographically |
| Extension A leaves | Keccak-256 of RLP bytes | Matches Ethereum's actual leaf computation |

### Tamper Evidence Properties

```mermaid
flowchart TD
    TX["Tamper any transaction"] --> LH["Leaf hash changes\nsha256(new_tx_data) ≠ old"]
    LH --> IH["Parent hash changes\nsha256(new_leaf ∥ sibling) ≠ old"]
    IH --> RH["Root hash changes\npropagates all the way up"]
    RH --> MISMATCH["Reconstructed root ≠ block header root"]
    MISMATCH --> DETECT["Tamper detected ✅"]

    style TX fill:#b71c1c,color:#ffcdd2
    style DETECT fill:#1b5e20,color:#c8e6c9
```

### Odd-Leaf Duplication

```
3 leaves: [H_a, H_b, H_c]
          └ duplicate last → [H_a, H_b, H_c, H_c]
          → pair: [H(H_a‖H_b), H(H_c‖H_c)]
          → root: H(H_ab ‖ H_cc)
```

This convention is applied consistently at every level of the tree during both build and proof generation.

---

## 5. Container Architecture

```mermaid
graph TB
    subgraph HOST["Host Machine"]
        ENV_FILE[".env file\nRPC_URL=..."]
        SRC["Source code\n./src ./tests ./main.py"]
    end

    subgraph DOCKER["Docker Network"]
        subgraph APP_SVC["app service"]
            A_IMG["python:3.11-slim\n+ requirements.txt"]
            A_CMD["CMD: python main.py"]
        end
        subgraph TEST_SVC["tests service"]
            T_IMG["python:3.11-slim\n(shared image)"]
            T_CMD["CMD: pytest tests/ -v"]
        end
    end

    ENV_FILE -->|env_file mount| APP_SVC & TEST_SVC
    SRC -->|COPY . .| APP_SVC & TEST_SVC

    style HOST fill:#263238,color:#eceff1
    style DOCKER fill:#0d47a1,color:#e3f2fd
    style APP_SVC fill:#1565c0,color:#e3f2fd
    style TEST_SVC fill:#1565c0,color:#e3f2fd
```

**Dockerfile layers (optimised for cache):**

```
python:3.11-slim
└── RUN apt-get gcc python3-dev        # system deps for pycryptodome
└── COPY requirements.txt              # cached separately
└── RUN pip install -r requirements.txt
└── COPY . .                           # source last (most volatile)
└── CMD ["python", "main.py"]
```

---

## 6. Dependency Graph

```mermaid
graph TD
    MAIN[main.py] --> P1 & P2 & P3 & EXT

    P3[part3_verify.py] --> P1[part1_tree.py]
    EXT[extensions.py] --> P1 & P2[part2_fetch.py] & P3

    P1 --> HL[hashlib\nstdlib]
    P2 --> REQ[requests]
    P2 --> OS[os\nstdlib]
    EXT --> RLP[rlp]
    EXT --> PCD[pycryptodome]

    MAIN --> DOT[python-dotenv]
    TST[tests/test_merkle.py] --> P1 & P3 & PY[pytest]

    style MAIN fill:#37474f,color:#eceff1
    style P1 fill:#1a237e,color:#e3f2fd
    style P2 fill:#1a237e,color:#e3f2fd
    style P3 fill:#1a237e,color:#e3f2fd
    style EXT fill:#4a148c,color:#e1bee7
```

---

## 7. Error Handling Architecture

| Layer | Error Type | Handler |
|-------|-----------|---------|
| RPC HTTP | `requests.HTTPError` | Re-raised from `_rpc_call()` |
| RPC logic | `ValueError` | Raised with code + message |
| Missing block | `ValueError` | "Block not found" |
| Empty tree | `ValueError` | "Cannot build from empty list" |
| Bad proof index | `IndexError` | "Leaf index out of range" |
| Missing RPC_URL | `EnvironmentError` | Printed with setup steps, `sys.exit(1)` |
| Extension A import | `ImportError` | Caught, prints `[SKIP]` message |

---

## 8. Scalability Considerations

| Factor | Current Approach | Production Approach |
|--------|-----------------|-------------------|
| Proof size | O(log₂ n) hashes | Same — this is optimal |
| Tree build | O(n) memory for all levels | Could stream, store only current + previous level |
| RPC calls | Single `eth_getBlockByNumber` | Retry logic + backoff for production |
| Transaction hashing | SHA-256 of tx hash string | Full RLP + Keccak-256 (Extension A) |
| Trie structure | Plain binary tree | Merkle Patricia Trie (Ethereum actual) |

---

## 9. Why Not a Merkle Patricia Trie?

Ethereum's actual `transactionsRoot` is computed using a **Merkle Patricia Trie** (MPT), not a plain binary tree:

| Aspect | Plain Binary Tree (this project) | Merkle Patricia Trie (Ethereum) |
|--------|----------------------------------|--------------------------------|
| Indexing | Position-based (index 0, 1, 2…) | Key-value (RLP-encoded index as key) |
| Proof type | List of sibling hashes | List of trie nodes along path |
| Match block header? | ❌ No | ✅ Yes |
| Conceptual clarity | ✅ High | ⚠️ Complex |
| Purpose here | Build core intuition | Production blockchain use |

This project implements the plain binary tree to build solid intuition of the core concept. Extension A brings the leaf hashing closer to Ethereum's actual computation.
