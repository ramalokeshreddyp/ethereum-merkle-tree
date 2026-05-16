"""
Part 3 — Reconstruct & Verify Ethereum Transactions Root
==========================================================
Ties together Parts 1 and 2:
  - Hashes each transaction in a block (simplified SHA-256 approach)
  - Builds a MerkleTree over those hashes
  - Compares the reconstructed root to the block header's transactionsRoot
  - Generates and verifies inclusion proofs for individual transactions
  - Demonstrates tamper-evidence (broken proof → False)
"""

import hashlib
import os

from src.part1_tree import MerkleTree, verify_proof


# ---------------------------------------------------------------------------
# Transaction hashing
# ---------------------------------------------------------------------------

def hash_transaction(tx: dict) -> bytes:
    """
    Produce a canonical hash for a transaction object.

    Option A (simplified — used here):
        SHA-256 of the transaction's 'hash' hex string encoded as UTF-8.
        Consistent and deterministic; will NOT match Ethereum's actual
        transactionsRoot (which uses RLP + Keccak-256 + Patricia Trie).
        Use this to validate tree logic end-to-end.

    Option B (accurate — see extensions.py):
        Keccak-256 of the RLP-encoded transaction fields.
        Matches the actual transactionsRoot in the block header.

    Args:
        tx: A transaction dict as returned by eth_getBlockByNumber.

    Returns:
        32-byte SHA-256 digest of the transaction hash string.
    """
    tx_hash_str: str = tx.get("hash", "")
    return hashlib.sha256(tx_hash_str.encode("utf-8")).digest()


# ---------------------------------------------------------------------------
# Root reconstruction
# ---------------------------------------------------------------------------

def reconstruct_transactions_root(transactions: list[dict]) -> bytes:
    """
    Hash each transaction with hash_transaction(), build a MerkleTree
    over the resulting leaf hashes, and return the computed root.

    Args:
        transactions: List of full transaction dicts from a block.

    Returns:
        32-byte Merkle root computed over the transaction hashes.

    Raises:
        ValueError: if transactions list is empty.
    """
    if not transactions:
        raise ValueError("No transactions to reconstruct root from.")

    # Pre-hash each transaction to get leaf bytes
    leaf_hashes: list[bytes] = [hash_transaction(tx) for tx in transactions]

    # Build tree — MerkleTree internally sha256_leaf()'s each item,
    # but we are passing already-hashed bytes, so we need a thin wrapper.
    # We pass the raw tx hash bytes as "data" and the tree will sha256 them
    # again — that is intentional for the simplified Option A path where
    # the leaf = sha256(sha256(tx_hash_string)).
    tree = MerkleTree(leaf_hashes)
    return tree.root


def verify_transactions_root(block: dict) -> bool:
    """
    Compare the reconstructed Merkle root against the block header's
    transactionsRoot field.

    With Option A (SHA-256) hashing the roots will NOT match because
    Ethereum uses Keccak-256 + RLP + a Patricia Trie.  Both values are
    printed so the difference is visible.

    Args:
        block: Full block dict as returned by fetch_block().

    Returns:
        True if the roots match (only possible with Option B / extensions.py).
    """
    transactions: list[dict] = block.get("transactions", [])
    header_root: str = block.get("transactionsRoot", "")

    print("\n" + "─" * 60)
    print("Reconstructing Transactions Root …")

    if not transactions:
        print("[WARN] Block has 0 transactions — nothing to reconstruct.")
        return False

    computed_root: bytes = reconstruct_transactions_root(transactions)
    computed_root_hex: str = "0x" + computed_root.hex()

    print(f"\n  Block header transactionsRoot  : {header_root}")
    print(f"  Our reconstructed root (SHA-256): {computed_root_hex}")

    match = computed_root_hex.lower() == header_root.lower()
    if match:
        print("\n  ✓ ROOTS MATCH — Merkle tree reconstruction verified!")
    else:
        print(
            "\n  ✗ Roots differ (expected — Option A uses SHA-256, not Keccak-256)."
        )
        print(
            "    See extensions.py (Extension A) for the exact RLP + Keccak approach."
        )
    print("─" * 60)
    return match


# ---------------------------------------------------------------------------
# Inclusion proof generation & verification
# ---------------------------------------------------------------------------

def prove_transaction_inclusion(
    block: dict,
    tx_index: int = 0,
) -> None:
    """
    Full end-to-end inclusion proof for a specific transaction in a block.

    Steps:
      1. Reconstruct the Merkle tree over all transactions.
      2. Generate a Merkle proof for tx at tx_index.
      3. Verify the proof against the reconstructed root.
      4. Print the proof path (sibling hashes).
      5. Demonstrate tamper-evidence: mutating any sibling breaks verification.

    Args:
        block:    Full block dict from fetch_block().
        tx_index: Index of the transaction to prove (0-based).
    """
    transactions: list[dict] = block.get("transactions", [])
    if not transactions:
        print("[WARN] Block has no transactions.")
        return

    if tx_index < 0 or tx_index >= len(transactions):
        raise IndexError(
            f"tx_index {tx_index} is out of range [0, {len(transactions) - 1}]."
        )

    target_tx: dict = transactions[tx_index]
    target_leaf_data: bytes = hash_transaction(target_tx)

    print("\n" + "=" * 60)
    print("PART 3 — Transaction Inclusion Proof")
    print("=" * 60)
    print(f"\n  Block Number   : {int(block.get('number', '0x0'), 16):,}")
    print(f"  Total Txs      : {len(transactions)}")
    print(f"  Target Tx Index: {tx_index}")
    print(f"  Target Tx Hash : {target_tx.get('hash', 'N/A')}")

    # ── Step 1: Rebuild tree ───────────────────────────────────────────────
    leaf_hashes = [hash_transaction(tx) for tx in transactions]
    tree = MerkleTree(leaf_hashes)
    reconstructed_root = tree.root

    print(f"\n  Reconstructed Merkle Root: {reconstructed_root.hex()}")

    # ── Step 2: Generate proof ─────────────────────────────────────────────
    proof = tree.get_proof(tx_index)

    print(f"\n  Merkle Proof ({len(proof)} steps):")
    for i, step in enumerate(proof):
        print(
            f"    Step {i + 1}: sibling={step['hash'].hex()[:16]}…  "
            f"position={step['position']}"
        )

    # ── Step 3: Verify proof ───────────────────────────────────────────────
    valid = verify_proof(target_leaf_data, proof, reconstructed_root)
    print(f"\n  Proof Verification → {'✓ VALID' if valid else '✗ INVALID'}")
    assert valid, "Proof verification failed for a valid transaction!"

    # ── Step 4: Demonstrate tamper-evidence ───────────────────────────────
    print("\n  [Tamper Demo] Mutating first sibling hash in proof …")
    tampered_proof = [step.copy() for step in proof]
    tampered_proof[0] = {**tampered_proof[0], "hash": b"\xde\xad\xbe\xef" * 8}

    tampered_result = verify_proof(target_leaf_data, tampered_proof, reconstructed_root)
    print(
        f"  Tampered Proof Verification → "
        f"{'✓ VALID' if tampered_result else '✗ INVALID (tamper detected ✓)'}"
    )
    assert not tampered_result, "Tampered proof should have failed!"

    print("\n  [Tamper Demo] Using wrong leaf data (different transaction) …")
    wrong_data = hash_transaction(transactions[(tx_index + 1) % len(transactions)])
    wrong_leaf_result = verify_proof(wrong_data, proof, reconstructed_root)
    print(
        f"  Wrong Leaf Verification    → "
        f"{'✓ VALID' if wrong_leaf_result else '✗ INVALID (tamper detected ✓)'}"
    )
    assert not wrong_leaf_result, "Wrong leaf data should have failed!"

    print("\n" + "=" * 60)
    print("End-to-End Part 3 PASSED ✓")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def run_part3(block: dict, tx_index: int = 0) -> None:
    """
    Run the full Part 3 pipeline on an already-fetched block.

    Args:
        block:    Full block dict from fetch_block().
        tx_index: Which transaction to generate a proof for.
    """
    verify_transactions_root(block)
    prove_transaction_inclusion(block, tx_index)


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    from src.part2_fetch import fetch_block

    load_dotenv()
    rpc_url = os.environ.get("RPC_URL", "")
    if not rpc_url:
        print("ERROR: Set RPC_URL in your .env file.")
        sys.exit(1)

    block = fetch_block(rpc_url, "latest")
    run_part3(block, tx_index=0)
