#!/usr/bin/env python3
"""
fetch_13f.py (Python Service)
==============================

Purpose:
    Poll SEC EDGAR for 13F-HR filings from a given fund, download and parse holdings into
    structured JSON, and generate quarter-over-quarter diffs. Designed for daily polling
    to detect new filings as soon as they appear (due ~45 days after quarter-end).

Layer: Backend / Python Services / SEC Data

Requirements:
    - Python stdlib only (urllib, xml.etree, json, argparse)
    - No API key required — SEC EDGAR data.sec.gov is free with a User-Agent header
    - Rate limit: max ~10 req/sec; script sleeps 0.5s between requests

Usage Examples:
    python3 fetch_13f.py --cik 0002045724 --all
    python3 fetch_13f.py --cik 0002045724 --poll
    python3 fetch_13f.py --cik 0002045724 --fetch-last 4
    python3 fetch_13f.py --cik 0002045724 --summary
    python3 fetch_13f.py --cik 0002045724 --diff

Data written to:
    investment_screener/backend/data/13f/{CIK}_index.json       — filing list cache
    investment_screener/backend/data/13f/{accession}.json       — parsed holdings per filing
    investment_screener/backend/data/13f/{CIK}_diff.json        — latest vs prior quarter diff

Key Functions:
    - poll_for_new()         — compare cached index vs EDGAR; returns True if new filing found
    - fetch_filings()        — download and parse last N 13F-HR filings
    - parse_holdings_xml()   — parse informationTable XML into holdings list
    - generate_diff()        — build quarter-over-quarter change summary
    - print_summary()        — ranked holdings table for terminal output
    - print_diff_report()    — formatted change report for terminal output
"""

import argparse
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import urllib.request as _urllib

try:
    import requests as _requests
    _SESSION = _requests.Session()
    _SESSION.headers.update({"User-Agent": "InvestmentToolkit richfrem connect.richfrem@gmail.com"})
    _USE_REQUESTS = True
except ImportError:
    _USE_REQUESTS = False

# ── constants ─────────────────────────────────────────────────────────────────

EDGAR_BASE = "https://data.sec.gov"
ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
NS = "http://www.sec.gov/edgar/document/thirteenf/informationtable"

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent.parent.parent / "investment_screener" / "backend" / "data" / "13f"


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def fetch_text(url: str) -> str:
    if _USE_REQUESTS:
        resp = _SESSION.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    import ssl
    ctx = ssl.create_default_context()
    req = _urllib.Request(url, headers={"User-Agent": "InvestmentToolkit richfrem connect.richfrem@gmail.com"})
    with _urllib.urlopen(req, timeout=15, context=ctx) as r:  # type: ignore[arg-type]
        return r.read().decode("utf-8")


def fetch_url(url: str, as_json: bool = False) -> dict | str:
    raw = fetch_text(url)
    time.sleep(0.4)
    if as_json:
        return json.loads(raw)
    return raw


# ── filing index ───────────────────────────────────────────────────────────────

def normalize_cik(cik: str) -> str:
    """Zero-pad CIK to 10 digits for API URLs."""
    return str(int(cik.replace("CIK", "").strip())).zfill(10)


def load_submissions(cik10: str) -> dict:
    url = f"{EDGAR_BASE}/submissions/CIK{cik10}.json"
    result = fetch_url(url, as_json=True)
    assert isinstance(result, dict)
    return result


def get_13f_filings(submissions: dict) -> list[dict]:
    """Return list of 13F-HR filings sorted newest-first."""
    recent = submissions["filings"]["recent"]
    keys = ["form", "filingDate", "accessionNumber", "reportDate"]
    rows = zip(*(recent[k] for k in keys))
    filings = [
        {"form": f, "filing_date": d, "accession": a, "period_of_report": r}
        for f, d, a, r in rows
        if "13F-HR" == f
    ]
    return sorted(filings, key=lambda x: x["filing_date"], reverse=True)


# ── holdings XML discovery and parsing ────────────────────────────────────────

def acc_nodash(accession: str) -> str:
    return accession.replace("-", "")


def discover_holdings_filename(cik_int: int, accession: str) -> str | None:
    """List the filing folder HTML to find the informationTable XML filename."""
    url = f"{ARCHIVES_BASE}/{cik_int}/{acc_nodash(accession)}/"
    html = fetch_url(url)
    assert isinstance(html, str)
    # Find all .xml hrefs; the data file is any XML that isn't primary_doc.xml
    candidates = re.findall(r'href="([^"]*\.xml)"', html)
    for href in candidates:
        basename = href.split("/")[-1]
        if basename and basename != "primary_doc.xml":
            return basename
    return None


def parse_holdings_xml(xml_text: str) -> list[dict]:
    """Parse ns1:informationTable XML into a list of holding dicts."""
    root = ET.fromstring(xml_text)
    holdings = []
    for info in root.findall(f"{{{NS}}}infoTable"):

        def txt(tag):
            el = info.find(f"{{{NS}}}{tag}")
            return el.text.strip() if el is not None and el.text else None

        shares_el = info.find(f"{{{NS}}}shrsOrPrnAmt")
        shares = int(shares_el.findtext(f"{{{NS}}}sshPrnamt", "0").strip()) if shares_el is not None else 0
        share_type = shares_el.findtext(f"{{{NS}}}sshPrnamtType", "SH").strip() if shares_el is not None else "SH"

        holdings.append({
            "name": txt("nameOfIssuer"),
            "cusip": txt("cusip"),
            "title_class": (txt("titleOfClass") or "").strip(),
            "value_usd": int(txt("value") or 0),
            "shares": shares,
            "type": share_type,
            "put_call": txt("putCall"),
            "discretion": txt("investmentDiscretion"),
        })
    return holdings


def enrich_with_pct(holdings: list[dict]) -> list[dict]:
    total = sum(h["value_usd"] for h in holdings)
    for h in holdings:
        h["value_pct"] = round(h["value_usd"] / total * 100, 2) if total else 0
    return sorted(holdings, key=lambda x: x["value_usd"], reverse=True)


# ── fetch + persist ────────────────────────────────────────────────────────────

def index_path(cik10: str) -> Path:
    return DATA_DIR / f"{cik10}_index.json"


def filing_path(accession: str) -> Path:
    return DATA_DIR / f"{acc_nodash(accession)}.json"


def diff_path(cik10: str) -> Path:
    return DATA_DIR / f"{cik10}_diff.json"


def load_index(cik10: str) -> list[dict]:
    p = index_path(cik10)
    if p.exists():
        return json.loads(p.read_text())
    return []


def save_index(cik10: str, filings: list[dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    index_path(cik10).write_text(json.dumps(filings, indent=2))


def fetch_and_save_filing(fund_name: str, cik10: str, cik_int: int, filing: dict) -> dict | None:
    out = filing_path(filing["accession"])
    if out.exists():
        return json.loads(out.read_text())

    print(f"  Downloading {filing['filing_date']} ({filing['accession']}) …")
    filename = discover_holdings_filename(cik_int, filing["accession"])
    if not filename:
        print(f"    ⚠ Could not find holdings XML — skipping")
        return None

    url = f"{ARCHIVES_BASE}/{cik_int}/{acc_nodash(filing['accession'])}/{filename}"
    xml_text = fetch_url(url)
    assert isinstance(xml_text, str)
    holdings = enrich_with_pct(parse_holdings_xml(xml_text))
    total = sum(h["value_usd"] for h in holdings)

    record = {
        "cik": cik10,
        "fund": fund_name,
        "filing_date": filing["filing_date"],
        "period_of_report": filing["period_of_report"],
        "accession": filing["accession"],
        "source_xml": filename,
        "total_value_usd": total,
        "position_count": len(holdings),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "holdings": holdings,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2))
    print(f"    ✓ {len(holdings)} positions, ${total/1_000_000:,.1f}M total → {out.name}")
    return record


# ── diff ──────────────────────────────────────────────────────────────────────

def generate_diff(current: dict, prior: dict) -> dict:
    cur = {h["cusip"]: h for h in current["holdings"]}
    prv = {h["cusip"]: h for h in prior["holdings"]}

    new_pos, closed, increased, decreased, unchanged = [], [], [], [], []

    for cusip, h in cur.items():
        if cusip not in prv:
            new_pos.append(h)
        else:
            p = prv[cusip]
            delta_shares = h["shares"] - p["shares"]
            delta_value = h["value_usd"] - p["value_usd"]
            delta_pct = round(delta_shares / p["shares"] * 100, 1) if p["shares"] else 0
            entry = {
                **h,
                "prior_shares": p["shares"],
                "prior_value_usd": p["value_usd"],
                "delta_shares": delta_shares,
                "delta_value_usd": delta_value,
                "delta_pct": delta_pct,
            }
            if delta_shares > 0:
                increased.append(entry)
            elif delta_shares < 0:
                decreased.append(entry)
            else:
                unchanged.append(entry)

    for cusip, h in prv.items():
        if cusip not in cur:
            closed.append(h)

    diff = {
        "from_date": prior["period_of_report"],
        "to_date": current["period_of_report"],
        "from_filing": prior["filing_date"],
        "to_filing": current["filing_date"],
        "from_total_usd": prior["total_value_usd"],
        "to_total_usd": current["total_value_usd"],
        "new_positions": sorted(new_pos, key=lambda x: x["value_usd"], reverse=True),
        "closed_positions": sorted(closed, key=lambda x: x["value_usd"], reverse=True),
        "increased": sorted(increased, key=lambda x: abs(x["delta_value_usd"]), reverse=True),
        "decreased": sorted(decreased, key=lambda x: abs(x["delta_value_usd"]), reverse=True),
        "unchanged": unchanged,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    diff_path(cik10_from_record(current)).write_text(json.dumps(diff, indent=2))
    return diff


def cik10_from_record(record: dict) -> str:
    return normalize_cik(record["cik"])


# ── terminal output ────────────────────────────────────────────────────────────

def print_summary(record: dict):
    print(f"\n{'═'*70}")
    print(f"  {record['fund']} — 13F Holdings")
    print(f"  Period: {record['period_of_report']}  |  Filed: {record['filing_date']}")
    print(f"  Total: ${record['total_value_usd']/1_000_000:,.1f}M  |  Positions: {record['position_count']}")
    print(f"{'═'*70}")
    print(f"  {'#':<4} {'Ticker/Name':<35} {'$M':>8} {'%':>6} {'Shares':>12} {'Type':<6} {'P/C':<5}")
    print(f"  {'-'*4} {'-'*35} {'-'*8} {'-'*6} {'-'*12} {'-'*6} {'-'*5}")
    for i, h in enumerate(record["holdings"], 1):
        name = (h["name"] or "")[:34]
        val_m = h["value_usd"] / 1_000_000
        pc = h["put_call"] or ""
        print(f"  {i:<4} {name:<35} {val_m:>8,.1f} {h['value_pct']:>5.1f}% {h['shares']:>12,} {h['type']:<6} {pc:<5}")


def print_diff_report(diff: dict):
    def _rows(items, show_delta=False):
        for h in items:
            name = (h["name"] or "")[:34]
            val_m = h["value_usd"] / 1_000_000
            if show_delta:
                d = h["delta_pct"]
                arrow = "▲" if d > 0 else "▼"
                print(f"    {name:<35} ${val_m:>8,.1f}M  {arrow}{abs(d):.1f}%")
            else:
                print(f"    {name:<35} ${val_m:>8,.1f}M")

    print(f"\n{'═'*60}")
    print(f"  SA LP — Quarter-over-Quarter Changes")
    print(f"  {diff['from_date']} → {diff['to_date']}")
    delta_aum = (diff["to_total_usd"] - diff["from_total_usd"]) / 1_000_000
    print(f"  AUM: ${diff['from_total_usd']/1_000_000:,.1f}M → ${diff['to_total_usd']/1_000_000:,.1f}M  ({delta_aum:+,.1f}M)")
    print(f"{'═'*60}")

    if diff["new_positions"]:
        print(f"\n  🟢 NEW POSITIONS ({len(diff['new_positions'])})")
        _rows(diff["new_positions"])

    if diff["closed_positions"]:
        print(f"\n  🔴 CLOSED POSITIONS ({len(diff['closed_positions'])})")
        _rows(diff["closed_positions"])

    if diff["increased"]:
        print(f"\n  ▲ INCREASED ({len(diff['increased'])})")
        _rows(diff["increased"], show_delta=True)

    if diff["decreased"]:
        print(f"\n  ▼ DECREASED ({len(diff['decreased'])})")
        _rows(diff["decreased"], show_delta=True)

    print(f"\n  Unchanged: {len(diff['unchanged'])} positions")


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_poll(cik10: str, filings: list[dict]) -> bool:
    """Return True if a new filing was found and downloaded."""
    cached = load_index(cik10)
    cached_dates = {f["filing_date"] for f in cached}
    latest = filings[0] if filings else None
    if latest and latest["filing_date"] not in cached_dates:
        print(f"  🆕 New filing detected: {latest['filing_date']} ({latest['period_of_report']})")
        return True
    print(f"  ✓ No new filings (latest: {filings[0]['filing_date'] if filings else 'none'})")
    return False


def cmd_fetch(cik10: str, fund_name: str, filings: list[dict], n: int) -> list[dict]:
    cik_int = int(cik10)
    records = []
    for filing in filings[:n]:
        r = fetch_and_save_filing(fund_name, cik10, cik_int, filing)
        if r:
            records.append(r)
    save_index(cik10, filings)
    return records


def cmd_diff(cik10: str) -> dict | None:
    cached = load_index(cik10)
    if len(cached) < 2:
        print("  ⚠ Need at least 2 filings cached. Run --fetch-last 2 first.")
        return None
    current_path = filing_path(cached[0]["accession"])
    prior_path = filing_path(cached[1]["accession"])
    if not current_path.exists() or not prior_path.exists():
        print("  ⚠ Filing JSON not found. Run --fetch-last 2 first.")
        return None
    current = json.loads(current_path.read_text())
    prior = json.loads(prior_path.read_text())
    diff = generate_diff(current, prior)
    print(f"  ✓ Diff written → {diff_path(cik10).name}")
    return diff


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SEC EDGAR 13F filing tracker")
    parser.add_argument("--cik", required=True, help="Fund CIK (e.g. 0002045724)")
    parser.add_argument("--poll", action="store_true", help="Check EDGAR for new filing vs cache")
    parser.add_argument("--fetch-last", type=int, metavar="N", help="Download last N 13F filings")
    parser.add_argument("--summary", action="store_true", help="Print current holdings summary")
    parser.add_argument("--diff", action="store_true", help="Print quarter-over-quarter diff")
    parser.add_argument("--all", action="store_true", help="poll + fetch-last 4 + summary + diff")
    args = parser.parse_args()

    cik10 = normalize_cik(args.cik)
    print(f"CIK: {cik10}")

    print("Fetching EDGAR submissions …")
    submissions = load_submissions(cik10)
    print(f"Fund: {submissions.get('name')}")
    filings = get_13f_filings(submissions)
    print(f"13F-HR filings on record: {len(filings)}")

    do_fetch = args.fetch_last or args.all
    do_poll = args.poll or args.all
    do_summary = args.summary or args.all
    do_diff = args.diff or args.all

    fund_name = submissions.get("name", "Unknown Fund")

    new_found = False
    if do_poll:
        new_found = cmd_poll(cik10, filings)

    if do_fetch:
        n = args.fetch_last if args.fetch_last else 4
        print(f"\nFetching last {n} filings …")
        cmd_fetch(cik10, fund_name, filings, n)

    if do_diff or (do_poll and new_found):
        print("\nGenerating diff …")
        diff = cmd_diff(cik10)
        if diff and do_diff:
            print_diff_report(diff)

    if do_summary:
        cached = load_index(cik10)
        if cached:
            p = filing_path(cached[0]["accession"])
            if p.exists():
                print_summary(json.loads(p.read_text()))
            else:
                print("  ⚠ Latest filing not cached. Run --fetch-last 1 first.")

    print("\nDone.")


if __name__ == "__main__":
    main()
