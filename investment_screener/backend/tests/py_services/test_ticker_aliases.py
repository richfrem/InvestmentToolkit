"""Purpose: broker spellings of one fund resolve to a single canonical ticker.

Layer: Tests. Key Functions: alias and passthrough cases.
Key Input Dependencies: ticker_aliases.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "investment_screener/backend/py_services"))
from ticker_aliases import normalize_ticker  # noqa: E402


def test_every_broker_spelling_of_the_cash_fund_is_one_position():
    """PSU.U (TradingView), PSU.U.TO and PSUCF (Questrade activity feed) are all PSU-U.TO."""
    assert {normalize_ticker(symbol) for symbol in ("PSU.U", "PSU.U.TO", "PSUCF", "PSU-U.TO")} == {"PSU-U.TO"}


def test_other_tickers_pass_through_unchanged():
    assert normalize_ticker("ZS") == "ZS"
    assert normalize_ticker("G036247") == "G036247"  # conversion leg: deliberately not aliased


def test_both_cash_symbols_count_as_cash():
    """The broker sync stores cash as CASH_USD; older data used USD_CASH."""
    from ticker_aliases import is_cash
    assert is_cash("CASH_USD") and is_cash("CASH_CAD") and is_cash("USD_CASH") and is_cash("USD_CASH_TFSA")
    assert not is_cash("CASHX") and not is_cash("PSU-U.TO") and not is_cash("AAPL")
