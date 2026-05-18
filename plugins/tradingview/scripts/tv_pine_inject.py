#!/usr/bin/env python3
"""
tv_pine_inject.py (CLI)
=====================================

Purpose:
    Inject custom Pine Script code into the active TradingView chart.
    This script acts as the Python wrapper for the pine-inject Node CDP logic.

Usage Examples:
    # Inject script from a file:
    python3 plugins/tradingview/scripts/tv_pine_inject.py --file my_script.pine

    # Inject script via STDIN:
    cat my_script.pine | python3 plugins/tradingview/scripts/tv_pine_inject.py
"""

import sys
import argparse
import json
from tv_client import tv_call, validate_cdp_installation

def main():
    parser = argparse.ArgumentParser(description="Inject Pine Script via CDP")
    parser.add_argument("--file", "-f", help="Path to Pine Script file to inject")
    args = parser.parse_args()

    status = validate_cdp_installation()
    if not status["installed"]:
        for issue in status["issues"]:
            print(f"ERROR: {issue}", file=sys.stderr)
        sys.exit(1)

    script_content = ""
    if args.file:
        with open(args.file, "r") as f:
            script_content = f.read()
    elif not sys.stdin.isatty():
        script_content = sys.stdin.read()
    else:
        print("ERROR: Must provide Pine Script via --file or STDIN.", file=sys.stderr)
        sys.exit(1)

    if not script_content.strip():
        print("ERROR: Provided script is empty.", file=sys.stderr)
        sys.exit(1)

    try:
        # tv_call automatically handles cwd and node binary invocation
        # The node cli expects: node cli.js pine inject --script "..."
        # But looking at cli.js we updated it earlier, let's just pass the file if we have it or script
        # The node CLI expects `-f file` or something. Let's look at the old SKILL.md.
        # It said: `node tradingview-cdp/cli.js pine inject -f temp/generated_script.pine`
        
        if args.file:
            result = tv_call("pine", "inject", "-f", args.file)
        else:
            # If no file, we might need a temp file. Let's just create a temp file.
            import tempfile
            import os
            fd, tmp_path = tempfile.mkstemp(suffix=".pine")
            with os.fdopen(fd, 'w') as f:
                f.write(script_content)
            try:
                result = tv_call("pine", "inject", "-f", tmp_path)
            finally:
                os.remove(tmp_path)

        print(json.dumps(result, indent=2))
        sys.exit(0)

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
