"""Grade predictions — E3 weekly grading job.

Finds every matured, ungraded prediction and appends a grade record based on
realized ticker return vs. SPY return since the claim's basePrice. Never
mutates predictions.jsonl — grading only appends to predictions_graded.jsonl.

Usage:
    python3 grade_predictions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prediction_ledger import (  # noqa: E402
    GRADED_PATH,
    PREDICTIONS_PATH,
    append_grade,
    grade_claim,
    load_graded,
    load_predictions,
)


def find_maturable_predictions(
    predictions: list[dict[str, Any]], graded_ids: set[str], today: date
) -> list[dict[str, Any]]:
    """Return predictions whose horizon has elapsed and that aren't graded yet.

    Args:
        predictions: All prediction records loaded from predictions.jsonl.
        graded_ids: Prediction ids that already have a grade record, to skip.
        today: The date to evaluate maturity against.

    Returns:
        Prediction records whose claimDate + horizonDays has elapsed and
        that have no existing grade record.
    """
    result = []
    for p in predictions:
        if p["id"] in graded_ids:
            continue
        claim_date = date.fromisoformat(p["date"])
        matures_on = claim_date + timedelta(days=p["horizonDays"])
        if today >= matures_on:
            result.append(p)
    return result


def grade_prediction(
    prediction: dict[str, Any], ticker_price_now: float, spy_price_now: float, graded_at: str
) -> dict[str, Any]:
    """Compute a grade record for one matured prediction from current prices.

    Args:
        prediction: The prediction record being graded (needs id, basePrice,
            baseSpyPrice, and direction).
        ticker_price_now: Current price of the prediction's ticker.
        spy_price_now: Current price of SPY, used as the market baseline.
        graded_at: ISO date string to stamp this grade record with.

    Returns:
        A grade record dict with tickerReturn, spyReturn, relativeReturn,
        and verdict, ready to append to predictions_graded.jsonl.
    """
    ticker_return = (ticker_price_now - prediction["basePrice"]) / prediction["basePrice"]
    spy_return = (spy_price_now - prediction["baseSpyPrice"]) / prediction["baseSpyPrice"]
    relative_return = ticker_return - spy_return
    verdict = grade_claim(prediction["direction"], relative_return)
    return {
        "v": 1,
        "predictionId": prediction["id"],
        "gradedAt": graded_at,
        "tickerReturn": round(ticker_return, 4),
        "spyReturn": round(spy_return, 4),
        "relativeReturn": round(relative_return, 4),
        "verdict": verdict,
    }


def _fetch_current_prices(ticker: str) -> tuple[float, float] | None:
    """Fetch (ticker, SPY) current quote prices via market_data.get_quote().

    Args:
        ticker: Ticker symbol to fetch alongside SPY.

    Returns:
        A (ticker_price, spy_price) tuple, or None if either quote is
        unavailable.
    """
    from market_data import get_quote
    result = get_quote([ticker, "SPY"])
    t = result.get(ticker, {}).get("price")
    s = result.get("SPY", {}).get("price")
    if t is None or s is None:
        return None
    return t, s


def run_grading(
    predictions_path: Path = PREDICTIONS_PATH, graded_path: Path = GRADED_PATH
) -> list[dict[str, Any]]:
    """Find matured, ungraded predictions and append a grade record for each.

    Args:
        predictions_path: Ledger path to read prediction records from.
        graded_path: Ledger path to read existing grades from and append
            new grade records to.

    Returns:
        Every newly appended grade record this run. Predictions whose
        current price lookup fails are skipped (not graded) and left for
        a future run to retry.
    """
    predictions = load_predictions(predictions_path)
    graded_ids = {g["predictionId"] for g in load_graded(graded_path)}
    today = date.today()

    new_grades: list[dict[str, Any]] = []
    for prediction in find_maturable_predictions(predictions, graded_ids, today):
        prices = _fetch_current_prices(prediction["ticker"])
        if prices is None:
            print(f"  Grading skipped for {prediction['id']}: price lookup failed", file=sys.stderr)
            continue
        ticker_price_now, spy_price_now = prices
        grade = grade_prediction(prediction, ticker_price_now, spy_price_now, today.isoformat())
        append_grade(grade, graded_path)
        new_grades.append(grade)
    return new_grades


def main() -> None:
    """CLI entrypoint: grade matured predictions, or report matured count in --dry-run mode.

    Returns:
        None. Prints a summary line to stdout; writes new grade records to
        GRADED_PATH unless --dry-run is passed.
    """
    parser = argparse.ArgumentParser(description="Grade matured predictions")
    parser.add_argument("--dry-run", action="store_true", help="Report matured count, don't write")
    args = parser.parse_args()

    if args.dry_run:
        predictions = load_predictions(PREDICTIONS_PATH)
        graded_ids = {g["predictionId"] for g in load_graded(GRADED_PATH)}
        matured = find_maturable_predictions(predictions, graded_ids, date.today())
        print(f"{len(matured)} prediction(s) ready to grade. Dry-run: no writes performed.")
        return

    new_grades = run_grading()
    print(f"Graded {len(new_grades)} prediction(s).")


if __name__ == "__main__":
    main()
