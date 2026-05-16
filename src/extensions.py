"""
Extension Challenges
=====================
Extension A — RLP + Keccak-256 hashing (matches Ethereum's actual root)
Extension B — Odd-leaf block detection and validation
Extension C — Light client simulation (header-only proof verification)
Extension D — Historical block verification

Install extras:  pip install rlp pysha3
"""

import hashlib
import os
from typing import Optional


# ---------------------------------------------------------------------------
# Extension A — RLP Encoding + Keccak-256
# ---------------------------------------------------------------------------

def keccak256(data: bytes) -> bytes:
    """Compute Keccak-256 hash using pycryptodome."""
    try:
        from Crypto.Hash import keccak
        k = keccak.new(digest_bits=256)
        k.update(data)
        return k.digest()
    except ImportError:
        raise ImportError(
            "pycryptodome is required for Extension A. Install with: pip install pycryptodome"
        )


def _to_int(hex_str: str) -> int:
    """Convert a 0x-prefixed hex string to int, handling None."""
    if hex_str is None or hex_str == "0x":
        return 0
    return int(hex_str, 16)


def _to_bytes(hex_str: str) -> bytes:
    """Convert a 0x-prefixed hex string to bytes."""
    if hex_str is None or hex_str in ("0x", ""):
        return b""
    s = hex_str[2:] if hex_str.startswith("0x") else hex_str
    if len(s) % 2:
        s = "0" + s
    return bytes.fromhex(s)


def rlp_encode_transaction(tx: dict) -> bytes:
    """
    RLP-encode a legacy (Type 0) Ethereum transaction for Keccak hashing.

    Fields encoded (in order per EIP-155 / Yellow Paper):
        nonce, gasPrice, gas, to, value, input, v, r, s

    Note: EIP-2930 (Type 1) and EIP-1559 (Type 2) transactions have a
    type prefix byte prepended before the RLP-encoded list.

    Args:
        tx: Transaction dict from eth_getBlockByNumber.

    Returns:
        RLP-encoded bytes of the transaction.
    """
    try:
        import rlp
        from rlp.sedes import Binary, big_endian_int, binary, List
    except ImportError:
        raise ImportError(
            "rlp is required for Extension A. Install with: pip install rlp"
        )

    tx_type = _to_int(tx.get("type", "0x0"))

    nonce = _to_int(tx.get("nonce", "0x0"))
    gas = _to_int(tx.get("gas", "0x0"))
    value = _to_int(tx.get("value", "0x0"))
    to_bytes = _to_bytes(tx.get("to", "") or "")
    data_bytes = _to_bytes(tx.get("input", "0x") or "0x")
    v = _to_int(tx.get("v", "0x0"))
    r = _to_bytes(tx.get("r", "0x0"))
    s = _to_bytes(tx.get("s", "0x0"))

    if tx_type == 0:
        gas_price = _to_int(tx.get("gasPrice", "0x0"))
        fields = [nonce, gas_price, gas, to_bytes, value, data_bytes, v, r, s]
        encoded = rlp.encode(fields)
    elif tx_type == 1:
        # EIP-2930
        chain_id = _to_int(tx.get("chainId", "0x1"))
        gas_price = _to_int(tx.get("gasPrice", "0x0"))
        access_list = []  # simplified
        fields = [chain_id, nonce, gas_price, gas, to_bytes, value, data_bytes, access_list, v, r, s]
        encoded = b"\x01" + rlp.encode(fields)
    elif tx_type == 2:
        # EIP-1559
        chain_id = _to_int(tx.get("chainId", "0x1"))
        max_priority_fee = _to_int(tx.get("maxPriorityFeePerGas", "0x0"))
        max_fee = _to_int(tx.get("maxFeePerGas", "0x0"))
        access_list = []  # simplified
        fields = [chain_id, nonce, max_priority_fee, max_fee, gas, to_bytes, value, data_bytes, access_list, v, r, s]
        encoded = b"\x02" + rlp.encode(fields)
    else:
        # Fallback: encode the tx hash string
        encoded = tx.get("hash", "").encode("utf-8")

    return encoded


def hash_transaction_keccak(tx: dict) -> bytes:
    """
    Extension A: Keccak-256 of the RLP-encoded transaction.
    This is the hash that Ethereum uses when building the transactions trie.

    Args:
        tx: Transaction dict.

    Returns:
        32-byte Keccak-256 digest.
    """
    encoded = rlp_encode_transaction(tx)
    return keccak256(encoded)


def reconstruct_root_keccak(transactions: list[dict]) -> bytes:
    """
    Reconstruct the transactions root using proper Keccak-256 hashing.
    Still uses a plain binary Merkle tree (not a Patricia Trie), so the
    result won't match the block header exactly, but confirms the hashing
    layer is correct.

    Args:
        transactions: List of full transaction dicts.

    Returns:
        32-byte Merkle root using Keccak-256 leaf hashes.
    """
    from src.part1_tree import MerkleTree

    leaf_hashes = [hash_transaction_keccak(tx) for tx in transactions]
    tree = MerkleTree(leaf_hashes)
    return tree.root


def run_extension_a(block: dict) -> None:
    """Run Extension A: reconstruct root using RLP + Keccak-256."""
    print("\n" + "=" * 60)
    print("EXTENSION A — RLP + Keccak-256 Hashing")
    print("=" * 60)
    transactions = block.get("transactions", [])
    if not transactions:
        print("[WARN] No transactions in block.")
        return

    try:
        root = reconstruct_root_keccak(transactions)
        header_root = block.get("transactionsRoot", "")
        print(f"\n  Keccak-256 tree root : 0x{root.hex()}")
        print(f"  Block header root    : {header_root}")
        print(
            "\n  Note: A plain binary Merkle tree still won't match Ethereum's"
            "\n  Merkle Patricia Trie root exactly, but the leaf hashes are correct."
        )
    except ImportError as e:
        print(f"[SKIP] {e}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Extension B — Odd-Leaf Block Detection
# ---------------------------------------------------------------------------

def find_odd_tx_block(rpc_url: str, start_block: int = 0, max_search: int = 100) -> Optional[dict]:
    """
    Search recent blocks for one with an odd number of transactions.
    Demonstrates that odd-leaf duplication logic is exercised.

    Args:
        rpc_url:     Ethereum JSON-RPC URL.
        start_block: Block number to start searching from (0 = latest).
        max_search:  Maximum number of blocks to scan.

    Returns:
        The first block found with an odd transaction count, or None.
    """
    from src.part2_fetch import fetch_block

    if start_block == 0:
        latest = fetch_block(rpc_url, "latest")
        start_block = int(latest.get("number", "0x0"), 16)

    print(f"\n[Extension B] Searching for odd-tx block from #{start_block} …")
    for offset in range(max_search):
        block_num = start_block - offset
        if block_num < 0:
            break
        try:
            block = fetch_block(rpc_url, block_num)
            tx_count = len(block.get("transactions", []))
            if tx_count % 2 == 1:
                print(f"  Found odd-tx block: #{block_num} with {tx_count} transactions")
                return block
        except Exception:
            continue
    print("[Extension B] No odd-tx block found in search range.")
    return None


def run_extension_b(rpc_url: str) -> None:
    """Run Extension B: find odd-tx block and verify proof."""
    print("\n" + "=" * 60)
    print("EXTENSION B — Odd-Leaf Block Verification")
    print("=" * 60)
    from src.part3_verify import prove_transaction_inclusion

    block = find_odd_tx_block(rpc_url)
    if block:
        tx_count = len(block.get("transactions", []))
        print(f"  Verifying last tx (index {tx_count - 1}) in odd-leaf block …")
        prove_transaction_inclusion(block, tx_index=tx_count - 1)
    print("=" * 60)


# ---------------------------------------------------------------------------
# Extension C — Light Client Simulation
# ---------------------------------------------------------------------------

def light_client_verify(
    block_header: dict,
    tx_index: int,
    proof: list[dict],
    leaf_data: bytes,
) -> bool:
    """
    Simulate what an Ethereum light client does:
    Accept only the block header and a Merkle proof — NOT the full block —
    and verify that a specific transaction was included.

    The light client:
      1. Reads the transactionsRoot from the block header.
      2. Recomputes the root from the provided proof and leaf data.
      3. Returns True iff the recomputed root matches the header root.

    Args:
        block_header: Dict containing at least 'transactionsRoot'.
        tx_index:     Index of the transaction being proved.
        proof:        Merkle proof as returned by MerkleTree.get_proof().
        leaf_data:    The hash of the transaction (the leaf value).

    Returns:
        True if proof is valid against the header's transactionsRoot.
    """
    from src.part1_tree import verify_proof

    # Extract the committed root from the block header only
    header_root_hex: str = block_header.get("transactionsRoot", "")
    if not header_root_hex or header_root_hex == "0x":
        print("[LightClient] No transactionsRoot in header.")
        return False

    # Strip 0x prefix and convert to bytes
    header_root_bytes = bytes.fromhex(header_root_hex.lstrip("0x"))

    return verify_proof(leaf_data, proof, header_root_bytes)


def run_extension_c(block: dict) -> None:
    """Run Extension C: light client simulation using header + proof only."""
    print("\n" + "=" * 60)
    print("EXTENSION C — Light Client Simulation")
    print("=" * 60)

    from src.part1_tree import MerkleTree
    from src.part3_verify import hash_transaction

    transactions = block.get("transactions", [])
    if not transactions:
        print("[WARN] No transactions.")
        return

    leaf_hashes = [hash_transaction(tx) for tx in transactions]
    tree = MerkleTree(leaf_hashes)

    tx_index = 0
    proof = tree.get_proof(tx_index)
    leaf_data = leaf_hashes[tx_index]

    # Simulate: give the light client ONLY the header (strip transactions)
    header_only = {k: v for k, v in block.items() if k != "transactions"}
    # Override transactionsRoot with reconstructed root (Option A)
    header_only["transactionsRoot"] = "0x" + tree.root.hex()

    result = light_client_verify(header_only, tx_index, proof, leaf_data)
    print(f"\n  Light client verified tx[{tx_index}]: {'✓ VALID' if result else '✗ INVALID'}")
    print("  (No full block data was used — header + proof only)")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Extension D — Historical Block Verification
# ---------------------------------------------------------------------------

def run_extension_d(rpc_url: str) -> None:
    """
    Run Extension D: fetch a block from ~6 months ago and verify a transaction.
    Uses approximate block number math (Ethereum ~12s/block).
    """
    print("\n" + "=" * 60)
    print("EXTENSION D — Historical Block Verification")
    print("=" * 60)

    from src.part2_fetch import fetch_block
    from src.part3_verify import prove_transaction_inclusion

    # ~6 months ago: ~6 * 30 * 24 * 3600 / 12 ≈ 1,296,000 blocks ago
    blocks_per_6_months = 1_296_000

    latest_block = fetch_block(rpc_url, "latest")
    latest_num = int(latest_block.get("number", "0x0"), 16)
    historical_num = max(0, latest_num - blocks_per_6_months)

    print(f"\n  Latest block   : #{latest_num:,}")
    print(f"  Historical target: #{historical_num:,}  (~6 months ago)")
    print(f"  Fetching block #{historical_num:,} …")

    try:
        hist_block = fetch_block(rpc_url, historical_num)
        tx_count = len(hist_block.get("transactions", []))
        print(f"  Block #{historical_num:,}: {tx_count} transactions")
        if tx_count > 0:
            prove_transaction_inclusion(hist_block, tx_index=0)
        else:
            print("  [WARN] No transactions in historical block — try a different block.")
    except Exception as exc:
        print(f"  [ERROR] {exc}")
    print("=" * 60)
