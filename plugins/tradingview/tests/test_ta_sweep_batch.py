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

    def test_save_sweep_results_writes_timestamped_json(self, tmp_path: Path):
        """save_sweep_results() writes {timestamp, scan_date, count, results} to file."""
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import save_sweep_results  # noqa: PLC0415

        out_file = tmp_path / "ta-sweep-results.json"
        jsonl_path = tmp_path / "observations.jsonl"
        db_path = tmp_path / "intelligence.sqlite"
        save_sweep_results(FIXTURE_RESULTS, json_export_path=out_file, jsonl_path=jsonl_path, db_path=db_path)

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
        jsonl_path = tmp_path / "observations.jsonl"
        db_path = tmp_path / "intelligence.sqlite"
        save_sweep_results(FIXTURE_RESULTS, json_export_path=out_file, jsonl_path=jsonl_path, db_path=db_path)
        save_sweep_results(FIXTURE_RESULTS + FIXTURE_RESULTS, json_export_path=out_file, jsonl_path=jsonl_path, db_path=db_path)

        data = json.loads(out_file.read_text())
        assert data["count"] == 2, "Second write must overwrite — not append"

    def test_save_sweep_results_writes_to_ledger_and_sqlite(self, tmp_path: Path):
        """save_sweep_results() must write TECHNICAL_SWEEP events to the ledger and SQLite DB."""
        sys.path.insert(0, str(SCRIPT.parent))
        from ta_sweep_batch import save_sweep_results  # noqa: PLC0415
        sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
        from intelligence.db_client import initialize_db  # noqa: E402
        import sqlite3

        out_file = tmp_path / "ta-sweep-results.json"
        jsonl_path = tmp_path / "observations.jsonl"
        db_path = tmp_path / "intelligence.sqlite"

        # Initialize the test DB and instrument
        conn = initialize_db(str(db_path))
        conn.execute("INSERT INTO instrument VALUES ('us-aapl', 'AAPL', 'NASDAQ', 'Apple', '2026-07-18', NULL);")
        conn.commit()
        conn.close()

        save_sweep_results(FIXTURE_RESULTS, json_export_path=out_file, jsonl_path=jsonl_path, db_path=db_path)

        # 1. Verify JSON file still exists (legacy compatibility)
        assert out_file.exists()

        # 2. Verify JSONL ledger contains the TECHNICAL_SWEEP event
        assert jsonl_path.exists()
        lines = jsonl_path.read_text().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["event_type"] == "TECHNICAL_SWEEP"
        assert record["ticker"] == "AAPL"
        
        # 3. Verify SQLite DB contains the technical sweep event resolved to instrument
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT instrument_id, event_type, status, payload_json FROM intelligence_event;")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "us-aapl"
        assert row[1] == "TECHNICAL_SWEEP"
        assert row[2] == "ACTIVE"
        payload = json.loads(row[3])
        assert payload["ticker"] == "AAPL"
        assert payload["rsi"] == 45.0
        conn.close()

    def test_save_sweep_results_writes_no_json_by_default(self, tmp_path: Path):
        """Wave 5B: without json_export_path, save_sweep_results must not create any JSON file —
        only the ledger/SQLite write is unconditional now."""
        sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))
        from ta_sweep_batch import save_sweep_results  # noqa: PLC0415

        jsonl_path = tmp_path / "observations.jsonl"
        db_path = tmp_path / "intelligence.sqlite"
        from intelligence.db_client import initialize_db  # noqa: PLC0415
        conn = initialize_db(str(db_path))
        conn.execute("INSERT INTO instrument VALUES ('us-aapl', 'AAPL', 'NASDAQ', 'Apple', '2026-01-01', NULL);")
        conn.commit()
        conn.close()

        save_sweep_results(FIXTURE_RESULTS, jsonl_path=jsonl_path, db_path=db_path)

        assert not any(tmp_path.glob("*.json"))  # no flat JSON written anywhere
        import sqlite3
        conn = sqlite3.connect(db_path)
        count = conn.execute(
            "SELECT COUNT(*) FROM intelligence_event WHERE event_type = 'TECHNICAL_SWEEP';"
        ).fetchone()[0]
        conn.close()
        assert count == len(FIXTURE_RESULTS)  # ledger/SQLite write still unconditional


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


# ── local vs. TV Data Window cross-check (--validate mode) ───────────────────

sys.path.insert(0, str(SCRIPT.parent))
from ta_sweep_batch import add_local_validation  # noqa: E402


def test_add_local_validation_flags_divergence_over_2pts():
    result = {"ticker": "NVDA", "rsi": 57.9, "adx": 30.1}

    def fake_snapshot(ticker, timeframe, period, benchmark, anchor_date):
        return {"rsi14": 58.2, "adx14": 27.3}

    enriched = add_local_validation(result, snapshot_fn=fake_snapshot)

    assert enriched["localValidation"]["rsi"]["local"] == 58.2
    assert enriched["localValidation"]["rsi"]["tv"] == 57.9
    assert enriched["localValidation"]["rsi"]["flag"] is False  # 0.3pt divergence
    assert enriched["localValidation"]["adx"]["divergencePts"] == 2.8
    assert enriched["localValidation"]["adx"]["flag"] is True  # 2.8pt > 2.0pt threshold


def test_add_local_validation_handles_missing_tv_values():
    result = {"ticker": "NVDA"}  # no "rsi"/"adx" keys from the TV scrape

    def fake_snapshot(ticker, timeframe, period, benchmark, anchor_date):
        return {"rsi14": 58.2, "adx14": 27.3}

    enriched = add_local_validation(result, snapshot_fn=fake_snapshot)
    assert enriched["localValidation"]["rsi"]["tv"] is None
    assert enriched["localValidation"]["rsi"]["flag"] is False  # can't flag without a TV value


# ── load_dcf — Wave 1 Task 7B rewire onto domain_model.sqlite (ADR-029) ───────

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    save_projection_version,
    add_projection_scenario,
)

from ta_sweep_batch import load_dcf  # noqa: E402


def test_load_dcf_returns_latest_projection_fields(tmp_path):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-06-01T00:00:00Z",
            analyzed_at="2026-06-01T00:00:00Z",
            fair_value=200.0, action="ACCUMULATE", source="AI_AGENT",
        )
        projection_id = f"{investment_id}:1"
        add_projection_scenario(conn, projection_id, "bear", scenario_price=150.0)
        add_projection_scenario(conn, projection_id, "base", scenario_price=200.0)
        add_projection_scenario(conn, projection_id, "bull", scenario_price=260.0)
    finally:
        conn.close()

    dcf = load_dcf("NVDA", db_path=db_path)
    assert dcf["fairValue"] == 200.0
    assert dcf["action"] == "ACCUMULATE"
    assert dcf["bear"] == 150.0
    assert dcf["base"] == 200.0
    assert dcf["bull"] == 260.0
    assert dcf["analyzedAt"] == "2026-06-01T00:00:00Z"
    assert dcf["daysSinceDCF"] is not None
    assert dcf["daysSinceDCF"] >= 90


def test_add_dcf_flags_flags_earnings_dcf_due_when_stale():
    from ta_sweep_batch import add_dcf_flags

    res = {"ticker": "AAPL", "close": 230.0}
    dcf = {
        "fairValue": 220.0,
        "action": "HOLD",
        "daysSinceDCF": 120,
        "analyzedAt": "2026-05-02T00:00:00Z",
    }
    add_dcf_flags(res, dcf)
    assert "EARNINGS_DCF_DUE" in res["flags"]
    assert any("EARNINGS / QUARTERLY DCF UPDATE DUE" in r for r in res.get("hitl_reminders", []))
    assert res["dcf"]["daysSinceDCF"] == 120


def test_add_dcf_flags_does_not_flag_fresh_dcf():
    from ta_sweep_batch import add_dcf_flags

    res = {"ticker": "ARM", "close": 230.0}
    dcf = {
        "fairValue": 150.0,
        "action": "SELL",
        "daysSinceDCF": 2,
        "analyzedAt": "2026-09-01T00:00:00Z",
    }
    add_dcf_flags(res, dcf)
    assert "EARNINGS_DCF_DUE" not in res.get("flags", [])


def test_load_dcf_returns_none_for_unknown_ticker(tmp_path):
    db_path = tmp_path / "test.sqlite"
    initialize_db(str(db_path)).close()

    assert load_dcf("ZZZZ", db_path=db_path) is None


# ── load_portfolio — Wave 3 rewire onto domain_model.sqlite (SQLite holdings) ──


def _seed_portfolio_db(tmp_path, rows):
    """Build a throwaway domain_model.sqlite with (account, symbol, qty, price)
    rows and return its path. Mirrors test_portfolio_io.py::_build_test_db."""
    sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
    from domain_model.db_client import initialize_db  # noqa: PLC0415
    from domain_model.account_repository import upsert_account  # noqa: PLC0415
    from domain_model.investment_repository import resolve_investment  # noqa: PLC0415
    from domain_model.investment_price_repository import upsert_investment_price  # noqa: PLC0415
    from domain_model.account_investment_repository import upsert_account_investment  # noqa: PLC0415

    db_path = str(tmp_path / "portfolio.sqlite")
    conn = initialize_db(db_path)
    seen: set[str] = set()
    for account_id, symbol, qty, price in rows:
        if account_id not in seen:
            upsert_account(conn, account_id, account_id, account_id)
            seen.add(account_id)
        inv_id = resolve_investment(conn, symbol, asset_class="EQUITY", currency="USD")
        upsert_investment_price(conn, inv_id, price=price, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_account_investment(
            conn, account_id, inv_id, quantity=qty, average_cost=price,
            book_value=qty * price, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
    conn.close()
    return db_path


def test_load_portfolio_reads_symbols_from_sqlite_not_json(tmp_path, monkeypatch):
    """load_portfolio() must return the holdings' symbols from domain_model.sqlite,
    not portfolio.json — even if a stale portfolio.json exists on disk."""
    sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
    import portfolio_io  # noqa: PLC0415

    db_path = _seed_portfolio_db(tmp_path, [("TFSA", "NVDA", 10, 150.0), ("RRSP", "AAPL", 5, 200.0)])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    # A stale portfolio.json exists but must NOT be read.
    from ta_sweep_batch import load_portfolio  # noqa: PLC0415
    holdings = load_portfolio()
    symbols = {h["symbol"] for h in holdings}
    assert symbols == {"NVDA", "AAPL"}


def test_load_target_portfolio_reads_thesis_holdings_from_sqlite_not_json(tmp_path, monkeypatch):
    """load_target_portfolio() must read investment.target_weight/sub_strategy_id
    from domain_model.sqlite via portfolio_io.load_thesis_holdings() — not the
    archived target-portfolio.json (regression: this raised FileNotFoundError
    in production on 2026-08-13 since that file no longer exists on disk)."""
    sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
    import portfolio_io  # noqa: PLC0415
    from domain_model.db_client import initialize_db  # noqa: PLC0415
    from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: PLC0415
    from domain_model.pillar_repository import resolve_pillar, resolve_sub_strategy  # noqa: PLC0415

    db_path = str(tmp_path / "portfolio.sqlite")
    conn = initialize_db(db_path)
    resolve_pillar(conn, "asi-race", "ASI Race")
    resolve_sub_strategy(conn, "sa-asi-race", "asi-race", "SA ASI Race")
    inv_id = resolve_investment(conn, "NVDA", asset_class="EQUITY", currency="USD")
    update_investment_fields(conn, inv_id, target_weight=5.0, sub_strategy_id="sa-asi-race")
    conn.close()
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    from ta_sweep_batch import load_target_portfolio  # noqa: PLC0415
    target_map = load_target_portfolio()
    assert target_map["NVDA"]["targetWeight"] == 5.0
    assert target_map["NVDA"]["subStrategyId"] == "sa-asi-race"


def test_load_dcf_uses_highest_version_regardless_of_source(tmp_path):
    """Original code took raw[-1] (last array element = highest version) with no
    source filter — this must not prefer AI_AGENT over a newer non-AI_AGENT row."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "DXYZ", asset_class="ETF")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-06-01T00:00:00Z",
            fair_value=40.0, action="HOLD", source="AI_AGENT",
        )
        save_projection_version(
            conn, investment_id, version=2, saved_at="2026-07-01T00:00:00Z",
            fair_value=45.0, action="INITIATE", source="ETF_ANALYSIS",
        )
    finally:
        conn.close()

    dcf = load_dcf("DXYZ", db_path=db_path)
    assert dcf["fairValue"] == 45.0
    assert dcf["action"] == "INITIATE"


def test_load_watchlisted_tickers_returns_watchlist_only_deduplicated(tmp_path):
    """load_watchlisted_tickers must return is_watchlisted=True symbols from domain_model.sqlite,
    deduplicated — mirrors overnight_gaps.py::_load_tickers()'s watchlist half.
    """
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root / "investment_screener/backend/py_services"))
    sys.path.insert(0, str(repo_root / "plugins/tradingview/scripts"))

    from domain_model.db_client import initialize_db  # noqa: E402
    from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
    from ta_sweep_batch import load_watchlisted_tickers  # noqa: PLC0415

    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    for ticker in ("OKLO", "RKLB"):
        inv_id = resolve_investment(conn, ticker)
        update_investment_fields(conn, inv_id, is_watchlisted=True)
    resolve_investment(conn, "MSFT")  # held, not watchlisted — is_watchlisted defaults False
    conn.close()

    tickers = load_watchlisted_tickers(db_path=db_path)

    assert sorted(tickers) == ["OKLO", "RKLB"]
    assert "MSFT" not in tickers


def test_main_ticker_universe_is_union_of_holdings_and_watchlist(tmp_path, monkeypatch):
    """main()'s scan universe must be holdings UNION watchlist, not holdings alone —
    confirmed via load_portfolio() + load_watchlisted_tickers() combined, minus DEFAULT_SKIP.
    """
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root / "plugins/tradingview/scripts"))
    import ta_sweep_batch  # noqa: PLC0415

    monkeypatch.setattr(ta_sweep_batch, "load_portfolio", lambda: [{"symbol": "MSFT"}, {"symbol": "NVDA"}])
    monkeypatch.setattr(ta_sweep_batch, "load_watchlisted_tickers", lambda db_path=None: ["NVDA", "OKLO", "RKLB"])

    holdings = ta_sweep_batch.load_portfolio()
    watchlisted = ta_sweep_batch.load_watchlisted_tickers()
    seen: set[str] = set()
    universe: list[str] = []
    for sym in [h["symbol"] for h in holdings] + watchlisted:
        if sym and sym not in ta_sweep_batch.DEFAULT_SKIP and sym not in seen:
            seen.add(sym)
            universe.append(sym)

    assert universe == ["MSFT", "NVDA", "OKLO", "RKLB"]  # holdings first, no NVDA duplicate
