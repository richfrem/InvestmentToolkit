"""Tests for app_smoke_test.py helpers (the full run needs the real databases and a running backend)."""
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/toolkit-manager/scripts"))

import app_smoke_test as smoke  # noqa: E402


def test_a_matching_response_passes():
    probe = smoke.Probe("/x", json_type=dict, keys=("a",))
    assert smoke.check_probe(probe, 200, {"a": 1}) is None


def test_wrong_status_type_or_missing_key_fail_with_a_reason():
    probe = smoke.Probe("/x", json_type=dict, keys=("a",))
    assert "status 500" in smoke.check_probe(probe, 500, {})
    assert "expected" in smoke.check_probe(probe, 200, [])
    assert "missing keys ['a']" in smoke.check_probe(probe, 200, {"b": 1})


def test_an_allowed_non_200_status_is_not_body_checked():
    probe = smoke.Probe("/x", (200, 404), json_type=dict, keys=("a",))
    assert smoke.check_probe(probe, 404, {"error": "none"}) is None


def test_every_probe_is_a_read_route_under_a_known_prefix():
    prefixes = ("/health", "/api/")
    assert all(p.path.startswith(prefixes) for p in smoke.PROBES)
    assert all(p.path not in {"/api/portfolio/refresh-prices"} for p in smoke.PROBES)


def test_copy_databases_copies_content_and_replaces_stale_files(tmp_path):
    source, dest = tmp_path / "source", tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    for name in smoke.DATABASES:
        conn = sqlite3.connect(str(source / name))
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (7)")
        conn.commit()
        conn.close()
    (dest / "domain_model.sqlite").write_text("stale")
    copied = smoke.copy_databases(source, dest)
    assert sorted(copied) == sorted(smoke.DATABASES)
    assert sqlite3.connect(str(dest / "intelligence.sqlite")).execute("SELECT x FROM t").fetchone()[0] == 7
    assert sqlite3.connect(str(dest / "domain_model.sqlite")).execute("SELECT x FROM t").fetchone()[0] == 7


def test_copy_never_modifies_the_source(tmp_path):
    source, dest = tmp_path / "source", tmp_path / "dest"
    source.mkdir()
    conn = sqlite3.connect(str(source / "domain_model.sqlite"))
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.commit()
    conn.close()
    before = (source / "domain_model.sqlite").read_bytes()
    smoke.copy_databases(source, dest)
    assert (source / "domain_model.sqlite").read_bytes() == before


def test_the_main_checkout_is_not_a_worktree_and_refuses_to_run(tmp_path):
    (tmp_path / ".git").mkdir()
    assert smoke.is_worktree(tmp_path) is False
    linked = tmp_path / "linked"
    linked.mkdir()
    (linked / ".git").write_text("gitdir: /somewhere")
    assert smoke.is_worktree(linked) is True


def test_key_values_summarises_the_headline_numbers():
    lines = smoke.key_values({
        "/api/portfolio/summary": {"positionCount": 26, "totalMarketValueUSD": 33714.46, "ytdAvailable": True, "price_source": "x"},
        "/api/screener/all-holdings": [{"hasValuation": True}, {"hasValuation": False}],
        "/api/research": {"reports": [1, 2, 3]},
    })
    assert any("26 positions" in l and "33,714.46" in l for l in lines)
    assert any("2 tickers, 1 with a valuation" in l for l in lines)
    assert any("3 reports" in l for l in lines)


def test_a_null_where_the_screen_needs_a_number_fails_the_probe():
    probe = smoke.Probe("/summary", json_type=dict, keys=("a",), numbers=("a",))
    assert smoke.check_probe(probe, 200, {"a": 1.5}) is None
    assert "not a number: ['a']" in smoke.check_probe(probe, 200, {"a": None})
    assert "not a number" in smoke.check_probe(probe, 200, {"a": "1"})


def test_the_summary_probe_requires_numeric_rates_and_totals():
    summary = next(p for p in smoke.PROBES if p.path == "/api/portfolio/summary")
    assert {"jan1UsdCadRate", "liveUsdCadRate", "totalMarketValueUSD"} <= set(summary.numbers)
