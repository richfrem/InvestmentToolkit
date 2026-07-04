"""
edgar_facts.py (Python Service)
=====================================

Purpose:
    SEC EDGAR XBRL companyfacts client. Point-in-time-correct fundamentals
    (each datapoint carries its actual filing date) for US filers only —
    yfinance is the fallback/supplement for non-US listings in market_data.py.

Layer: Backend / Python Services / Data Layer

Usage Examples:
    python3 edgar_facts.py 0000320193
"""

import sys
import requests

USER_AGENT = "InvestmentToolkit research@localhost"

_TAG_MAP = {
    "revenue": "Revenues",
    "netIncome": "NetIncomeLoss",
    "operatingIncome": "OperatingIncomeLoss",
}


def get_company_facts(cik: str) -> dict:
    """Fetch SEC EDGAR XBRL company facts for a given CIK.

    Args:
        cik: Central Index Key (10-digit CIK string or unpadded integer).

    Returns:
        dict: Mapping of metric keys (e.g., 'revenue', 'netIncome') to dicts with
              'value' (float) and 'asOf' (filing date string). Metrics with missing
              or malformed values are excluded (not zeroed).
    """
    padded_cik = cik.zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded_cik}.json"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT})
    if resp.status_code != 200:
        return {}

    data = resp.json()
    gaap = data.get("facts", {}).get("us-gaap", {})

    result = {}
    for key, tag in _TAG_MAP.items():
        units = gaap.get(tag, {}).get("units", {}).get("USD", [])
        annual = [u for u in units if u.get("form") == "10-K"]
        if not annual:
            continue
        latest = max(annual, key=lambda u: u.get("end", ""))

        # Skip this metric if 'val' is missing or cannot be converted to float
        val = latest.get("val")
        if val is None:
            continue
        try:
            numeric_val = float(val)
        except (TypeError, ValueError):
            continue

        result[key] = {"value": numeric_val, "asOf": latest.get("filed", latest.get("end"))}

    return result


def main():
    """CLI entry point: fetch and print company facts JSON for a given CIK."""
    if len(sys.argv) < 2:
        print('{"error": "cik required"}')
        sys.exit(1)
    import json
    print(json.dumps(get_company_facts(sys.argv[1]), indent=2))


if __name__ == "__main__":
    main()
