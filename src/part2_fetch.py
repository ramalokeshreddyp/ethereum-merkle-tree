"""
Part 2 — Fetch Real Ethereum Data
===================================
Interacts with an Ethereum JSON-RPC endpoint to fetch:
  - Full blocks (with transaction objects)
  - Block header fields including transactionsRoot
  - Optional: transaction inclusion proofs (eth_getProof)

Requires an RPC endpoint URL (Alchemy / Infura) in the RPC_URL env var
or passed directly to the functions.
"""

import os
import json
import requests
from typing import Any


# ---------------------------------------------------------------------------
# JSON-RPC helper
# ---------------------------------------------------------------------------

def _rpc_call(rpc_url: str, method: str, params: list) -> Any:
    """
    Execute a single JSON-RPC 2.0 call and return the 'result' field.

    Raises:
        requests.HTTPError: on non-2xx HTTP responses.
        ValueError: if the RPC response contains an 'error' field.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(rpc_url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    if "error" in data:
        raise ValueError(
            f"RPC error [{data['error'].get('code')}]: {data['error'].get('message')}"
        )
    return data.get("result")


# ---------------------------------------------------------------------------
# Block fetching
# ---------------------------------------------------------------------------

def fetch_block(rpc_url: str, block_number: int | str = "latest") -> dict:
    """
    Fetch a full Ethereum block (with full transaction objects) from a
    JSON-RPC endpoint using eth_getBlockByNumber.

    Args:
        rpc_url:      The Ethereum node RPC URL.
        block_number: Integer block number or "latest" / "earliest" / "pending".

    Returns:
        The raw block dict including 'transactionsRoot' and 'transactions'.

    Raises:
        ValueError: if the block is not found or RPC returns an error.
    """
    # Convert integer to hex string as required by the JSON-RPC spec
    if isinstance(block_number, int):
        block_tag = hex(block_number)
    else:
        block_tag = block_number  # "latest", "earliest", etc.

    result = _rpc_call(rpc_url, "eth_getBlockByNumber", [block_tag, True])

    if result is None:
        raise ValueError(
            f"Block {block_number!r} not found on the network."
        )
    return result


def fetch_transaction_by_hash(rpc_url: str, tx_hash: str) -> dict:
    """
    Fetch a single transaction by its hash.

    Args:
        rpc_url:  The Ethereum node RPC URL.
        tx_hash:  Transaction hash (0x-prefixed hex string).

    Returns:
        Transaction dict or None if not found.
    """
    result = _rpc_call(rpc_url, "eth_getTransactionByHash", [tx_hash])
    if result is None:
        raise ValueError(f"Transaction {tx_hash!r} not found.")
    return result


def fetch_transaction_proof(rpc_url: str, tx_hash: str) -> dict | None:
    """
    Attempt to fetch an eth_getProof for a transaction's inclusion.
    Note: eth_getProof is designed for storage/account proofs; transaction
    trie proofs require eth_getTransactionByHash + manual trie reconstruction.
    This function returns the transaction receipt for reference.

    Args:
        rpc_url: The Ethereum node RPC URL.
        tx_hash: Transaction hash (0x-prefixed hex string).

    Returns:
        Transaction receipt dict or None.
    """
    try:
        result = _rpc_call(rpc_url, "eth_getTransactionReceipt", [tx_hash])
        return result
    except Exception as exc:
        print(f"[WARN] Could not fetch transaction proof: {exc}")
        return None


# ---------------------------------------------------------------------------
# Block inspector
# ---------------------------------------------------------------------------

def inspect_block(block: dict) -> None:
    """
    Print key information from a fetched Ethereum block.

    Outputs:
        - Block number (decimal)
        - Block timestamp (Unix epoch)
        - Miner / fee recipient
        - Transaction count
        - transactionsRoot (the Merkle root we will reconstruct)
        - Gas used / gas limit
        - First 5 transaction hashes (for reference)
    """
    print("\n" + "=" * 60)
    print("PART 2 — Ethereum Block Inspector")
    print("=" * 60)

    block_number_hex: str = block.get("number", "0x0")
    block_number = int(block_number_hex, 16)

    timestamp_hex: str = block.get("timestamp", "0x0")
    timestamp = int(timestamp_hex, 16)

    gas_used_hex: str = block.get("gasUsed", "0x0")
    gas_limit_hex: str = block.get("gasLimit", "0x0")
    gas_used = int(gas_used_hex, 16)
    gas_limit = int(gas_limit_hex, 16)

    transactions: list = block.get("transactions", [])
    tx_root: str = block.get("transactionsRoot", "N/A")
    miner: str = block.get("miner", block.get("feeRecipient", "N/A"))

    print(f"\n  Block Number       : {block_number:,}  ({block_number_hex})")
    print(f"  Timestamp (UTC)    : {timestamp}  (epoch)")
    print(f"  Miner / Validator  : {miner}")
    print(f"  Transaction Count  : {len(transactions)}")
    print(f"  Gas Used           : {gas_used:,} / {gas_limit:,}")
    print(f"\n  transactionsRoot   : {tx_root}")
    print(f"  (This is what we will reconstruct from raw transactions)")

    if transactions:
        print(f"\n  First 5 tx hashes:")
        for tx in transactions[:5]:
            tx_hash = tx.get("hash", "N/A") if isinstance(tx, dict) else tx
            print(f"    {tx_hash}")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def run_part2(rpc_url: str | None = None) -> dict:
    """
    Fetch a recent Ethereum block, inspect it, and return the block dict.

    Args:
        rpc_url: Ethereum JSON-RPC URL. Falls back to RPC_URL env var.

    Returns:
        The fetched block dict.
    """
    if rpc_url is None:
        rpc_url = os.environ.get("RPC_URL", "")
    if not rpc_url:
        raise EnvironmentError(
            "No RPC URL provided. Set the RPC_URL environment variable "
            "or pass rpc_url to this function."
        )

    print("\n[INFO] Fetching latest Ethereum block …")
    block = fetch_block(rpc_url, "latest")
    inspect_block(block)
    return block


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_part2()
