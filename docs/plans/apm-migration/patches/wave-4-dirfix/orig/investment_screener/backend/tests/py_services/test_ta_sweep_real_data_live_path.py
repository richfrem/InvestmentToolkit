"""Wave 5B remediation: proves the TA sweep read path works against real, main-checkout
data -- not only tmp_path fixtures -- per the design spec's Definition of Done item 8
("Tests prove live path behavior against real data, not only fixture behavior.").

Read-only against the real intelligence.sqlite -- never writes to it. Skips gracefully
when that file isn't present (fresh checkout, CI, or a machine that hasn't run a real
sweep yet) -- it's real production data, gitignored, never guaranteed to exist.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
REAL_DB_PATH = REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))

pytestmark = pytest.mark.skipif(
    not REAL_DB_PATH.exists(),
    reason="real intelligence.sqlite not present on this checkout (gitignored data file)",
)


def test_load_ta_returns_real_technical_sweep_data():
    from compute_conviction_scores import _load_ta  # noqa: PLC0415

    ta_map, stale_days = _load_ta(db_path=str(REAL_DB_PATH))
    assert len(ta_map) > 0, "expected at least one real TECHNICAL_SWEEP row in main's ledger"
    sample_ticker, sample_row = next(iter(ta_map.items()))
    assert isinstance(sample_ticker, str) and sample_ticker.isupper()
    assert "rsi" in sample_row or "close" in sample_row
    assert stale_days is not None and stale_days >= 0


def test_ta_age_hours_returns_real_age():
    from daily_brief import _ta_age_hours  # noqa: PLC0415

    age = _ta_age_hours(db_path=str(REAL_DB_PATH))
    assert age is not None and age >= 0


def test_load_latest_ta_sweep_count_matches_load_ta_ticker_count():
    from compute_conviction_scores import _load_ta  # noqa: PLC0415
    from daily_brief import _load_latest_ta_sweep_count  # noqa: PLC0415

    count = _load_latest_ta_sweep_count(db_path=str(REAL_DB_PATH))
    ta_map, _ = _load_ta(db_path=str(REAL_DB_PATH))
    assert count is not None and count > 0
    # count is scoped to the most recent scan's effective_at date; ta_map is "latest
    # row per ticker across all history" -- so count is always <= len(ta_map).
    assert count <= len(ta_map)
