"""
Part 1 — Merkle Tree Implementation
=====================================
Pure Python implementation of a binary Merkle Tree with:
  - Bottom-up tree construction (duplicates last leaf on odd count)
  - Merkle proof generation (sibling hashes from leaf to root)
  - Standalone proof verification (no tree access needed)
"""

import hashlib
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Core hash helper
# ---------------------------------------------------------------------------

def sha256_pair(left: bytes, right: bytes) -> bytes:
    """
    Hash two child digests together to produce a parent node hash.
    Concatenates left + right, then SHA-256 hashes the result.
    """
    return hashlib.sha256(left + right).digest()


def sha256_leaf(data: bytes) -> bytes:
    """Hash a raw data item to produce a leaf node hash."""
    return hashlib.sha256(data).digest()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MerkleNode:
    """A single node in the Merkle tree."""
    hash: bytes
    left: "MerkleNode | None" = field(default=None, repr=False)
    right: "MerkleNode | None" = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Merkle Tree
# ---------------------------------------------------------------------------

class MerkleTree:
    """
    Binary Merkle Tree built bottom-up from a list of raw data items.

    Odd-leaf convention: if a level has an odd number of nodes, the last
    node is duplicated before pairing — the standard approach used in
    Bitcoin and many educational Ethereum implementations.
    """

    def __init__(self, leaves: list[bytes]):
        if not leaves:
            raise ValueError("Cannot build a Merkle tree from an empty leaf list.")

        # Store original leaves for proof generation reference
        self._leaf_hashes: list[bytes] = [sha256_leaf(item) for item in leaves]

        # Build leaf nodes
        leaf_nodes = [MerkleNode(h) for h in self._leaf_hashes]

        # Build tree and store root node
        self._root_node: MerkleNode = self._build(leaf_nodes)

        # Store all levels (bottom = index 0) for proof generation
        self._levels: list[list[MerkleNode]] = []
        self._populate_levels(leaf_nodes)

    # ------------------------------------------------------------------
    # Internal build helpers
    # ------------------------------------------------------------------

    def _build(self, nodes: list[MerkleNode]) -> MerkleNode:
        """
        Recursively pair up nodes and hash each pair until one root remains.
        Mutates nothing — returns the root MerkleNode.
        """
        if len(nodes) == 1:
            return nodes[0]

        next_level: list[MerkleNode] = []
        # Duplicate last node if odd count
        if len(nodes) % 2 == 1:
            nodes = nodes + [nodes[-1]]

        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1]
            parent_hash = sha256_pair(left.hash, right.hash)
            parent = MerkleNode(hash=parent_hash, left=left, right=right)
            next_level.append(parent)

        return self._build(next_level)

    def _populate_levels(self, leaf_nodes: list[MerkleNode]) -> None:
        """
        Reconstruct level-by-level arrays for O(log n) proof generation.
        Index 0 = leaf level, last index = root level.
        """
        current = leaf_nodes[:]
        self._levels.append(current[:])

        while len(current) > 1:
            if len(current) % 2 == 1:
                current = current + [current[-1]]
            next_level: list[MerkleNode] = []
            for i in range(0, len(current), 2):
                left = current[i]
                right = current[i + 1]
                parent_hash = sha256_pair(left.hash, right.hash)
                parent = MerkleNode(hash=parent_hash, left=left, right=right)
                next_level.append(parent)
            current = next_level
            self._levels.append(current[:])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def root(self) -> bytes:
        """Return the 32-byte Merkle root hash."""
        return self._root_node.hash

    def get_proof(self, index: int) -> list[dict]:
        """
        Generate a Merkle proof for the leaf at the given index.

        Returns a list of dicts ordered from the leaf-level sibling up to
        the child of the root:
            [{"hash": <bytes>, "position": "left" | "right"}, ...]

        "position" indicates where the *sibling* sits relative to the
        current node on the path:
          - "right" → sibling is the right child; current node is left
          - "left"  → sibling is the left child; current node is right
        """
        n_leaves = len(self._levels[0])
        if index < 0 or index >= n_leaves:
            raise IndexError(
                f"Leaf index {index} out of range [0, {n_leaves - 1}]."
            )

        proof: list[dict] = []
        current_index = index

        for level in self._levels[:-1]:  # skip root level
            # Pad odd level with duplicate of last element
            padded = level if len(level) % 2 == 0 else level + [level[-1]]

            if current_index % 2 == 0:
                # Current node is left child; sibling is right
                sibling_index = current_index + 1
                # Clamp to last valid index (handles odd padding)
                sibling_index = min(sibling_index, len(padded) - 1)
                proof.append({
                    "hash": padded[sibling_index].hash,
                    "position": "right",
                })
            else:
                # Current node is right child; sibling is left
                sibling_index = current_index - 1
                proof.append({
                    "hash": padded[sibling_index].hash,
                    "position": "left",
                })

            current_index //= 2  # Move up one level

        return proof


# ---------------------------------------------------------------------------
# Standalone proof verifier
# ---------------------------------------------------------------------------

def verify_proof(
    leaf_data: bytes,
    proof: list[dict],
    expected_root: bytes,
) -> bool:
    """
    Verify a Merkle proof without access to the full tree.

    Hashes ``leaf_data`` to get the starting hash, then iteratively
    combines it with each sibling hash in ``proof`` (ordered from leaf
    sibling to root child).  Returns True iff the final computed hash
    matches ``expected_root``.

    Args:
        leaf_data:     The raw original data for the leaf being verified.
        proof:         List of {"hash": bytes, "position": "left"|"right"}.
        expected_root: The known Merkle root to verify against.

    Returns:
        True if the recomputed root equals expected_root, False otherwise.
    """
    current_hash = sha256_leaf(leaf_data)

    for step in proof:
        sibling_hash: bytes = step["hash"]
        position: str = step["position"]

        if position == "right":
            # Current is left child; sibling is right
            current_hash = sha256_pair(current_hash, sibling_hash)
        elif position == "left":
            # Current is right child; sibling is left
            current_hash = sha256_pair(sibling_hash, current_hash)
        else:
            raise ValueError(f"Invalid proof step position: {position!r}")

    return current_hash == expected_root


# ---------------------------------------------------------------------------
# Part 1 self-tests
# ---------------------------------------------------------------------------

def run_part1_tests() -> None:
    """
    Run all Part 1 assertions and print results.
    Covers: valid proof, tampered leaf, tampered proof hash.
    """
    print("=" * 60)
    print("PART 1 — Merkle Tree Unit Tests")
    print("=" * 60)

    items = [b"alice", b"bob", b"carol", b"dave"]
    tree = MerkleTree(items)

    print(f"\nLeaves    : {[i.decode() for i in items]}")
    print(f"Merkle Root: {tree.root.hex()}")

    # ── Test 1: Valid proof for 'carol' (index 2) ─────────────────────────
    proof = tree.get_proof(2)
    result = verify_proof(b"carol", proof, tree.root)
    assert result, "FAIL: Valid proof should return True"
    print(f"\n[PASS] Valid proof for 'carol' (index 2) → {result}")

    # ── Test 2: Tampered leaf ─────────────────────────────────────────────
    result_tampered_leaf = verify_proof(b"mallory", proof, tree.root)
    assert not result_tampered_leaf, "FAIL: Tampered leaf should return False"
    print(f"[PASS] Tampered leaf 'mallory'          → {result_tampered_leaf}")

    # ── Test 3: Tampered proof hash ───────────────────────────────────────
    tampered_proof = [step.copy() for step in proof]
    tampered_proof[0] = {**tampered_proof[0], "hash": b"\x00" * 32}
    result_tampered_proof = verify_proof(b"carol", tampered_proof, tree.root)
    assert not result_tampered_proof, "FAIL: Tampered proof should return False"
    print(f"[PASS] Tampered proof hash              → {result_tampered_proof}")

    # ── Test 4: All leaves verified ───────────────────────────────────────
    print("\n[INFO] Verifying all leaves individually:")
    for i, item in enumerate(items):
        p = tree.get_proof(i)
        ok = verify_proof(item, p, tree.root)
        assert ok, f"FAIL: leaf {i} ({item}) did not verify"
        print(f"       Leaf {i} ({item.decode()!r:8s}) → {ok}")

    # ── Test 5: Odd number of leaves ──────────────────────────────────────
    odd_items = [b"tx1", b"tx2", b"tx3"]
    odd_tree = MerkleTree(odd_items)
    for i, item in enumerate(odd_items):
        p = odd_tree.get_proof(i)
        ok = verify_proof(item, p, odd_tree.root)
        assert ok, f"FAIL: odd-leaf tree leaf {i} did not verify"
    print(f"\n[PASS] Odd-leaf tree (3 leaves) — all proofs verified.")

    # ── Test 6: Single leaf ───────────────────────────────────────────────
    single_tree = MerkleTree([b"only"])
    p = single_tree.get_proof(0)
    ok = verify_proof(b"only", p, single_tree.root)
    assert ok, "FAIL: single-leaf tree proof should verify"
    print(f"[PASS] Single-leaf tree — proof verified.")

    print("\n" + "=" * 60)
    print("All Part 1 tests PASSED ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_part1_tests()
