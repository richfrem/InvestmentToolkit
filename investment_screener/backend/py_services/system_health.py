#!/usr/bin/env python3
"""
system_health.py — Deterministic system integrity check.

Checks all critical system components and exits 0 if healthy, 1 if degraded.

Usage:
    python3 investment_screener/backend/py_services/system_health.py
    python3 investment_screener/backend/py_services/system_health.py --json
    python3 investment_screener/backend/py_services/system_health.py --quiet   # exit code only

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Diagnostics metrics check)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND   = REPO_ROOT / "investment_screener/backend"
DATA      = BACKEND / "data"
SCRIPTS   = REPO_ROOT / "plugins/portfolio-advisor/scripts"
RUNTIME   = REPO_ROOT / ".runtime"
TV_CDP_PORT = int(os.environ.get("TV_CDP_PORT", "9222"))

# ── individual checks ─────────────────────────────────────────────────────────

def _check_backend_build() -> dict:
    result = subprocess.run(
        ["npx", "tsc", "--noEmit"],
        capture_output=True, text=True,
        cwd=BACKEND,
    )
    ok = result.returncode == 0
    return {"status": "PASS" if ok else "FAIL", "detail": result.stderr.strip()[:300] or "clean"}

def _check_python_scripts() -> dict:
    scripts = [
        BACKEND / "py_services/place_order.py",
        BACKEND / "py_services/fetch_financials.py",
        BACKEND / "py_services/system_health.py",
        SCRIPTS / "apply_catalyst.py",
        SCRIPTS / "update_targets.py",
        SCRIPTS / "generate_review.py",
        SCRIPTS / "portfolio_action.py",
    ]
    failures = []
    for s in scripts:
        r = subprocess.run([sys.executable, "-m", "py_compile", str(s)], capture_output=True, text=True)
        if r.returncode != 0:
            failures.append(s.name)
    ok = len(failures) == 0
    return {"status": "PASS" if ok else "FAIL", "detail": f"{len(scripts)} scripts checked" + (f", failed: {failures}" if failures else "")}

def _check_portfolio_file() -> dict:
    p = DATA / "portfolio.json"
    if not p.exists():
        return {"status": "FAIL", "detail": "portfolio.json not found"}
    age_min = (time.time() - p.stat().st_mtime) / 60
    fresh = age_min <= 60
    return {
        "status": "PASS" if fresh else "WARN",
        "detail": f"age {age_min:.0f} min {'(fresh)' if fresh else '(stale — run /tv-portfolio-sync)'}",
        "age_minutes": round(age_min, 1),
    }

def _check_target_weights() -> dict:
    p = DATA / "theses/target-portfolio.json"
    if not p.exists():
        return {"status": "FAIL", "detail": "target-portfolio.json not found"}
    try:
        data = json.loads(p.read_text())
        total = sum(h.get("targetWeight", 0) or 0 for h in data.get("holdings", []))
        ok = abs(total - 100.0) <= 0.5
        return {"status": "PASS" if ok else "FAIL", "detail": f"weights sum to {total:.4f}%"}
    except Exception as e:
        return {"status": "FAIL", "detail": str(e)}

def _check_projections() -> dict:
    proj_dir = DATA / "projections"
    thesis_p = DATA / "theses/target-portfolio.json"
    if not proj_dir.exists():
        return {"status": "WARN", "detail": "projections/ directory not found"}
    try:
        thesis = json.loads(thesis_p.read_text()) if thesis_p.exists() else {}
        tickers = [h["ticker"] for h in thesis.get("holdings", []) if h.get("ticker")]
        total = len(tickers)
        has_proj = [t for t in tickers if (proj_dir / f"{t}.json").exists()]
        missing = [t for t in tickers if t not in has_proj]
        ok = len(missing) == 0
        return {
            "status": "PASS" if ok else "WARN",
            "detail": f"{len(has_proj)}/{total} holdings have projections",
            "missing": missing[:10],
        }
    except Exception as e:
        return {"status": "FAIL", "detail": str(e)}

def _check_cdp() -> dict:
    import socket
    try:
        s = socket.create_connection(("127.0.0.1", TV_CDP_PORT), timeout=0.5)
        s.close()
        # Verify it's actually TradingView, not Chrome or another CDP client
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{TV_CDP_PORT}/json/list", timeout=1) as r:
            targets = json.loads(r.read())
        tv = any("tradingview" in (t.get("url", "")).lower() for t in targets)
        return {
            "status": "PASS" if tv else "WARN",
            "detail": f"port {TV_CDP_PORT} reachable — {'TradingView target found' if tv else 'no TradingView target (Chrome? wrong port?)'}",
        }
    except Exception:
        return {"status": "WARN", "detail": f"port {TV_CDP_PORT} not reachable (TradingView not running — yfinance fallback active)"}

def _check_api_auth() -> dict:
    token_file = RUNTIME / "api-token"
    if token_file.exists():
        tok = token_file.read_text().strip()
        return {"status": "PASS", "detail": f"token file exists ({len(tok)} chars), perms {oct(token_file.stat().st_mode & 0o777)}"}
    return {"status": "WARN", "detail": "no .runtime/api-token — backend not yet started or auth disabled"}

def _check_last_audit() -> dict:
    audit_dir = REPO_ROOT / "plugins/tradingview/audit"
    if not audit_dir.exists():
        return {"status": "INFO", "detail": "no audit directory (no orders placed yet)"}
    files = sorted(audit_dir.glob("orders-*.jsonl"), reverse=True)
    if not files:
        return {"status": "INFO", "detail": "no audit log files yet"}
    try:
        lines = files[0].read_text().strip().split("\n")
        last = json.loads(lines[-1]) if lines else {}
        return {"status": "INFO", "detail": f"last event: {last.get('event','?')} at {last.get('ts','?')} ({files[0].name})"}
    except Exception as e:
        return {"status": "WARN", "detail": str(e)}

def _check_stale_locks() -> dict:
    import glob as _glob
    locks = list(BACKEND.rglob("*.pylock")) + list(BACKEND.rglob("*.lock"))
    stale = []
    for lk in locks:
        try:
            age = time.time() - lk.stat().st_mtime
            if age > 300:  # > 5 min = likely stale
                stale.append(lk.name)
        except OSError:
            pass
    return {
        "status": "PASS" if not stale else "WARN",
        "detail": "no stale locks" if not stale else f"stale locks: {stale}",
    }

# ── runner ────────────────────────────────────────────────────────────────────

CHECKS = [
    ("Backend TS build",      _check_backend_build),
    ("Python scripts syntax", _check_python_scripts),
    ("portfolio.json",        _check_portfolio_file),
    ("Target weights sum",    _check_target_weights),
    ("DCF projections",       _check_projections),
    ("CDP / TradingView",     _check_cdp),
    ("API auth token",        _check_api_auth),
    ("Last audit event",      _check_last_audit),
    ("Stale lock files",      _check_stale_locks),
]

STATUS_ICON = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌", "INFO": "ℹ️ "}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output JSON instead of human-readable")
    parser.add_argument("--quiet", action="store_true", help="No output — exit code only (0=healthy, 1=degraded)")
    args = parser.parse_args()

    results = {}
    for name, fn in CHECKS:
        try:
            results[name] = fn()
        except Exception as e:
            results[name] = {"status": "FAIL", "detail": f"check threw: {e}"}

    overall_statuses = [r["status"] for r in results.values()]
    if "FAIL" in overall_statuses:
        overall = "BLOCKED"
    elif "WARN" in overall_statuses:
        overall = "DEGRADED"
    else:
        overall = "HEALTHY"

    if args.json:
        print(json.dumps({"overall": overall, "checks": results}, indent=2))
        sys.exit(0 if overall == "HEALTHY" else 1)

    if not args.quiet:
        print("\n╔══════════════════════════════════════════════╗")
        print("║           SYSTEM HEALTH CHECK                ║")
        print("╚══════════════════════════════════════════════╝\n")
        for name, result in results.items():
            icon = STATUS_ICON.get(result["status"], "?")
            print(f"  {icon}  {name:<26} {result['detail']}")
        print()
        overall_icon = {"HEALTHY": "✅", "DEGRADED": "⚠️ ", "BLOCKED": "❌"}[overall]
        print(f"  {overall_icon}  Overall: {overall}\n")

    sys.exit(0 if overall == "HEALTHY" else 1)


if __name__ == "__main__":
    main()
