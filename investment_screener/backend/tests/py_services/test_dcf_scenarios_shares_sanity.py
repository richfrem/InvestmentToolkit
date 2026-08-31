"""
Caught live 2026-08-29 valuing CBRS (Cerebras Systems): load_raw_json() always
preferred shares_diluted over shares_outstanding whenever present and > 0, with
no sanity check. For CBRS, shares_diluted (495.5M) was 4.4x shares_outstanding
(112.2M) -- an extreme divergence, not normal option/RSU dilution (typically
5-20%) -- and silently using the inflated diluted count produced a materially
wrong (too-low) EPS and fair value. The same bug had already corrupted BE's
persisted projection: it used shares_diluted (239.0M) while the projection's
own analyticsLog.shareCountMethod field falsely documented shares_outstanding
(294.5M) as what was used.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_dcf_scenarios_shares_sanity.py -v
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from dcf_scenarios import load_raw_json  # noqa: E402


def _write_raw(tmp_path, shares_outstanding, shares_diluted, revenue=500_000_000, price=100.0):
    path = tmp_path / "raw.json"
    path.write_text(json.dumps({
        "ticker": "TEST",
        "metrics": {
            "revenue": revenue, "price": price, "market_cap": price * shares_outstanding,
            "shares_outstanding": shares_outstanding, "shares_diluted": shares_diluted,
        },
    }))
    return str(path)


def test_normal_dilution_still_prefers_diluted(tmp_path):
    """Ordinary option/RSU dilution (diluted modestly above outstanding, e.g.
    10%) must still prefer shares_diluted -- this is the common, correct case."""
    path = _write_raw(tmp_path, shares_outstanding=100_000_000, shares_diluted=110_000_000)
    _, _, shares, _ = load_raw_json(path)
    assert shares == 110_000_000


def test_extreme_diluted_above_outstanding_falls_back(tmp_path):
    """CBRS's real case: diluted 4.4x outstanding -- too extreme to be normal
    dilution, falls back to shares_outstanding instead of trusting it blindly."""
    path = _write_raw(tmp_path, shares_outstanding=112_247_109, shares_diluted=495_472_916)
    _, _, shares, _ = load_raw_json(path)
    assert shares == 112_247_109


def test_extreme_diluted_below_outstanding_falls_back(tmp_path):
    """BE's real case: diluted meaningfully below outstanding (239.0M vs 294.5M,
    ~19% lower) -- also not normal (diluted should be >= outstanding), falls
    back to shares_outstanding."""
    path = _write_raw(tmp_path, shares_outstanding=294_527_346, shares_diluted=239_010_811)
    _, _, shares, _ = load_raw_json(path)
    assert shares == 294_527_346


def test_missing_diluted_uses_outstanding(tmp_path):
    path = _write_raw(tmp_path, shares_outstanding=100_000_000, shares_diluted=0)
    _, _, shares, _ = load_raw_json(path)
    assert shares == 100_000_000


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        test_normal_dilution_still_prefers_diluted(p)
        test_extreme_diluted_above_outstanding_falls_back(p)
        test_extreme_diluted_below_outstanding_falls_back(p)
        test_missing_diluted_uses_outstanding(p)
    print("✓ All dcf_scenarios shares-sanity tests passed!")
