#!/usr/bin/env python3
"""
main.py — Ethereum Merkle Tree — Full End-to-End Runner
=========================================================
Orchestrates all three parts and optional extension challenges.

Usage:
    python main.py                        # Run all parts (requires RPC_URL)
    python main.py --part 1               # Part 1 only (no network)
    python main.py --extensions a b c d   # Run extension challenges

Environment:
    RPC_URL  — Ethereum JSON-RPC endpoint URL (required for parts 2 & 3)
"""

import argparse
import os
import sys

# Ensure stdout handles Unicode on Windows (cp1252 terminal)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv


def banner(title: str, char: str = "═", width: int = 64) -> None:
    print(f"\n{'╔' + char * (width - 2) + '╗'}")
    print(f"║  {title.ljust(width - 4)}║")
    print(f"{'╚' + char * (width - 2) + '╝'}")


def get_rpc_url() -> str:
    """Load RPC_URL from env; exit with a helpful message if missing."""
    rpc_url = os.environ.get("RPC_URL", "")
    if not rpc_url:
        print("\n[ERROR] RPC_URL environment variable is not set.")
        print("  1. Copy .env.example to .env")
        print("  2. Add your Alchemy or Infura URL as RPC_URL")
        print("  3. Re-run this script\n")
        sys.exit(1)
    return rpc_url


# ---------------------------------------------------------------------------
# Part runners
# ---------------------------------------------------------------------------

def run_part1() -> None:
    banner("PART 1 — Merkle Tree Unit Tests (Pure Python)")
    from src.part1_tree import run_part1_tests
    run_part1_tests()


def run_part2(rpc_url: str) -> dict:
    banner("PART 2 — Ethereum Block Fetcher")
    from src.part2_fetch import run_part2
    block = run_part2(rpc_url)
    return block


def run_part3(block: dict) -> None:
    banner("PART 3 — Transaction Inclusion Proof (End-to-End)")
    from src.part3_verify import run_part3
    transactions = block.get("transactions", [])
    # Pick a transaction index — default to index 0, or last if only 1 tx
    tx_index = min(0, len(transactions) - 1)
    run_part3(block, tx_index=tx_index)


def run_extensions(rpc_url: str, block: dict, extensions: list[str]) -> None:
    from src.extensions import (
        run_extension_a,
        run_extension_b,
        run_extension_c,
        run_extension_d,
    )

    ext_map = {
        "a": lambda: run_extension_a(block),
        "b": lambda: run_extension_b(rpc_url),
        "c": lambda: run_extension_c(block),
        "d": lambda: run_extension_d(rpc_url),
    }

    for ext in extensions:
        ext = ext.lower()
        if ext in ext_map:
            banner(f"EXTENSION {ext.upper()}")
            try:
                ext_map[ext]()
            except Exception as exc:
                print(f"[ERROR] Extension {ext.upper()} failed: {exc}")
        else:
            print(f"[WARN] Unknown extension: {ext!r} (valid: a, b, c, d)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ethereum Merkle Tree — Build, Verify, and Prove"
    )
    parser.add_argument(
        "--part",
        type=int,
        choices=[1, 2, 3],
        help="Run only a specific part (1=tree, 2=fetch, 3=verify). "
             "Default: runs all parts.",
    )
    parser.add_argument(
        "--block",
        type=str,
        default="latest",
        help="Block number to fetch (integer or 'latest'). Default: latest.",
    )
    parser.add_argument(
        "--tx-index",
        type=int,
        default=0,
        help="Transaction index within the block to generate a proof for. Default: 0.",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        metavar="EXT",
        help="Extension challenges to run (a, b, c, d). Example: --extensions a c",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    print("\n" + "╔" + "═" * 62 + "╗")
    print("║  🔗  Ethereum Merkle Tree Verifier                          ║")
    print("║      Building Trust Through Cryptographic Proofs           ║")
    print("╚" + "═" * 62 + "╝")

    block: dict | None = None

    # ── Part 1: Always safe to run (no network needed) ────────────────────
    if args.part is None or args.part == 1:
        run_part1()

    # ── Parts 2 & 3 require network ───────────────────────────────────────
    if args.part is None or args.part in (2, 3):
        rpc_url = get_rpc_url()

        # Resolve block number
        block_number: int | str = args.block
        if block_number != "latest":
            try:
                block_number = int(block_number)
            except ValueError:
                print(f"[ERROR] Invalid block number: {block_number!r}")
                sys.exit(1)

        if args.part is None or args.part == 2:
            block = run_part2(rpc_url)
        elif args.part == 3:
            # Need to fetch block for part 3 even if part 2 is skipped
            from src.part2_fetch import fetch_block, inspect_block
            print(f"\n[INFO] Fetching block {block_number!r} …")
            block = fetch_block(rpc_url, block_number)
            inspect_block(block)

        if block and (args.part is None or args.part == 3):
            # Override tx_index from CLI arg
            transactions = block.get("transactions", [])
            tx_index = args.tx_index
            if transactions and tx_index >= len(transactions):
                print(
                    f"[WARN] --tx-index {tx_index} exceeds tx count "
                    f"({len(transactions)}); using index 0."
                )
                tx_index = 0

            from src.part3_verify import run_part3
            run_part3(block, tx_index=tx_index)

    # ── Extension challenges ───────────────────────────────────────────────
    if args.extensions:
        rpc_url = get_rpc_url()
        if block is None:
            from src.part2_fetch import fetch_block
            block = fetch_block(rpc_url, "latest")
        run_extensions(rpc_url, block, args.extensions)

    print("\n✅  All requested sections completed successfully.\n")


if __name__ == "__main__":
    main()
