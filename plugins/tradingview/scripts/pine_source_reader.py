"""Pine Script source reader — fetches indicator source code from TradingView.

Opens the Indicators dialog, navigates to the Top popularity list (or searches
by name), clicks the { } source code button for each indicator, and saves the
Pine Script source to temp/indicator_sources/.

Usage:
    # Read a specific indicator by name
    python3 pine_source_reader.py --name "SuperTrend"

    # Read what is currently open in the Pine Editor
    python3 pine_source_reader.py --current

    # Fetch the top N indicators by popularity and save all sources
    python3 pine_source_reader.py --top 10

    # Custom output directory
    python3 pine_source_reader.py --name "WaveTrend Oscillator" --out /tmp/sources/

Exit codes: 0 success, 1 error.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
# Walk up to find InvestmentToolkit root (contains tradingview-cdp/)
_REPO_ROOT = _SCRIPT_DIR
for _ in range(6):
    if (_REPO_ROOT / "tradingview-cdp").exists():
        break
    _REPO_ROOT = _REPO_ROOT.parent

_CLI = _REPO_ROOT / "tradingview-cdp" / "cli.js"
_DEFAULT_OUT = _REPO_ROOT / "temp" / "indicator_sources"

# Top indicators to fetch when --top is used (TV popularity order as of 2026-05)
_TOP_INDICATORS = [
    "Smart Money Concepts [LuxAlgo]",
    "Squeeze Momentum Indicator [LazyBear]",
    "MacD Custom Indicator-Multiple Time Frame",
    "SuperTrend",
    "CM_Williams_Vix_Fix  Finds Market Bottoms",
    "Indicator: WaveTrend Oscillator [WT]",
    "Support and Resistance Levels with Breaks [LuxAlgo]",
    "Market Structure Break & Order Block by EmreKb",
    "UT Bot Alerts",
    "Nadaraya-Watson Envelope [LuxAlgo]",
]


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _tv_cli(subcommand: str, *args: str, timeout: int = 30) -> dict:
    """Run a tradingview-cdp CLI command and return the parsed JSON result."""
    cmd = ["node", str(_CLI)] + subcommand.split() + list(args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(_REPO_ROOT),
        )
        text = result.stdout.strip()
        if not text:
            return {"success": False, "error": result.stderr.strip() or "empty output"}
        return json.loads(text)
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"timeout after {timeout}s"}
    except json.JSONDecodeError as exc:
        return {"success": False, "error": f"JSON parse error: {exc}"}


def fetch_source(name: Optional[str]) -> dict:
    """Fetch Pine Script source for one indicator name (or current editor if name is None).

    Args:
        name: Indicator display name to search for, or None to read current editor.

    Returns:
        dict with keys: success, name, source, version, lines
    """
    if name:
        result = _tv_cli("pine sourceRead", "--name", name)
    else:
        result = _tv_cli("pine sourceRead")

    if not result.get("success"):
        return result

    source = result.get("source", "")
    version = result.get("version", "unknown")
    return {
        "success": True,
        "name": result.get("name", name or "(current)"),
        "source": source,
        "version": version,
        "lines": source.count("\n") + 1,
    }


def save_source(data: dict, out_dir: Path) -> Path:
    """Write source to <out_dir>/<safe_name>.pine and return the path.

    Args:
        data: Result dict from fetch_source().
        out_dir: Directory to write into.

    Returns:
        Path to the written file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', data["name"])[:60]
    path = out_dir / f"{safe}.pine"
    path.write_text(data["source"], encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Fetch Pine Script source code from TradingView's Indicators dialog.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--name", "-n", metavar="NAME", help="Indicator name to fetch")
    group.add_argument("--current", action="store_true", help="Read whatever is open in the Pine Editor")
    group.add_argument("--top", metavar="N", type=int, help="Fetch the top N popular indicators")
    p.add_argument("--out", "-o", metavar="DIR", default=str(_DEFAULT_OUT), help="Output directory (default: temp/indicator_sources/)")
    p.add_argument("--json", action="store_true", help="Output results as JSON array")
    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    out_dir = Path(args.out)

    targets: Sequence[Optional[str]]
    if args.current:
        targets = [None]
    elif args.name:
        targets = [args.name]
    else:
        targets = _TOP_INDICATORS[: args.top]

    results = []
    for name in targets:
        label = name or "(current editor)"
        print(f"→ Fetching: {label} ...", flush=True)
        data = fetch_source(name)
        if data["success"]:
            path = save_source(data, out_dir)
            print(f"  ✓ {data['lines']} lines  {data['version']}  → {path}")
        else:
            print(f"  ✗ {data.get('error', 'unknown error')}")
        results.append(data)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        ok = sum(1 for r in results if r.get("success"))
        print(f"\nDone: {ok}/{len(results)} indicators captured → {out_dir}")

    return 0 if all(r.get("success") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
