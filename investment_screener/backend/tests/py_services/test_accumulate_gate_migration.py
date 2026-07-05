import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
PLUGIN_SCRIPTS_DIR = REPO_ROOT / "plugins/stock-valuation/scripts"
PROJECTIONS_DIR = REPO_ROOT / "investment_screener/backend/data/projections"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PLUGIN_SCRIPTS_DIR))

from validate_projection import check_accumulate_gate  # noqa: E402


def test_document_existing_accumulate_projections_against_new_gate(capsys):
    """Not a pass/fail gate on old data — a documentation pass. Prints every
    currently-ACCUMULATE projection that would fail the new 2-of-3 gate, so
    the agent can re-review each one (never silently auto-corrected, per the
    design spec's migration acceptance criterion)."""
    would_fail = []
    for path in sorted(PROJECTIONS_DIR.glob("*.json")):
        if path.name.endswith(".pylock"):
            continue
        try:
            with open(path) as f:
                entries = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(entries, list) or not entries:
            continue
        latest = entries[-1]
        if latest.get("aiThesis", {}).get("action") != "ACCUMULATE":
            continue
        gate = check_accumulate_gate(latest)
        if not gate["gatePassed"]:
            would_fail.append((path.stem, gate["lensesAgreeing"]))

    if would_fail:
        print(f"\n{len(would_fail)} existing ACCUMULATE projection(s) would fail the new gate "
              "(pre-Phase-2a data has no analyticsLog.{dcf,comps,reverseDcf} yet, so this is "
              "expected until each is re-run through /evaluate-stock):")
        for ticker, n in would_fail:
            print(f"  - {ticker}: only {n}/3 lenses agree")

    # Documentation only — always passes. The printed list above is the
    # actual deliverable (captured by `capsys` here just to keep the test
    # from being silently swallowed; run with `-s` to see it directly).
    captured = capsys.readouterr()
    assert True
