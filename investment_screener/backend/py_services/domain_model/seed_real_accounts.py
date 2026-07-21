"""One-time-per-wave seed: the three real accounts (CLAUDE.md account structure).

TFSA is primary (larger); RRSP mirrors at ~1/3 share count; CASH is the third
real broker sub-account (per explicit user decision, Wave 3 scope extension —
previously excluded, now seeded like TFSA/RRSP). All three are real, named
accounts — not free-text strings — so Wave 3's producers/consumers can resolve
against a stable account_id instead of parsing account names out of
portfolio.json's structure ad hoc.
"""

import sqlite3

from .account_repository import upsert_account


def seed_real_accounts(conn: sqlite3.Connection) -> None:
    upsert_account(conn, "TFSA", "TFSA", "TFSA", base_currency="CAD")
    upsert_account(conn, "RRSP", "RRSP", "RRSP", base_currency="CAD")
    upsert_account(conn, "CASH", "CASH", "CASH", base_currency="CAD")
