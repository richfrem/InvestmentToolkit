"""seed_real_accounts.py - Seed the three real broker accounts into the account table.

Purpose:
    One-time-per-wave seed: the three real accounts (AGENTS.md account structure).
    TFSA is primary (larger); RRSP mirrors at ~1/3 share count; CASH is the third
    real broker sub-account (per explicit user decision, Wave 3 scope extension —
    previously excluded, now seeded like TFSA/RRSP). All three are real, named
    accounts — not free-text strings — so producers/consumers resolve against a
    stable account_id instead of parsing account names out of the retired
    portfolio.json structure ad hoc.

Layer:
    Backend / Python Services / Domain Model

Usage Examples:
    from domain_model.seed_real_accounts import seed_real_accounts
    seed_real_accounts(conn)  # idempotent; safe to call on every migration run

Key Functions (Index):
    - seed_real_accounts(): upsert the TFSA, RRSP and CASH account rows

Key Input Dependencies:
    - An open domain_model.sqlite connection (see db_client.initialize_db)
    - domain_model/account_repository.py (upsert_account)

Key Output Dependencies:
    - account table rows (account_id, account_name, account_type, base_currency)
"""

import sqlite3

from .account_repository import upsert_account


def seed_real_accounts(conn: sqlite3.Connection) -> None:
    """Upsert the TFSA, RRSP and CASH accounts (CAD base currency). Idempotent."""
    upsert_account(conn, "TFSA", "TFSA", "TFSA", base_currency="CAD")
    upsert_account(conn, "RRSP", "RRSP", "RRSP", base_currency="CAD")
    upsert_account(conn, "CASH", "CASH", "CASH", base_currency="CAD")
