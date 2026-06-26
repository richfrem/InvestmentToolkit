"""Sync role field in target-portfolio.json from actual portfolio.json positions.

Rule:
  shares == 0  → role must be: watchlist | monitor | initiate | avoid
  shares  > 0  → role must be: trim | accumulate | exit

Run after every TV sync or manually to keep roles consistent.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PORTFOLIO_JSON = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
TARGET_JSON = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from portfolio_io import load_portfolio_state  # noqa: E402
from ticker_aliases import normalize_ticker    # noqa: E402

VALID_NOT_HELD = {"watchlist", "monitor", "initiate", "avoid"}
VALID_HELD = {"trim", "accumulate", "exit"}


def load_actual_shares(portfolio_path: Path) -> dict[str, float]:
    """Read portfolio.json and return {ticker: shares} for all held positions.

    Delegates to portfolio_io.load_portfolio_state — single source of truth.
    """
    return load_portfolio_state(portfolio_path)["shares"]


def _first_action_word(text: str) -> str:
    words = text.upper().split()
    return words[0] if words else ""


def determine_role(holding: dict, actual_shares: float) -> str:
    """Determine the correct action-role for a holding."""
    target_weight = float(holding.get("targetWeight") or 0)
    thesis = (holding.get("thesisForInclusion") or "").upper()
    agent = (holding.get("agentRationale") or "").upper()
    standing_type = (holding.get("standingDecision") or {}).get("type", "").upper()

    if actual_shares == 0:
        # Not held
        if target_weight > 0:
            return "initiate"
        # Explicit exit/avoid signals
        if thesis.startswith("EXIT:") or "TARGET 0%: EXIT" in agent or "EXIT." in agent[:20]:
            return "avoid"
        return "watchlist"

    # Held position
    if target_weight == 0:
        return "exit"

    # SA_LP_EXIT_OVERRIDE means "don't add, trim toward target" — not a full exit
    if standing_type == "SA_LP_EXIT_OVERRIDE":
        return "trim"

    # Other explicit trim signals in standing decision
    if any(kw in standing_type for kw in ("TRIM", "REDUCE")):
        return "trim"

    # Parse first action word from agentRationale
    first = _first_action_word(agent)
    if first in ("TRIM", "REDUCE"):
        return "trim"
    if first in ("EXIT", "SELL"):
        return "exit"
    if first in ("ACCUMULATE", "BUY", "INITIATE"):
        return "accumulate"
    if first in ("CLOSED",):
        return "exit"  # stale entry — mark for cleanup

    # Default: held with positive target → accumulate
    return "accumulate"


def sync_roles(dry_run: bool = False) -> None:
    actual = load_actual_shares(PORTFOLIO_JSON)
    tp = json.loads(TARGET_JSON.read_text())

    # Remove PSU.U.TO ghost alias — broker dot-notation duplicate of PSU-U.TO
    before = len(tp.get("holdings", []))
    tp["holdings"] = [h for h in tp.get("holdings", []) if h.get("ticker") != "PSU.U.TO"]
    removed = before - len(tp["holdings"])
    if removed:
        print(f"  Removed {removed} ghost alias entry (PSU.U.TO → PSU-U.TO canonical).")

    changed = 0
    violations: list[str] = []

    for h in tp.get("holdings", []):
        ticker = h.get("ticker", "")
        ticker_canonical = normalize_ticker(ticker)
        actual_shares = actual.get(ticker_canonical, actual.get(ticker, 0))
        old_role = h.get("role", "")
        new_role = determine_role(h, actual_shares)

        # Only update if the current role is in the wrong bucket
        if actual_shares == 0 and old_role not in VALID_NOT_HELD:
            violations.append(f"  {ticker:<10} shares=0  role={old_role!r:15} → {new_role!r}")
            if not dry_run:
                h["role"] = new_role
            changed += 1
        elif actual_shares > 0 and old_role not in VALID_HELD:
            violations.append(f"  {ticker:<10} shares={actual_shares:<6.1f} role={old_role!r:15} → {new_role!r}")
            if not dry_run:
                h["role"] = new_role
            changed += 1

    if violations:
        print(f"{'DRY RUN — ' if dry_run else ''}Role violations fixed ({changed}):")
        for v in violations:
            print(v)
    else:
        print("✓ All roles are consistent with actual positions.")

    if not dry_run and changed:
        tp["updatedAt"] = "2026-06-21T18:30:00Z"
        TARGET_JSON.write_text(json.dumps(tp, indent=2, ensure_ascii=False))
        print(f"\n✓ target-portfolio.json updated ({changed} roles fixed).")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    sync_roles(dry_run=dry_run)
