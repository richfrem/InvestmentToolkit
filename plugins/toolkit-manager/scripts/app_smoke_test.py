#!/usr/bin/env python3
"""
app_smoke_test.py - Start the backend on a COPY of the real databases and call every read route the web app uses.

Purpose:
    After changes to storage (tables, migrations, files removed), the unit tests prove each piece
    but not that the running app still serves its screens. This copies the real
    domain_model.sqlite and intelligence.sqlite into a git WORKTREE's data folder (never the main
    checkout), lets the app's own migrator upgrade the copies, starts the Express backend there
    on a spare port with none of the retired data files present, and calls the read routes the
    React app uses. Each route must answer with the expected status and JSON shape. Nothing is
    written to the real databases.

Layer:
    Audit / Verification (read-only against real data)

Usage Examples:
    python3 plugins/toolkit-manager/scripts/app_smoke_test.py
    python3 plugins/toolkit-manager/scripts/app_smoke_test.py --source-data /path/to/main/investment_screener/backend/data --port 3199
    python3 plugins/toolkit-manager/scripts/app_smoke_test.py --routes-only      # skip the copy, test whatever data folder is there

Key Functions (Index):
    - PROBES: the routes and the response each one must give
    - check_probe(): compare one response with its expectation
    - main_checkout_data_dir(): the real data folder (first entry of `git worktree list`)
    - copy_databases(): sqlite backup copy of the real databases into this worktree
    - run(): copy, start the backend, probe, stop, report

Key Input Dependencies:
    - The real investment_screener/backend/data/*.sqlite (read through the SQLite backup API)
    - investment_screener/backend (ts-node); the main checkout's node_modules are linked in temporarily

Key Output Dependencies:
    - A PASS/FAIL table on stdout; exit status 1 if any probe fails
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

DATABASES = ("domain_model.sqlite", "intelligence.sqlite")
RETIRED_FILES = (
    "portfolio.json", "target-portfolio.json", "trade-log.json", "cash_flows.json",
    "thesis_breaker_state.json", "orders_executed.jsonl", "observations.jsonl",
    "intelligence_events.jsonl", "ytd_performance_report.json", "portfolio-config.json",
)


@dataclass
class Probe:
    """One route and the response it must give."""
    path: str
    statuses: tuple[int, ...] = (200,)
    json_type: type | tuple[type, ...] = (dict, list)
    keys: tuple[str, ...] = field(default_factory=tuple)
    numbers: tuple[str, ...] = field(default_factory=tuple)  # keys that must hold a number, never null (the screens format them)
    note: str = ""


PROBES = [
    Probe("/health", keys=("status",)),
    Probe("/api/tv-status", keys=("price_source",)),
    Probe("/api/portfolio", json_type=dict, keys=("dataSource",)),
    Probe("/api/portfolio/summary", json_type=dict, keys=("totalMarketValueUSD", "ytdStartValueCAD", "price_source"),
          numbers=("totalMarketValueUSD", "totalMarketValueCAD", "ytdStartValueCAD", "ytdChangePctCAD",
                   "liveUsdCadRate", "jan1UsdCadRate", "positionCount"),
          note="a null here crashed the Portfolio Summary screen"),
    Probe("/api/portfolio/performance", (200, 404, 500, 503), note="needs cash-flow data; any JSON answer"),
    Probe("/api/portfolio/weights", json_type=dict),
    Probe("/api/portfolio/status", (200, 404)),
    Probe("/api/portfolio/strategy-allocation", json_type=dict),
    Probe("/api/portfolio/position/NVDA", (200, 404)),
    Probe("/api/projections", json_type=list),
    Probe("/api/projections/NVDA", (200, 404)),
    Probe("/api/screener/all-holdings", json_type=(dict, list)),
    Probe("/api/screener/watchlist", json_type=(dict, list)),
    Probe("/api/screener/recommendations", (200, 500, 503), note="needs prices; any JSON answer"),
    Probe("/api/stock/NVDA", (200, 404, 500)),
    Probe("/api/research", json_type=dict, keys=("reports",)),
    Probe("/api/docs/investment-thesis", (200, 404)),
    Probe("/api/docs/latest-review-data", (200, 404)),
    Probe("/api/docs/agent-guide", (200, 404)),
    Probe("/api/theses/target-portfolio", (200, 404)),
    Probe("/api/theses/target-portfolio/health", (200, 404)),
    Probe("/api/theses/sub-strategies", json_type=(dict, list)),
    Probe("/api/trading/audit/today", json_type=dict, keys=("events",)),
    Probe("/api/trading/log", json_type=(dict, list)),
    Probe("/api/daily-brief/latest", (200, 404)),
    Probe("/api/daily-brief/history", json_type=(dict, list)),
]


def check_probe(probe: Probe, status: int, body: object) -> str | None:
    """None when ``status``/``body`` match ``probe``; else a one-line reason."""
    if status not in probe.statuses:
        return f"status {status}, expected one of {probe.statuses}"
    if status == 200:
        if not isinstance(body, probe.json_type if isinstance(probe.json_type, tuple) else (probe.json_type,)):
            return f"body is {type(body).__name__}, expected {probe.json_type}"
        if probe.keys and isinstance(body, dict):
            missing = [k for k in probe.keys if k not in body]
            if missing:
                return f"missing keys {missing}"
            bad = [k for k in probe.numbers if not isinstance(body.get(k), (int, float)) or isinstance(body.get(k), bool)]
            if bad:
                return f"not a number: {bad}"
    return None


def key_values(bodies: dict) -> list[str]:
    """A few headline numbers from the responses, for a human to eyeball."""
    out = []
    summary = bodies.get("/api/portfolio/summary")
    if isinstance(summary, dict):
        out.append(
            f"summary: {summary.get('positionCount')} positions, ${summary.get('totalMarketValueUSD', 0):,.2f} USD, "
            f"YTD available={summary.get('ytdAvailable')}, price_source={summary.get('price_source')}"
        )
    portfolio = bodies.get("/api/portfolio")
    if isinstance(portfolio, dict):
        holdings = portfolio.get("holdings") or portfolio.get("items") or []
        out.append(f"portfolio table: {len(holdings)} rows, dataSource={portfolio.get('dataSource')}")
    screener = bodies.get("/api/screener/all-holdings")
    rows = screener if isinstance(screener, list) else (screener or {}).get("holdings", [])
    if isinstance(rows, list):
        out.append(f"screener: {len(rows)} tickers, {sum(1 for r in rows if isinstance(r, dict) and r.get('hasValuation'))} with a valuation")
    research = bodies.get("/api/research")
    if isinstance(research, dict):
        out.append(f"research list: {len(research.get('reports', []))} reports")
    projections = bodies.get("/api/projections")
    if isinstance(projections, list):
        out.append(f"projections: {len(projections)}")
    return out


def main_checkout_data_dir(repo_root: Path) -> Path:
    """The data folder of the main checkout (first entry of ``git worktree list``)."""
    out = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=repo_root, capture_output=True, text=True, check=True).stdout
    first = next(line.split(" ", 1)[1] for line in out.splitlines() if line.startswith("worktree "))
    return Path(first) / "investment_screener/backend/data"


def is_worktree(repo_root: Path) -> bool:
    """True when ``repo_root`` is a linked git worktree (its .git is a file)."""
    return (repo_root / ".git").is_file()


def copy_databases(source_dir: Path, dest_dir: Path) -> list[str]:
    """Copy each database with the SQLite backup API (consistent, read-only on the source)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in DATABASES:
        src = source_dir / name
        if not src.exists():
            continue
        for suffix in ("", "-wal", "-shm"):
            stale = dest_dir / (name + suffix)
            if stale.exists():
                stale.unlink()
        source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        target = sqlite3.connect(str(dest_dir / name))
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        copied.append(name)
    return copied


def _get(url: str, token: str | None) -> tuple[int, object]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    try:
        return status, json.loads(raw or b"null")
    except json.JSONDecodeError:
        return status, raw.decode("utf-8", "replace")[:200]


def run(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[3]
    backend = repo_root / "investment_screener/backend"
    data_dir = backend / "data"
    if not is_worktree(repo_root):
        print("REFUSED: run this from a git worktree, not the main checkout (it replaces the data-folder databases).", file=sys.stderr)
        return 2

    if not args.routes_only:
        source = Path(args.source_data) if args.source_data else main_checkout_data_dir(repo_root)
        if source.resolve() == data_dir.resolve():
            print("REFUSED: source and destination data folders are the same.", file=sys.stderr)
            return 2
        copied = copy_databases(source, data_dir)
        print(f"copied {copied} from {source}")
        migrated = subprocess.run(
            [sys.executable, str(backend / "py_services/domain_model/schema_migrator.py"), "--db", str(data_dir / "domain_model.sqlite")],
            capture_output=True, text=True,
        )
        print("schema migrator on the copy:", (migrated.stdout.strip() or migrated.stderr.strip())[-300:])
        if migrated.returncode != 0:
            return 1
    present = [name for name in RETIRED_FILES if (data_dir / name).exists()]
    print(f"retired data files present in this checkout's data folder: {present or 'none'}")

    main_root = main_checkout_data_dir(repo_root).parents[2]
    linked = []
    for rel in ("investment_screener/backend/node_modules", "investment_screener/node_modules"):
        target = repo_root / rel
        if not target.exists():
            target.symlink_to(main_root / rel)
            linked.append(target)
    env = {**os.environ, "PORT": str(args.port)}
    server = subprocess.Popen(
        [str(repo_root / "investment_screener/node_modules/.bin/ts-node"), "--transpile-only", "src/index.ts"],
        cwd=backend, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    failures = 0
    try:
        base = f"http://127.0.0.1:{args.port}"
        for _ in range(60):
            try:
                if _get(f"{base}/health", None)[0] == 200:
                    break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(1)
        else:
            print("backend did not start:\n" + (server.stdout.read() if server.poll() is not None else ""), file=sys.stderr)
            return 1
        token = (repo_root / ".runtime/api-token").read_text().strip()
        bodies = {}
        for probe in PROBES:
            status, body = _get(base + probe.path, token)
            bodies[probe.path] = body
            problem = check_probe(probe, status, body)
            failures += problem is not None
            print(f"{'PASS' if problem is None else 'FAIL'}  {status}  {probe.path}" + (f"   <- {problem}" if problem else ""))
        print("\nvalues the app returned (compare with what you expect to see on screen):")
        for line in key_values(bodies):
            print("  " + line)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        for link in linked:
            link.unlink()
    print(f"\n{len(PROBES) - failures}/{len(PROBES)} routes passed")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-data", help="Real data folder to copy the databases from (default: the main checkout's)")
    parser.add_argument("--port", type=int, default=3199)
    parser.add_argument("--routes-only", action="store_true", help="Do not copy databases; test the data folder as it is")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
