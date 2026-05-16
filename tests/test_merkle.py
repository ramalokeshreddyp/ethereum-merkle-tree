"""
tests/test_merkle.py — Pytest test suite for the Ethereum Merkle Tree
======================================================================
Covers all core requirements:
  1. MerkleTree class instantiation
  2. Merkle root property (correct, 32-byte)
  3. Proof generation (structure, ordering, correctness)
  4. Standalone proof verification (valid / tampered leaf / tampered proof)
  5. Edge cases: single leaf, odd leaf count, large trees
  6. hash_transaction (Option A)
  7. reconstruct_transactions_root
"""

import hashlib
import pytest

from src.part1_tree import (
    MerkleTree,
    MerkleNode,
    sha256_pair,
    sha256_leaf,
    verify_proof,
)
from src.part3_verify import (
    hash_transaction,
    reconstruct_transactions_root,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tree(items: list[bytes]) -> MerkleTree:
    return MerkleTree(items)


STANDARD_ITEMS = [b"alice", b"bob", b"carol", b"dave"]


# ---------------------------------------------------------------------------
# 1. MerkleTree Class Implementation
# ---------------------------------------------------------------------------

class TestMerkleTreeConstruction:
    def test_build_four_leaves(self):
        tree = make_tree(STANDARD_ITEMS)
        assert tree is not None

    def test_build_single_leaf(self):
        tree = make_tree([b"solo"])
        assert tree is not None

    def test_build_two_leaves(self):
        tree = make_tree([b"left", b"right"])
        assert tree is not None

    def test_build_odd_leaves_three(self):
        tree = make_tree([b"a", b"b", b"c"])
        assert tree is not None

    def test_build_odd_leaves_five(self):
        tree = make_tree([b"a", b"b", b"c", b"d", b"e"])
        assert tree is not None

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            MerkleTree([])

    def test_large_tree(self):
        items = [f"tx_{i}".encode() for i in range(100)]
        tree = make_tree(items)
        assert tree is not None


# ---------------------------------------------------------------------------
# 2. Merkle Root Property
# ---------------------------------------------------------------------------

class TestMerkleRoot:
    def test_root_is_bytes(self):
        tree = make_tree(STANDARD_ITEMS)
        assert isinstance(tree.root, bytes)

    def test_root_is_32_bytes(self):
        tree = make_tree(STANDARD_ITEMS)
        assert len(tree.root) == 32

    def test_root_deterministic(self):
        tree1 = make_tree(STANDARD_ITEMS)
        tree2 = make_tree(STANDARD_ITEMS)
        assert tree1.root == tree2.root

    def test_root_changes_with_different_data(self):
        tree1 = make_tree([b"a", b"b"])
        tree2 = make_tree([b"a", b"c"])
        assert tree1.root != tree2.root

    def test_single_leaf_root(self):
        # Single leaf: root = sha256_pair(sha256_leaf(data), sha256_leaf(data))
        # because the odd-leaf logic duplicates it once
        tree = make_tree([b"only"])
        assert len(tree.root) == 32

    def test_two_leaf_root_manual(self):
        """Manually compute the expected root for 2 leaves and compare."""
        left = sha256_leaf(b"left")
        right = sha256_leaf(b"right")
        expected = sha256_pair(left, right)
        tree = make_tree([b"left", b"right"])
        assert tree.root == expected

    def test_four_leaf_root_manual(self):
        """Manually compute expected root for 4 leaves."""
        h_a = sha256_leaf(b"alice")
        h_b = sha256_leaf(b"bob")
        h_c = sha256_leaf(b"carol")
        h_d = sha256_leaf(b"dave")
        h_ab = sha256_pair(h_a, h_b)
        h_cd = sha256_pair(h_c, h_d)
        expected_root = sha256_pair(h_ab, h_cd)
        tree = make_tree(STANDARD_ITEMS)
        assert tree.root == expected_root


# ---------------------------------------------------------------------------
# 3. Proof Generation Method
# ---------------------------------------------------------------------------

class TestProofGeneration:
    def setup_method(self):
        self.tree = make_tree(STANDARD_ITEMS)

    def test_proof_is_list(self):
        proof = self.tree.get_proof(0)
        assert isinstance(proof, list)

    def test_proof_step_has_hash_key(self):
        proof = self.tree.get_proof(0)
        for step in proof:
            assert "hash" in step

    def test_proof_step_has_position_key(self):
        proof = self.tree.get_proof(0)
        for step in proof:
            assert "position" in step

    def test_proof_position_valid_values(self):
        for i in range(len(STANDARD_ITEMS)):
            proof = self.tree.get_proof(i)
            for step in proof:
                assert step["position"] in ("left", "right")

    def test_proof_step_hash_is_bytes(self):
        proof = self.tree.get_proof(0)
        for step in proof:
            assert isinstance(step["hash"], bytes)
            assert len(step["hash"]) == 32

    def test_proof_length_log2(self):
        # 4-leaf tree → 2-level proof
        proof = self.tree.get_proof(0)
        assert len(proof) == 2

    def test_proof_all_indices(self):
        for i in range(len(STANDARD_ITEMS)):
            proof = self.tree.get_proof(i)
            assert isinstance(proof, list)
            assert len(proof) > 0

    def test_proof_out_of_range(self):
        with pytest.raises(IndexError):
            self.tree.get_proof(100)

    def test_proof_negative_index(self):
        with pytest.raises(IndexError):
            self.tree.get_proof(-1)

    def test_proof_left_child_sibling_is_right(self):
        # Index 0 is left child at leaf level → sibling should be "right"
        proof = self.tree.get_proof(0)
        assert proof[0]["position"] == "right"

    def test_proof_right_child_sibling_is_left(self):
        # Index 1 is right child at leaf level → sibling should be "left"
        proof = self.tree.get_proof(1)
        assert proof[0]["position"] == "left"


# ---------------------------------------------------------------------------
# 4. Standalone Proof Verification
# ---------------------------------------------------------------------------

class TestVerifyProof:
    def setup_method(self):
        self.items = STANDARD_ITEMS
        self.tree = make_tree(self.items)

    def test_valid_proof_returns_true(self):
        for i, item in enumerate(self.items):
            proof = self.tree.get_proof(i)
            assert verify_proof(item, proof, self.tree.root) is True

    def test_tampered_leaf_returns_false(self):
        proof = self.tree.get_proof(2)
        assert verify_proof(b"mallory", proof, self.tree.root) is False

    def test_tampered_proof_hash_returns_false(self):
        proof = self.tree.get_proof(2)
        tampered = [step.copy() for step in proof]
        tampered[0] = {**tampered[0], "hash": b"\x00" * 32}
        assert verify_proof(b"carol", tampered, self.tree.root) is False

    def test_wrong_expected_root_returns_false(self):
        proof = self.tree.get_proof(0)
        wrong_root = b"\xff" * 32
        assert verify_proof(b"alice", proof, wrong_root) is False

    def test_cross_index_proof_fails(self):
        # Proof for index 0 should NOT verify index 1's data
        proof_for_0 = self.tree.get_proof(0)
        assert verify_proof(b"bob", proof_for_0, self.tree.root) is False

    def test_all_tampered_proof_steps_fail(self):
        proof = self.tree.get_proof(1)
        for i in range(len(proof)):
            tampered = [step.copy() for step in proof]
            tampered[i] = {**tampered[i], "hash": b"\xde\xad" * 16}
            assert verify_proof(b"bob", tampered, self.tree.root) is False

    def test_empty_proof_single_leaf(self):
        """Single leaf tree: proof is empty, root equals sha256_leaf(sha256_leaf(data))."""
        single = MerkleTree([b"only"])
        proof = single.get_proof(0)
        assert verify_proof(b"only", proof, single.root) is True

    def test_odd_tree_all_proofs(self):
        items = [b"tx1", b"tx2", b"tx3"]
        tree = make_tree(items)
        for i, item in enumerate(items):
            proof = tree.get_proof(i)
            assert verify_proof(item, proof, tree.root) is True


# ---------------------------------------------------------------------------
# 5. hash_transaction (Option A)
# ---------------------------------------------------------------------------

class TestHashTransaction:
    def test_returns_bytes(self):
        tx = {"hash": "0xabc123"}
        result = hash_transaction(tx)
        assert isinstance(result, bytes)

    def test_returns_32_bytes(self):
        tx = {"hash": "0xdeadbeef"}
        result = hash_transaction(tx)
        assert len(result) == 32

    def test_deterministic(self):
        tx = {"hash": "0x1234"}
        assert hash_transaction(tx) == hash_transaction(tx)

    def test_different_hashes_for_different_txs(self):
        tx1 = {"hash": "0xaaa"}
        tx2 = {"hash": "0xbbb"}
        assert hash_transaction(tx1) != hash_transaction(tx2)

    def test_missing_hash_field(self):
        # Should not crash — empty string fallback
        tx = {}
        result = hash_transaction(tx)
        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# 6. reconstruct_transactions_root
# ---------------------------------------------------------------------------

class TestReconstructTransactionsRoot:
    def _make_txs(self, hashes: list[str]) -> list[dict]:
        return [{"hash": h} for h in hashes]

    def test_returns_bytes(self):
        txs = self._make_txs(["0xaaa", "0xbbb"])
        result = reconstruct_transactions_root(txs)
        assert isinstance(result, bytes)

    def test_returns_32_bytes(self):
        txs = self._make_txs(["0x111", "0x222", "0x333"])
        result = reconstruct_transactions_root(txs)
        assert len(result) == 32

    def test_deterministic(self):
        txs = self._make_txs(["0xabc", "0xdef"])
        assert reconstruct_transactions_root(txs) == reconstruct_transactions_root(txs)

    def test_different_txs_different_root(self):
        txs1 = self._make_txs(["0xaaa", "0xbbb"])
        txs2 = self._make_txs(["0xccc", "0xddd"])
        assert reconstruct_transactions_root(txs1) != reconstruct_transactions_root(txs2)

    def test_empty_txs_raises(self):
        with pytest.raises(ValueError):
            reconstruct_transactions_root([])

    def test_root_matches_manual_construction(self):
        """Verify root equals manually built MerkleTree over same hashes."""
        txs = self._make_txs(["0xdead", "0xbeef", "0xcafe"])
        leaf_hashes = [hash_transaction(tx) for tx in txs]
        tree = MerkleTree(leaf_hashes)
        assert reconstruct_transactions_root(txs) == tree.root


# ---------------------------------------------------------------------------
# sha256_pair helper
# ---------------------------------------------------------------------------

class TestSha256Pair:
    def test_returns_32_bytes(self):
        result = sha256_pair(b"left", b"right")
        assert len(result) == 32

    def test_order_matters(self):
        assert sha256_pair(b"a", b"b") != sha256_pair(b"b", b"a")

    def test_manual_sha256(self):
        expected = hashlib.sha256(b"ab").digest()
        assert sha256_pair(b"a", b"b") == expected
