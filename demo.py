#!/usr/bin/env python3
"""
demo.py — Offline Demo of the Merkle Tree Implementation
=========================================================
This script demonstrates the Merkle tree without requiring a network
connection or Ethereum RPC endpoint.

Run:
    python demo.py

Output:
    - Builds a Merkle tree from sample data
    - Shows the tree structure
    - Generates inclusion proofs
    - Verifies proofs
    - Demonstrates tamper-detection
"""

import sys
from src.part1_tree import MerkleTree, sha256_leaf, sha256_pair, verify_proof


def print_header(title: str, width: int = 70) -> None:
    """Print a formatted header."""
    print(f"\n{'═' * width}")
    print(f"  {title}")
    print(f"{'═' * width}\n")


def bytes_to_hex_short(b: bytes, length: int = 16) -> str:
    """Convert bytes to shortened hex string."""
    hex_str = b.hex()
    if len(hex_str) > length:
        return hex_str[:length] + "…"
    return hex_str


def demo_part1_basics() -> None:
    """Demonstrate basic tree construction and properties."""
    print_header("Part 1: Basic Merkle Tree Construction")

    # Build a simple tree
    items = [b"Alice", b"Bob", b"Carol", b"Dave"]
    tree = MerkleTree(items)

    print(f"Items: {[item.decode() for item in items]}\n")
    print(f"Root Hash: {tree.root.hex()}")
    print(f"Root Hash (short): 0x{bytes_to_hex_short(tree.root)}…\n")

    # Show deterministic property
    tree2 = MerkleTree(items)
    print(f"Deterministic: {tree.root == tree2.root} ✓\n")

    # Show tamper-detection
    items_tampered = [b"Alice", b"Bob", b"Carol", b"Eve"]  # Changed Dave → Eve
    tree_tampered = MerkleTree(items_tampered)
    print(f"Tampered items: {[item.decode() for item in items_tampered]}")
    print(f"Root differs: {tree.root != tree_tampered.root} ✓")
    print(f"Original: 0x{bytes_to_hex_short(tree.root)}…")
    print(f"Tampered: 0x{bytes_to_hex_short(tree_tampered.root)}…\n")


def demo_proof_generation() -> None:
    """Demonstrate proof generation for specific leaves."""
    print_header("Part 2: Merkle Proof Generation")

    items = [b"alice", b"bob", b"carol", b"dave"]
    tree = MerkleTree(items)

    # Generate proof for Carol (index 2)
    carol_index = 2
    proof = tree.get_proof(carol_index)

    print(f"Target item: {items[carol_index].decode()!r} (index {carol_index})\n")
    print(f"Proof length: {len(proof)} sibling hashes\n")
    print(f"Proof path:")
    for i, step in enumerate(proof, 1):
        position = step["position"]
        hash_hex = bytes_to_hex_short(step["hash"])
        print(f"  Step {i}: sibling at {position:6s} = 0x{hash_hex}…")
    print()


def demo_proof_verification() -> None:
    """Demonstrate proof verification."""
    print_header("Part 3: Merkle Proof Verification")

    items = [b"alice", b"bob", b"carol", b"dave"]
    tree = MerkleTree(items)

    # Test 1: Valid proof
    print("TEST 1: Valid Proof")
    print("─" * 50)
    carol_index = 2
    proof = tree.get_proof(carol_index)
    result = verify_proof(items[carol_index], proof, tree.root)
    print(f"Leaf data: {items[carol_index]!r}")
    print(f"Verification result: {result}")
    print(f"Status: {'✅ PASSED' if result else '❌ FAILED'}\n")

    # Test 2: Wrong leaf data
    print("TEST 2: Wrong Leaf Data")
    print("─" * 50)
    result = verify_proof(b"mallory", proof, tree.root)
    print(f"Leaf data: b'mallory' (wrong)")
    print(f"Verification result: {result}")
    print(f"Status: {'✅ PASSED (tamper detected)' if not result else '❌ FAILED'}\n")

    # Test 3: Tampered proof
    print("TEST 3: Tampered Proof Hash")
    print("─" * 50)
    tampered_proof = [step.copy() for step in proof]
    tampered_proof[0]["hash"] = b"\x00" * 32
    result = verify_proof(items[carol_index], tampered_proof, tree.root)
    print(f"Original sibling: 0x{bytes_to_hex_short(proof[0]['hash'])}…")
    print(f"Tampered sibling: 0x{bytes_to_hex_short(tampered_proof[0]['hash'])}…")
    print(f"Verification result: {result}")
    print(f"Status: {'✅ PASSED (tamper detected)' if not result else '❌ FAILED'}\n")


def demo_odd_leaves() -> None:
    """Demonstrate handling of odd number of leaves."""
    print_header("Part 4: Odd Number of Leaves")

    items = [b"tx1", b"tx2", b"tx3"]  # 3 items (odd)
    tree = MerkleTree(items)

    print(f"Items: {[item.decode() for item in items]} ({len(items)} items)\n")
    print(f"All proofs verified:")

    for i, item in enumerate(items):
        proof = tree.get_proof(i)
        result = verify_proof(item, proof, tree.root)
        status = "✓" if result else "✗"
        print(f"  {status} Item {i} ({item.decode():3s})")

    print(f"\nRoot: 0x{bytes_to_hex_short(tree.root)}…\n")


def demo_large_tree() -> None:
    """Demonstrate efficiency with large trees."""
    print_header("Part 5: Efficiency with Large Trees")

    # Build a tree with 1000 items
    items = [f"tx_{i:04d}".encode() for i in range(1000)]
    tree = MerkleTree(items)

    print(f"Tree size: {len(items)} leaves\n")

    # Generate proof for middle item
    middle_index = len(items) // 2
    proof = tree.get_proof(middle_index)

    print(f"Proof for item {middle_index}:")
    print(f"  Proof size: {len(proof)} sibling hashes")
    print(f"  Proof bytes: {len(proof) * 32} bytes (if using 32-byte hashes)")
    print(f"  Efficiency: log₂({len(items)}) ≈ {len(proof)} hashes needed\n")

    # Verify
    result = verify_proof(items[middle_index], proof, tree.root)
    print(f"Verification: {'✅ PASSED' if result else '❌ FAILED'}\n")


def demo_transaction_simulation() -> None:
    """Simulate transaction verification scenario."""
    print_header("Part 6: Transaction Verification Scenario")

    # Simulate Ethereum transactions
    transactions = [
        b"0xaabbccdd1111...",  # Tx 1
        b"0xeeff00112222...",  # Tx 2
        b"0x33445566aaaa...",  # Tx 3
        b"0xbbccddee7777...",  # Tx 4 (transaction of interest)
        b"0xff0011229999...",  # Tx 5
    ]

    tree = MerkleTree(transactions)

    # Light client receives:
    # 1. Block header with transactionsRoot
    # 2. Merkle proof for the transaction of interest
    # 3. The transaction data itself

    tx_of_interest_index = 3
    tx_of_interest = transactions[tx_of_interest_index]
    transactions_root = tree.root
    proof = tree.get_proof(tx_of_interest_index)

    print("Scenario: Light Client Verifying Transaction Inclusion")
    print("─" * 50)
    print(f"\nLight client receives:")
    print(f"  1. Block header with transactionsRoot")
    print(f"     Root: 0x{bytes_to_hex_short(transactions_root)}…")
    print(f"  2. Transaction of interest")
    print(f"     Tx: {tx_of_interest.decode()}")
    print(f"  3. Merkle proof ({len(proof)} steps)")

    # Light client verifies
    is_valid = verify_proof(tx_of_interest, proof, transactions_root)

    print(f"\nLight client verification: {'✅ VALID' if is_valid else '❌ INVALID'}")
    print(f"\n✨ Transaction {tx_of_interest_index} is proven to be in the block\n")


def demo_tree_structure_ascii() -> None:
    """Show ASCII representation of tree structure."""
    print_header("Part 7: Tree Structure Visualization")

    items = [b"A", b"B", b"C", b"D"]
    print("Input items: A, B, C, D\n")
    print("Merkle tree structure:")
    print("""
                         ┌─── Root ───┐
                         │  H(AB, CD) │
                         └─────┬─────┘
                           /       \\
                    ┌─────────┐   ┌─────────┐
                    │ H(A, B) │   │ H(C, D) │
                    └────┬────┘   └────┬────┘
                       /  \\           /  \\
                    H(A) H(B)      H(C) H(D)
                     │    │        │    │
                     A    B        C    D

    Each parent = SHA256(left_child + right_child)
    Root is the cryptographic fingerprint of the entire dataset.
    """)

    tree = MerkleTree(items)
    print(f"\nComputed root: 0x{bytes_to_hex_short(tree.root)}\n")


def main() -> None:
    """Run all demonstrations."""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║                                                                    ║")
    print("║  🔗 Ethereum Merkle Tree — Offline Demo                          ║")
    print("║     (No RPC endpoint or network connection required)             ║")
    print("║                                                                    ║")
    print("╚" + "═" * 68 + "╝")

    try:
        demo_part1_basics()
        demo_proof_generation()
        demo_proof_verification()
        demo_odd_leaves()
        demo_large_tree()
        demo_transaction_simulation()
        demo_tree_structure_ascii()

        print_header("Demo Complete!")
        print("✅ All demonstrations executed successfully.\n")
        print("Next steps:")
        print("  1. Review the code in src/part1_tree.py")
        print("  2. Run tests: pytest tests/test_merkle.py -v")
        print("  3. Run the full pipeline: python main.py --part 1\n")

    except Exception as exc:
        print(f"\n❌ Error: {exc}\n", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
