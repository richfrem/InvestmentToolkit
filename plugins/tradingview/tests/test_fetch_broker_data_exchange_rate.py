import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from fetch_broker_data import _compute_exchange_rate_from_snapshot  # noqa: E402


def test_exchange_rate_respects_real_zero_combined_total():
    """Replicates TS `??` semantics: totalEquityCADCombined: 0.0 is a real,
    legitimate zero-equity value and must be used as-is, not silently replaced
    by the non-combined totalEquityCAD fallback field the way Python's falsy
    `or` operator would do. Both totals must be positive for a rate to be
    returned, so pair the 0.0 CAD combined total with a normal USD side and
    assert the function correctly refuses to produce a rate from a real
    zero -- exactly matching what `cad ?? fallback` would do in TypeScript
    (use the 0.0, not the fallback), as opposed to `cad || fallback` (which
    would wrongly fall through to totalEquityCAD).
    """
    snapshot = {
        "snapshots": [
            {
                "balances": {
                    "totalEquityCADCombined": 0.0,
                    "totalEquityCAD": 5000.0,  # must NOT be used -- combined is a real 0.0
                    "totalEquityUSDCombined": 1000.0,
                    "totalEquityUSD": 1000.0,
                }
            }
        ]
    }

    rate = _compute_exchange_rate_from_snapshot(snapshot)

    # total_cad correctly stays 0.0 (the real combined value), not 5000.0 (the
    # fallback field) -- so total_cad > 0 fails and no rate is returned. The
    # buggy `or`-based version would instead sum total_cad = 5000.0 and return
    # a spurious rate of 5.0.
    assert rate is None


def test_exchange_rate_uses_combined_when_present_and_nonzero():
    """Sanity check the normal path still works: real positive combined totals
    on both sides produce the expected ratio, unaffected by the coalescing fix.
    """
    snapshot = {
        "snapshots": [
            {
                "balances": {
                    "totalEquityCADCombined": 1380.0,
                    "totalEquityCAD": 999.0,
                    "totalEquityUSDCombined": 1000.0,
                    "totalEquityUSD": 111.0,
                }
            }
        ]
    }

    rate = _compute_exchange_rate_from_snapshot(snapshot)

    assert rate == 1.38


def test_exchange_rate_falls_back_to_non_combined_when_combined_missing():
    """When totalEquityCADCombined/USDCombined are absent (None) entirely --
    not present as a real 0.0 -- the fallback to totalEquityCAD/USD must still
    work, matching TS `??`'s "fall through only on null/undefined" behavior.
    """
    snapshot = {
        "snapshots": [
            {
                "balances": {
                    "totalEquityCAD": 1380.0,
                    "totalEquityUSD": 1000.0,
                }
            }
        ]
    }

    rate = _compute_exchange_rate_from_snapshot(snapshot)

    assert rate == 1.38
