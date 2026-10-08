#!/usr/bin/env python3
"""
tv_account_coverage.py - Detect and retry incomplete account reads from TradingView.

Purpose:
    TradingView's account dropdown sometimes lists only some accounts, so a sync can
    come back with RRSP but not TFSA and look successful. This module is the single
    place that says which accounts a read must cover and re-reads until it does, so
    the position snapshot and the trade import apply the same rule.

Layer:
    Plugins / TradingView / shared read guard (pure apart from the caller's fetch)

Usage Examples:
    from tv_account_coverage import accounts_with_holdings, read_until_complete

Key Functions (Index):
    - accounts_with_holdings()  - Accounts the database says currently hold something
    - missing_accounts()        - Expected accounts absent from a read
    - read_until_complete()     - Re-read until every expected account is covered

Key Input Dependencies:
    - domain_model.sqlite account_investment rows (read only)

Key Output Dependencies:
    None
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

# Reads attempted before an incomplete result is reported to the caller.
MAX_READS = 3


def accounts_with_holdings(conn: Any) -> set[str]:
    """Accounts that currently hold at least one position or cash balance."""
    rows = conn.execute("SELECT DISTINCT account_id FROM account_investment WHERE quantity > 0;").fetchall()
    return {str(row[0]).upper() for row in rows}


def missing_accounts(expected: Iterable[str], read: Iterable[str]) -> list[str]:
    """Expected accounts that a read did not cover, sorted."""
    covered = {str(name).upper() for name in read}
    return sorted({str(name).upper() for name in expected} - covered)


def read_until_complete(fetch: Callable[[], dict], covered: Callable[[dict], Iterable[str]],
                        expected: Iterable[str], attempts: int = MAX_READS) -> tuple[dict, list[str]]:
    """Call ``fetch`` until the result covers every expected account.

    Args:
        fetch: Performs one read and returns the snapshot dict (or {"error": ...}).
        covered: Returns the account names a snapshot actually read.
        expected: Account names that must be present.
        attempts: Maximum number of reads.

    Returns:
        (snapshot, missing). ``missing`` is empty when the read is complete. When no
        read is complete the one covering the most accounts is returned; an error is
        returned only when every read failed.
    """
    expected = list(expected)
    best: dict | None = None
    best_missing: list[str] = []
    last: dict = {"error": "no read attempted"}
    for _ in range(max(1, attempts)):
        last = fetch()
        if last.get("error"):
            continue
        gaps = missing_accounts(expected, covered(last))
        if not gaps:
            return last, []
        if best is None or len(gaps) < len(best_missing):
            best, best_missing = last, gaps
    return (best, best_missing) if best is not None else (last, missing_accounts(expected, []))
