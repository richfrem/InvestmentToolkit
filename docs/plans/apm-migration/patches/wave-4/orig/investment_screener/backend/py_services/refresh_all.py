"""
refresh_all.py — Master portfolio refresh orchestrator.

Called after any event that changes portfolio state:
  - TV portfolio sync     (fetch_broker_data.py --snapshot)
  - Trade execution       (place_order.py after fill)
  - Target weight changes (update_targets.py --write)
  - Thesis updates        (update_thesis.py)
  - Role sync             (sync_portfolio_roles.py)

Steps run in order (each step feeds the next):
  1. sync_portfolio_roles  — enforce role field consistency from actual shares

The thesis pages need no regeneration: their positions tables are live in the web app and
their current-developments notes are written by thesis_currency.py (see
references/thesis-page-currency.md). The old frozen blueprint and per-thesis position blocks
(generate_portfolio_blueprint.py, generate_sub_strategy_blocks.py) are no longer run.

With --publish (the closing step of every review workflow — /strategic-review,
/daily, /weekly-review, target calibration, valuation refreshes) it also brings
the web app's pages in line with what the session decided:
  3. generate_review_json --yes  — today's review JSON (Portfolio page)
  4. daily_brief --skip-ta       — republish the brief (Daily Brief page)
  5. verify_refresh              — consistency check across all of the above

Usage:
  python3 plugins/portfolio-advisor/scripts/refresh_all.py
  python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish
  python3 plugins/portfolio-advisor/scripts/refresh_all.py --skip-roles

Layer: Plugin / portfolio-advisor / Orchestrator

Key Input Dependencies:
    None directly (runs the steps listed above as subprocesses; they read domain_model.sqlite)
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS   = Path(__file__).parent

# Fallback to plugins directory if executed from backend py_services
if "py_services" in SCRIPTS.parts:
    plugin_scripts = REPO_ROOT / "plugins" / "portfolio-advisor" / "scripts"
    if plugin_scripts.exists():
        SCRIPTS = plugin_scripts

SYNC_ROLES  = SCRIPTS / "sync_portfolio_roles.py"
REVIEW_JSON = SCRIPTS / "generate_review_json.py"
DAILY_BRIEF = SCRIPTS / "daily_brief.py"
VERIFY      = SCRIPTS / "verify_refresh.py"

# (label, script, args) — run only with publish=True, after the thesis steps.
PUBLISH_STEPS = [
    ("Regenerating today's review JSON", REVIEW_JSON, ["--yes"]),
    ("Republishing the daily brief", DAILY_BRIEF, ["--skip-ta"]),
    ("Verifying refresh consistency", VERIFY, []),
]


def _run(script: Path, extra_args: list[str] | None = None) -> int:
    """Run a script as a subprocess. Returns exit code."""
    cmd = [sys.executable, str(script)] + (extra_args or [])
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    return result.returncode


def run_refresh(skip_roles: bool = False, publish: bool = False) -> int:
    """Execute the full refresh pipeline. Returns 0 on success, non-zero on any failure.

    Args:
        skip_roles:     Skip sync_portfolio_roles step (use when roles were just written).
        publish:        Also regenerate the review JSON, republish the daily brief and
                        run verify_refresh — the closing step of a review session.
                        Off by default so the frequent callers (broker sync,
                        update_targets, update_thesis) stay fast.

    Returns:
        Highest non-zero exit code seen, or 0 if all steps succeeded.
    """
    worst = 0

    if not skip_roles:
        print("── Syncing portfolio roles ───────────────────────────────────")
        code = _run(SYNC_ROLES)
        if code != 0:
            print(f"⚠ sync_portfolio_roles exited {code}", file=sys.stderr)
            worst = max(worst, code)

    if publish:
        for label, script, extra_args in PUBLISH_STEPS:
            print(f"── Publish: {label} ─────")
            code = _run(script, extra_args)
            if code != 0:
                print(f"⚠ {script.name} exited {code}", file=sys.stderr)
                worst = max(worst, code)

    if worst == 0:
        print("✓ refresh_all complete — roles synced.")
    else:
        print(f"⚠ refresh_all finished with errors (exit={worst}).", file=sys.stderr)
    return worst


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync role fields (and, with --publish, republish the review and brief) after any portfolio event"
    )
    parser.add_argument("--skip-roles",     action="store_true", help="Skip role sync step")
    parser.add_argument("--publish", action="store_true",
                        help="Also regenerate the review JSON, republish the daily brief and run verify_refresh")
    args = parser.parse_args()
    sys.exit(run_refresh(skip_roles=args.skip_roles, publish=args.publish))


if __name__ == "__main__":
    main()
