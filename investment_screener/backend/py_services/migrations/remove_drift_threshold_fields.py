#!/usr/bin/env python3
"""
migrations/remove_drift_threshold_fields.py
=====================================

Purpose:
    One-time cleanup: removes globalSettings.driftThresholdPct and
    globalSettings.criticalDriftPct from the thesis document. The portfolio
    policy's bandConfig is the single source of truth for drift-band
    thresholds, read by both rebalancer.py and ThesisService.ts. Idempotent —
    safe to run more than once.

Layer: Backend / Python Services / Migrations

Usage:
    python3 investment_screener/backend/py_services/migrations/remove_drift_threshold_fields.py
"""
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from update_thesis import load_thesis, save_thesis  # noqa: E402

RETIRED_FIELDS = ("driftThresholdPct", "criticalDriftPct")


def strip_drift_threshold_fields(data: dict[str, Any]) -> list[str]:
    """Removes the two drift-threshold fields from globalSettings, in place.

    Args:
        data: Parsed thesis document (globalSettings).

    Returns:
        List of field names actually removed (empty if already absent —
        callers use this to skip the save_thesis() call/version bump when
        there's nothing to do).
    """
    settings = data.get("globalSettings", {})
    removed = [k for k in RETIRED_FIELDS if k in settings]
    for key in removed:
        del settings[key]
    return removed


def main() -> None:
    data = load_thesis()
    removed = strip_drift_threshold_fields(data)
    if not removed:
        print("Nothing to migrate — fields already absent.")
        return
    save_thesis(
        data, dry_run=False,
        note=f"E2 migration: removed globalSettings.{', '.join(removed)} — "
             f"drift-band config now lives in the portfolio policy's bandConfig.",
    )


if __name__ == "__main__":
    main()
