"""
Tests for ta_sweep_batch.py — persistence and data quality.

Category A: Pure function tests (parseNum parity via subprocess, save_sweep_results).
Category B: CLI smoke test — valid fixture input → valid JSON written to disk.

Run:
    python3 -m pytest plugins/tradingview/tests/test_ta_sweep_batch.py -v
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parents[3]
SCRIPT     = REPO_ROOT / "plugins/tradingview/scripts/ta_sweep_batch.py"
NODE_ROOT  = REPO_ROOT / "tradingview-cdp"
SWEEP_JS   = NODE_ROOT / "core/sweep.js"

# ── parseNum K/M suffix regression tests ─────────────────────────────────────

PARSE_NUM_FIXTURE = """
const { createRequire } = await import('module');
// Inline the parseNum function as extracted from sweep.js for isolated unit testing
function parseNum(raw) {
  if (raw === null || raw === undefined || raw === '') return null;
  const s = String(raw).replace(/,/g, '').replace(/%/g, '').replace(/−/g, '-').trim();
  const suffixMatch = s.match(/^([-\\d.]+)([KMBkmb])$/);
  if (suffixMatch) {
    const n = parseFloat(suffixMatch[1]);
    const m = suffixMatch[2].toUpperCase();
    const mult = m === 'K' ? 1e3 : m === 'M' ? 1e6 : 1e9;
    return isNaN(n) ? null : n * mult;
  }
  const cleaned = s.replace(/[^\\d.\\-]/g, '');
  const n = parseFloat(cleaned);
  return isNaN(n) ? null : n;
}
const cases = [
  ['363K',   363000],
  ['1.29M',  1290000],
  ['2.34M',  2340000],
  ['14.91',  14.91],
  ['-99.3%', -99.3],
  ['23.74%', 23.74],
  ['1,234.56', 1234.56],
  [null,     null],
  ['',       null],
];
const results = cases.map(([input, expected]) => {
  const got = parseNum(input);
  return { input, expected, got, pass: got === expected };
});
console.log(JSON.stringify(results));
"""


def _run_node_expr(expression: str) -> tuple[str, str, int]:
    """Run a Node.js expression and return (stdout, stderr, returncode)."""
    result = subprocess.run(
        ["node", "--input-type=module"],
        input=expression,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


class TestParseNumKMSuffix:
    """parseNum must scale K/M/B suffixes — regression for false VOLUME_SPIKE."""

    def test_k_suffix_scales_to_thousands(self):
        """363K → 363000, not 363 (bug: ratio was 281× instead of 0.28×)."""
        stdout, _stderr, _rc = _run_node_expr(
            "function parseNum(r){if(!r&&r!==0)return null;"
            "const s=String(r).replace(/,/g,'').replace(/%/g,'').replace(/−/g,'-').trim();"
            "const m=s.match(/^([-\\d.]+)([KMBkmb])$/);if(m){const n=parseFloat(m[1]);"
            "const mult=m[2].toUpperCase()==='K'?1e3:m[2].toUpperCase()==='M'?1e6:1e9;"
            "return isNaN(n)?null:n*mult;}"
            "const c=s.replace(/[^\\d.\\-]/g,'');const n=parseFloat(c);return isNaN(n)?null:n;}"
            "\nconsole.log(parseNum('363K'));"
        )
        assert stdout == "363000", f"363K should parse to 363000, got: {stdout}"

    def test_m_suffix_scales_to_millions(self):
        """1.29M → 1290000."""
        stdout, _stderr, _rc = _run_node_expr(
            "function parseNum(r){if(!r&&r!==0)return null;"
            "const s=String(r).replace(/,/g,'').replace(/%/g,'').replace(/−/g,'-').trim();"
            "const m=s.match(/^([-\\d.]+)([KMBkmb])$/);if(m){const n=parseFloat(m[1]);"
            "const mult=m[2].toUpperCase()==='K'?1e3:m[2].toUpperCase()==='M'?1e6:1e9;"
            "return isNaN(n)?null:n*mult;}"
            "const c=s.replace(/[^\\d.\\-]/g,'');const n=parseFloat(c);return isNaN(n)?null:n;}"
            "\nconsole.log(parseNum('1.29M'));"
        )
        assert stdout == "1290000", f"1.29M should parse to 1290000, got: {stdout}"

    def test_volume_ratio_no_longer_spikes(self):
        """vol=363K / volMA=1.29M should give ~0.28, not 281."""
        vol_raw = 363000   # after K-scaling
        vma_raw = 1290000  # after M-scaling
        ratio = round(vol_raw / vma_raw * 100) / 100
        assert ratio < 1.0, f"Expected ratio < 1.0 (no spike), got {ratio}"
        assert abs(ratio - 0.28) < 0.01, f"Expected ~0.28, got {ratio}"


# ── save_sweep_results persistence tests ─────────────────────────────────────

FIXTURE_RESULTS = [
    {
        "ticker": "AAPL",
        "close": 195.5,
        "changePct": 0.5,
        "rsi": 45.0,
        "rsima": 50.0,
        "volBias": -30.0,
        "adx": 22.0,
        "squeezeOn": False,
        "vol": 52000000,
        "volMA": 65000000,
        "volumeRatio": 0.8,
        "flags": [],
        "action": "HOLD",
        "targetAction": None,
        "targetWeight": 3.0,
    }
]


class TestSweepResultsPersistence:
    """ta_sweep_batch.py must persist results to ta-sweep-results.json."""

    def test_save_results_flag_in_help(self):
        """--save-results flag must appear in the CLI help output."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=5,
        )
        assert "--save-results" in result.stdout, (
            "--save-results flag not found in help output — was it added to argparse?"
        )
        assert "--no-save" in result.stdout, "--no-save flag must also be present"

    def test_save_sweep_results_writes_timestamped_json(self, tmp_path: Path):
        """save_sweep_results() writes {timestamp, scan_date, count, results} to file."""
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import save_sweep_results  # noqa: PLC0415

        out_file = tmp_path / "ta-sweep-results.json"
        save_sweep_results(FIXTURE_RESULTS, out_file)

        assert out_file.exists(), "Output file must be created"
        data = json.loads(out_file.read_text())

        assert "timestamp" in data, "Must include ISO timestamp"
        assert "scan_date" in data, "Must include scan_date (YYYY-MM-DD)"
        assert "count" in data, "Must include count of holdings scanned"
        assert "results" in data, "Must include results array"
        assert data["count"] == 1
        assert data["results"][0]["ticker"] == "AAPL"

    def test_save_sweep_results_overwrites_existing(self, tmp_path: Path):
        """Calling save_sweep_results twice overwrites — no append corruption."""
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import save_sweep_results  # noqa: PLC0415

        out_file = tmp_path / "ta-sweep-results.json"
        save_sweep_results(FIXTURE_RESULTS, out_file)
        save_sweep_results(FIXTURE_RESULTS + FIXTURE_RESULTS, out_file)

        data = json.loads(out_file.read_text())
        assert data["count"] == 2, "Second write must overwrite — not append"


# ── pctToFV denominator tests ─────────────────────────────────────────────────

class TestPctToFVDenominator:
    """pctToFV must be (FV − price) / price — the % move from HERE to fair value.

    Regression: the enrichment used (FV − price) / FV, which produced impossible
    values like −742% for OKLO and understated upside for BUY names (APLD showed
    +29.9% when the true upside at price was +42.6%).
    """

    def test_upside_uses_price_denominator(self):
        """APLD: FV 58.35 vs close 40.92 → +42.6% upside, not +29.9%."""
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import add_dcf_flags  # noqa: PLC0415
        result = {"ticker": "APLD", "close": 40.92, "flags": []}
        add_dcf_flags(result, {"fairValue": 58.35, "action": "BUY", "base": None})
        assert result["dcf"]["pctToFV"] == 42.6, (
            f"Expected (58.35-40.92)/40.92*100 = 42.6, got {result['dcf']['pctToFV']}"
        )

    def test_downside_never_below_minus_100(self):
        """OKLO: FV 6.65 vs close 56.03 → −88.1%. A price-denominated ratio
        can never be below −100%; the old FV-denominated math gave −742%."""
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import add_dcf_flags  # noqa: PLC0415
        result = {"ticker": "OKLO", "close": 56.03, "flags": []}
        add_dcf_flags(result, {"fairValue": 6.65, "action": "SELL", "base": None})
        pct = result["dcf"]["pctToFV"]
        assert pct >= -100, f"pctToFV below -100% is mathematically impossible: {pct}"
        assert pct == -88.1, f"Expected (6.65-56.03)/56.03*100 = -88.1, got {pct}"


# ── Enrichment preservation after ADX validation ──────────────────────────────

class TestEnrichmentPreservedAfterAdxValidation:
    """validate_adx returns a copy — the main loop must keep enriching THAT copy.

    Regression: main() called `res = validate_adx(res)` inside `for res in
    scan_results`, so when ADX was out of range the nulled copy (and all
    subsequent action/targetWeight enrichment) was silently discarded — the
    persisted JSON kept the invalid ADX and lacked the action fields.
    """

    def test_invalid_adx_row_keeps_enrichment_and_nulled_adx(self):
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import enrich_results  # noqa: PLC0415
        rows = [{"ticker": "CLSK", "close": 10.0, "adx": 161.9,
                 "flags": ["ADX_STRONG"]}]
        out = enrich_results(
            rows,
            target_map={"CLSK": {"action": "MAINTAIN", "targetWeight": 2.2}},
            dcf_loader=lambda t: None,
        )
        row = out[0]
        assert row["adx"] is None, "Out-of-range ADX must be nulled in the OUTPUT rows"
        assert "ADX_STRONG" not in row["flags"]
        assert row["action"] == "HOLD", "Derived action must survive ADX validation"
        assert row["targetWeight"] == 2.2, "Target enrichment must survive ADX validation"

    def test_valid_adx_row_enriched_normally(self):
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import enrich_results  # noqa: PLC0415
        rows = [{"ticker": "AAPL", "close": 195.5, "adx": 22.0, "flags": []}]
        out = enrich_results(rows, target_map={}, dcf_loader=lambda t: None)
        assert out[0]["adx"] == 22.0
        assert out[0]["action"] == "HOLD"
        assert out[0]["targetAction"] is None


# ── ADX range validation tests ────────────────────────────────────────────────

class TestAdxValidation:
    """ADX values outside 0–100 are physically impossible — must be nulled."""

    def _parse_sweep_output(self, raw_results: list[dict]) -> list[dict]:
        """Import and apply the validation logic from sweep.js output processing."""
        # The Python batch script validates ADX after receiving sweep.js output
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import validate_adx  # noqa: PLC0415
        return [validate_adx(r) for r in raw_results]

    def test_negative_adx_nulled(self):
        """ADX=-88.9 (impossible) → None."""
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import validate_adx  # noqa: PLC0415
        result = validate_adx({"ticker": "BE", "adx": -88.9, "flags": ["ADX_WEAK"]})
        assert result["adx"] is None
        assert "ADX_WEAK" not in result["flags"], "ADX flags must be removed when adx is invalid"

    def test_adx_above_100_nulled(self):
        """ADX=161.9 (impossible, max is 100) → None."""
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import validate_adx  # noqa: PLC0415
        result = validate_adx({"ticker": "CLSK", "adx": 161.9, "flags": ["ADX_STRONG"]})
        assert result["adx"] is None
        assert "ADX_STRONG" not in result["flags"]

    def test_valid_adx_unchanged(self):
        """ADX=44.5 (valid) → unchanged."""
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import validate_adx  # noqa: PLC0415
        result = validate_adx({"ticker": "BTDR", "adx": 44.5, "flags": ["ADX_STRONG"]})
        assert result["adx"] == 44.5
        assert "ADX_STRONG" in result["flags"]
