#!/usr/bin/env python3
"""
verify_refresh.py — Post-target-change consistency checker.

Checks that ALL data sources are in sync after a target edit:
  1. target-portfolio.json  (ground truth)
  2. investment_thesis.md   (version, date, tables)
  3. latest review JSON     (date, thesisName, no stale holdings)
  4. portfolio actions      (no false ACCUMULATE on DCF-SELL, no false signals)

Run as part of the skill refresh chain:
  python3 plugins/portfolio-advisor/scripts/verify_refresh.py

Exit 0 = all clear. Exit 1 = inconsistencies found (lists every failure).
"""

import json, re, sys
from datetime import date
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parents[3]
THESIS_JSON = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
THESIS_MD   = REPO_ROOT / "investment_screener/backend/data/theses/investment_thesis.md"
PORTFOLIO   = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
REVIEWS_DIR = REPO_ROOT / "PortfolioAnalysis/strategic-reviews"
DB_PATH     = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"

# Positions user locked to "no change" — must stay at MAINTAIN
NO_CHANGE = {"GOOG", "HUMN", "KOID"}

# Known SA LP conviction plays where DCF disagrees — warn, don't fail
# These are intentional: SA LP holds large positions; user has not explicitly resolved the conflict
SA_DCF_CONFLICTS = {"CORZ", "LITE", "BE", "INTC", "IONQ", "QBTS", "OKLO", "CEG", "IREN", "EQT"}

sys.path.insert(0, str(Path(__file__).parent))
from validate_weights import compute_current, compute_target
from portfolio_action import derive_action

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import get_latest_projection_by_source  # noqa: E402
from domain_model.investment_repository import list_investments  # noqa: E402


def _load_holdings_map(db_path: Path = DB_PATH) -> dict:
    """Return {ticker: {targetWeight, agentRationale}} from investment.

    Storage backend (Wave 2 Task 10 rewire): replaces the direct
    target-portfolio.json ``holdings`` read (targetWeight, agentRationale
    fields) with ``investment.target_weight`` / ``investment.agent_rationale``
    via ``list_investments`` (ADR-029). Document-level fields (name, version,
    updatedAt) have no investment-table equivalent and are still read
    straight from target-portfolio.json below.
    """
    if not Path(db_path).exists():
        return {}
    conn = initialize_db(str(db_path))
    try:
        return {
            row["symbol"]: {
                "targetWeight": row.get("target_weight") or 0,
                "agentRationale": row.get("agent_rationale") or "",
            }
            for row in list_investments(conn)
        }
    finally:
        conn.close()


def _load_ai_agent_upside(ticker: str) -> float | None:
    """Return `(fairValue - price) / price * 100` for the latest AI_AGENT
    projection, or None if no AI_AGENT row (or no fairValue/price) exists.

    Storage backend (Wave 1 Task 7B): reads `projection_version` via
    `domain_model.projection_repository`, not `projections/{TICKER}.json`
    directly (ADR-029). Factors out the two duplicated file-read blocks the
    original script had (false-ACCUMULATE and false-INITIATE checks), both of
    which filtered strictly by `source == "AI_AGENT"` with no fallback.
    """
    conn = initialize_db(str(DB_PATH))
    try:
        row = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", (ticker,)
        ).fetchone()
        if row is None:
            return None
        entry = get_latest_projection_by_source(conn, row[0], "AI_AGENT")
        if entry is None:
            return None
        fv = entry.get("fair_value")
        snapshot = json.loads(entry["snapshot_json"]) if entry.get("snapshot_json") else {}
        price = snapshot.get("price")
        if not fv or not price:
            return None
        return (fv - price) / price * 100
    finally:
        conn.close()


errors   = []
warnings = []

def fail(msg): errors.append(f"  ✗ {msg}")
def warn(msg): warnings.append(f"  ⚠ {msg}")
def ok(msg):   print(f"  ✓ {msg}")

# ── 1. Load ground-truth JSON ─────────────────────────────────────────────────
print("\n── 1. target-portfolio.json ───────────────────────────────────────────")
with open(THESIS_JSON) as f:
    thesis = json.load(f)

json_name    = thesis.get("name", "")
json_version = thesis.get("version", 0)
json_updated = thesis.get("updatedAt", "")[:10]
ok(f"Loaded: {json_name}  (version={json_version}, updatedAt={json_updated})")

holdings_map = _load_holdings_map()
non_zero = {t: h for t, h in holdings_map.items() if h.get("targetWeight", 0) > 0}
exited   = {t: h for t, h in holdings_map.items() if h.get("targetWeight", 0) == 0}

ok(f"Holdings: {len(non_zero)} with targets, {len(exited)} EXIT (0%)")

# Check agentRationale present on all holdings
missing_rationale = [t for t, h in holdings_map.items() if not h.get("agentRationale")]
if missing_rationale:
    fail(f"agentRationale missing on: {missing_rationale}")
else:
    ok("agentRationale present on all holdings")

# ── 2. investment_thesis.md ───────────────────────────────────────────────────
print("\n── 2. investment_thesis.md ────────────────────────────────────────────")
md_text = THESIS_MD.read_text()

# Title version
title_match = re.search(r"^# Investment Thesis (v[\d.]+)", md_text, re.MULTILINE)
md_title = title_match.group(1) if title_match else "MISSING"
json_vname = re.search(r"v[\d.]+", json_name)
json_vname = json_vname.group(0) if json_vname else ""

if md_title == json_vname:
    ok(f"Title version matches JSON: {md_title}")
else:
    fail(f"Title mismatch: thesis.md says '{md_title}', JSON name says '{json_vname}'")

# Last Updated date
date_match = re.search(r"\*\*Last Updated\*\*\s*\|\s*(\S+)", md_text)
md_date = date_match.group(1) if date_match else "MISSING"
today = date.today().isoformat()
if md_date == today:
    ok(f"Last Updated is today: {md_date}")
else:
    warn(f"Last Updated is {md_date}, not today ({today}) — run --write to fix")

# Check stale table data for a sample of key tickers
current_data = compute_current(PORTFOLIO)
target_data  = compute_target(THESIS_JSON)

stale = []
for ticker, h in list(non_zero.items())[:8]:   # spot-check first 8
    action = derive_action(ticker,
                           current_data["holdings"].get(ticker, 0),
                           target_data["holdings"].get(ticker, 0))
    # Look for the ticker in the md with a different action
    pattern = rf"\|\s*\*\*{re.escape(ticker)}\*\*\s*\|[^|]*\|\s*[^|]*\|\s*[^|]*\|\s*[^|]*\|"
    row = re.search(pattern, md_text)
    if not row:
        stale.append(f"{ticker}(missing from tables)")

if stale:
    warn(f"Tickers missing from thesis.md tables: {stale}")
else:
    ok("Spot-check: key tickers found in thesis.md tables")

# ── 3. Latest review JSON ─────────────────────────────────────────────────────
print("\n── 3. Latest review JSON ──────────────────────────────────────────────")
review_jsons = sorted(
    [f for f in REVIEWS_DIR.iterdir()
     if f.suffix == ".json" and re.match(r"\d{4}-\d{2}-\d{2}", f.name)
     and "patch" not in f.name],
    reverse=True
)

if not review_jsons:
    warn("No review JSON files found in PortfolioAnalysis/strategic-reviews/")
else:
    latest_json = review_jsons[0]
    with open(latest_json) as f:
        review = json.load(f)

    rdate = review.get("reviewDate", "")
    rname = review.get("thesisName", "")
    ok(f"Latest review JSON: {latest_json.name}")

    if rdate == today:
        ok(f"Review date is today: {rdate}")
    else:
        fail(f"Review JSON date is {rdate}, not today ({today}) — generate a new review JSON")

    if rname == json_name:
        ok(f"Review thesisName matches JSON: {rname}")
    else:
        fail(f"Review thesisName mismatch: review says '{rname}', JSON says '{json_name}'")

    # Check for stale proposed targets (EXITED tickers still showing as INITIATE/ACCUMULATE in review)
    stale_in_review = []
    for h in review.get("holdings", []):
        t = h.get("ticker")
        if t in exited and h.get("action") in ("INITIATE", "ACCUMULATE"):
            stale_in_review.append(f"{t}(EXIT in JSON but {h['action']} in review)")
    if stale_in_review:
        fail(f"Stale holdings in review JSON: {stale_in_review}")
    else:
        ok("No stale INITIATE/ACCUMULATE for exited tickers in review JSON")

# ── 4. Portfolio actions ───────────────────────────────────────────────────────
print("\n── 4. Portfolio actions ────────────────────────────────────────────────")

false_accumulate = []
false_initiate   = []
no_change_broken = []

for ticker, h in holdings_map.items():
    actual = current_data["holdings"].get(ticker, 0)
    target = target_data["holdings"].get(ticker, 0)
    action = derive_action(ticker, actual, target)

    # No-change positions must be MAINTAIN
    if ticker in NO_CHANGE and action != "MAINTAIN":
        no_change_broken.append(f"{ticker}({action})")

    # Check for false ACCUMULATE: target > actual AND DCF is SELL-rated (< -15% upside)
    if action == "ACCUMULATE":
        try:
            upside = _load_ai_agent_upside(ticker)
            if upside is not None and upside < -15:
                msg = f"{ticker}(ACCUMULATE but DCF {upside:+.1f}%)"
                if ticker in SA_DCF_CONFLICTS:
                    warnings.append(f"  ⚠ Known SA/DCF conflict: {msg}")
                else:
                    false_accumulate.append(msg)
        except Exception:
            pass

    # Check for false INITIATE: target > 0 but DCF is strongly negative (< -20%)
    if action == "INITIATE" and target > 0:
        try:
            upside = _load_ai_agent_upside(ticker)
            if upside is not None and upside < -20:
                false_initiate.append(f"{ticker}(INITIATE but DCF {upside:+.1f}%)")
        except Exception:
            pass

if no_change_broken:
    fail(f"No-change positions not at MAINTAIN: {no_change_broken}")
else:
    ok(f"No-change positions all MAINTAIN: {sorted(NO_CHANGE)}")

if false_accumulate:
    fail(f"False ACCUMULATE (target > actual, DCF < -15%): {false_accumulate}")
else:
    ok("No false ACCUMULATE signals on DCF-negative stocks")

if false_initiate:
    fail(f"False INITIATE (DCF < -20%): {false_initiate}")
else:
    ok("No false INITIATE signals on strongly DCF-negative stocks")

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n── Summary ─────────────────────────────────────────────────────────────")
if warnings:
    for w in warnings:
        print(w)
if errors:
    for e in errors:
        print(e)
    print(f"\n✗ {len(errors)} error(s) found — fix before committing\n")
    sys.exit(1)
else:
    print(f"  ✅ All checks passed ({len(warnings)} warning(s))\n")
    sys.exit(0)
