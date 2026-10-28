"""
test_levels_ticker_tag.py - The AI TA Levels indicator draws a stock's levels only on that stock.

Purpose:
    The level inputs stay on the chart when the symbol changes, so a chart switched from VRT to
    HOOD showed VRT's buy and trim tiers on HOOD. The levels now carry the ticker they were drawn
    for (the "Levels for ticker" input); the indicator draws nothing, and warns, on any other ticker.

Layer: Tests / Python Services
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py_services"))

import pine_level_inputs  # noqa: E402

INDICATOR_SOURCE = pine_level_inputs.INDICATOR.read_text()


def test_indicator_has_a_ticker_input_and_it_gates_every_level():
    assert pine_level_inputs.ticker_input_title() == "Levels for ticker"
    gate = re.search(r"^is_plausible\(lvl\)\s*=>\s*(.+)$", INDICATOR_SOURCE, flags=re.M)
    assert gate and "levels_match" in gate.group(1), "every level must pass through the ticker check"
    for name in pine_level_inputs.LEVEL_INPUTS:
        assert re.search(rf"^valid_\w+\s*=\s*is_plausible\({name}\)", INDICATOR_SOURCE, flags=re.M), f"{name} bypasses the ticker check"


def test_indicator_compares_tickers_in_one_canonical_form():
    assert "canon(levels_for) == canon(syminfo.ticker)" in INDICATOR_SOURCE
    assert 'levels_for != ""' in INDICATOR_SOURCE, "levels never drawn for any ticker must draw nothing"


def test_fill_level_inputs_stamps_the_ticker(monkeypatch):
    monkeypatch.setattr(pine_level_inputs, "level_inputs", lambda symbol, db_path=None: {"target_buy1": 85.64})
    filled = pine_level_inputs.fill_level_inputs(INDICATOR_SOURCE, "hood")
    assert re.search(r'^levels_for\s*=\s*input\.string\("HOOD"', filled, flags=re.M)
    assert re.search(r"^target_buy1\s*=\s*input\.float\(85\.64", filled, flags=re.M)


def test_draw_levels_sets_the_ticker_with_the_levels(monkeypatch):
    calls = []

    def fake_tv_call(group, action, *args):
        calls.append((group, action, args))
        return {"success": True}

    import types
    monkeypatch.setitem(sys.modules, "pine_script_manager", types.SimpleNamespace(tv_call=fake_tv_call))
    monkeypatch.setattr(pine_level_inputs, "level_inputs", lambda symbol, db_path=None: {"target_buy1": 85.64})
    monkeypatch.setattr(pine_level_inputs, "known_symbol", lambda symbol, db_path=None: True)
    pine_level_inputs.draw_levels("HOOD")
    set_inputs = next(c for c in calls if c[1] == "setInputs")
    values = json.loads(set_inputs[2][set_inputs[2].index("--values") + 1])
    assert values["Levels for ticker"] == "HOOD"
    assert values["🟢 Buy Tier 1"] == 85.64


def test_follow_step_draws_only_when_the_symbol_changes():
    drawn = []
    draw = lambda symbol: drawn.append(symbol) or {"success": True}
    last = pine_level_inputs.follow_step("HOOD", None, draw)
    assert last == "HOOD" and drawn == ["HOOD"]
    assert pine_level_inputs.follow_step("HOOD", last, draw) == "HOOD" and drawn == ["HOOD"]   # unchanged: no redraw
    assert pine_level_inputs.follow_step("AAPL", last, draw) == "AAPL" and drawn == ["HOOD", "AAPL"]


def test_follow_step_ignores_an_unreadable_symbol_and_retries_a_failed_draw():
    assert pine_level_inputs.follow_step(None, "HOOD", lambda s: {"success": True}) == "HOOD"
    failing = lambda symbol: {"success": False, "error": "no indicator"}
    assert pine_level_inputs.follow_step("AAPL", "HOOD", failing) == "HOOD", "a failed draw must be retried on the next poll"


def test_known_symbol_never_creates_a_stock(tmp_path):
    import sqlite3
    db = tmp_path / "t.sqlite"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE investment (symbol TEXT)")
    conn.execute("INSERT INTO investment VALUES ('HOOD')")
    conn.commit()
    conn.close()
    assert pine_level_inputs.known_symbol("HOOD", db) is True
    assert pine_level_inputs.known_symbol("ZZZZ", db) is False
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM investment").fetchone()[0] == 1
    conn.close()
    assert pine_level_inputs.known_symbol("HOOD", tmp_path / "missing.sqlite") is False

