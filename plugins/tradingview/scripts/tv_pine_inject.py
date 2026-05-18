#!/usr/bin/env python3
"""
tv_pine_inject.py — Inject Pine Script into TradingView via CDP.

Usage:
    python3 tv_pine_inject.py --file path/to/script.pine
    cat script.pine | python3 tv_pine_inject.py

Args:
    --file, -f: Path to a .pine file (relative or absolute).

Returns:
    JSON to stdout: {"success": true} or {"success": false, "error": "..."}
"""

import os
import sys
import argparse
import json

# Resolve imports even when executed via symlink from a skill folder
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from tv_client import tv_call, validate_cdp_installation


def _preflight_check(content: str) -> str | None:
    """Return an error string if the script has obvious structural problems, else None."""
    import re
    lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("//")]
    if not lines:
        return "Script has no non-comment content"
    # Must have a version declaration
    if not any(l.startswith("//@version=") for l in content.splitlines()):
        return "Missing //@version= declaration (e.g. //@version=6)"
    # Must declare indicator or strategy
    if not any(re.match(r"^(indicator|strategy|library)\s*\(", l) for l in lines):
        return "Missing indicator(), strategy(), or library() declaration"
    return None


def main():
    parser = argparse.ArgumentParser(description="Inject Pine Script via CDP")
    parser.add_argument("--file", "-f", help="Path to Pine Script file to inject")
    args = parser.parse_args()

    status = validate_cdp_installation()
    if not status["installed"]:
        for issue in status["issues"]:
            print(f"ERROR: {issue}", file=sys.stderr)
        sys.exit(1)

    if args.file:
        # Read content here (Python's cwd is correct), then pass via --content so
        # Node doesn't need to resolve the path from its own cwd (tradingview-cdp/).
        abs_file = os.path.abspath(args.file)
        if not os.path.isfile(abs_file):
            print(json.dumps({"success": False, "error": f"File not found: {abs_file}"}))
            sys.exit(1)
        with open(abs_file, "r") as fh:
            script_content = fh.read()
    elif not sys.stdin.isatty():
        script_content = sys.stdin.read()
    else:
        print("ERROR: Provide --file or pipe content via STDIN.", file=sys.stderr)
        sys.exit(1)

    if not script_content.strip():
        print(json.dumps({"success": False, "error": "Script content is empty"}))
        sys.exit(1)

    # Fast local pre-flight: catch obvious Pine Script structure errors before
    # hitting the TV CDP round-trip.
    preflight_error = _preflight_check(script_content)
    if preflight_error:
        print(json.dumps({"success": False, "error": f"Pine Script pre-flight: {preflight_error}"}))
        sys.exit(1)

    try:
        result = tv_call("pine", "inject", "--content", script_content)
        print(json.dumps(result, indent=2))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
