# BOATS Overnight Gap Scanner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pre-market/overnight gap scan to the daily brief that flags portfolio holdings and key watchlist names with extended-hours moves ≥ 2% before the TA sweep and macro regime sections run.

**Architecture:** A standalone `overnight_gaps.py` script in `py_services/` fetches extended-hours price data from yfinance using `fast_info.last_price` (which reflects extended-hours price when the regular market is closed) and compares it to `previous_close`. The script is callable as a CLI tool and importable as a module. `daily_brief.py` calls it as step 0 — before macro — and the `render()` function surfaces movers at the top of the terminal output. Ticker source is the **union of `portfolio.json` holdings and `watchlist.json`** (matching the user's curated TradingView "BOATS-mylist" of ~39 active names). Canadian tickers (`.TO`, `.V`) and futures (`NQ1!`, `GC1!`) are skipped; yfinance cannot fetch extended-hours data for them.

**Tech Stack:** Python 3.11+, yfinance, `concurrent.futures.ThreadPoolExecutor` (matching pattern in `fetch_quotes.py`), pytest with `monkeypatch` and `tmp_path` fixtures.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| **Create** | `investment_screener/backend/py_services/overnight_gaps.py` | Gap scan logic, CLI entry point |
| **Create** | `investment_screener/backend/tests/py_services/test_overnight_gaps.py` | Full unit test coverage |
| **Modify** | `plugins/portfolio-advisor/scripts/daily_brief.py` | Add step 0 in `run()`, add gap section in `render()` |

---

## Task 1: Write overnight_gaps.py

**Files:**
- Create: `investment_screener/backend/py_services/overnight_gaps.py`

- [ ] **Step 1: Write the failing import test first**

Create `investment_screener/backend/tests/py_services/test_overnight_gaps.py` with just an import smoke test:

```python
"""Tests for overnight_gaps.py — extended-hours gap scanner.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_overnight_gaps.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

import overnight_gaps  # noqa: E402


class TestImport:
    def test_module_imports(self):
        assert hasattr(overnight_gaps, "get_overnight_gaps")
        assert hasattr(overnight_gaps, "_load_tickers")
        assert hasattr(overnight_gaps, "_fetch_gap")
        assert hasattr(overnight_gaps, "_is_scannable")
```

- [ ] **Step 2: Run import test — confirm it fails**

```bash
python3 -m pytest investment_screener/backend/tests/py_services/test_overnight_gaps.py::TestImport -v
```

Expected: `ModuleNotFoundError: No module named 'overnight_gaps'`

- [ ] **Step 3: Write overnight_gaps.py**

```python
"""Overnight / extended-hours gap scanner for portfolio holdings.

Uses yfinance fast_info.last_price (which reflects extended-hours price when
the regular market is closed) vs previous_close to detect significant overnight
moves before the daily brief runs.

Usage:
    python3 overnight_gaps.py                  # scan all portfolio holdings
    python3 overnight_gaps.py NVDA,AAPL,TSLA   # explicit ticker list
    python3 overnight_gaps.py --threshold 3.0  # custom threshold (default: 2.0%)
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import yfinance as yf

REPO_ROOT      = Path(__file__).resolve().parents[3]
PORTFOLIO_PATH = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
WATCHLIST_PATH = REPO_ROOT / "investment_screener/backend/data/watchlist.json"

SKIP_SUFFIXES = (".TO", ".V")          # Canadian markets — no extended-hours data via yfinance
SKIP_PATTERNS = ("!", )                # Futures contracts (NQ1!, GC1!) — not supported by yfinance


def _is_scannable(ticker: str) -> bool:
    """Return True if ticker is a US equity that yfinance can fetch extended-hours data for.

    Args:
        ticker: Ticker symbol string.

    Returns:
        False for Canadian suffixes (.TO, .V) and futures contracts (NQ1!, GC1!).
    """
    upper = ticker.upper()
    if any(upper.endswith(s) for s in SKIP_SUFFIXES):
        return False
    if any(p in upper for p in SKIP_PATTERNS):
        return False
    return True


def _load_tickers() -> list[str]:
    """Load scannable tickers from portfolio.json union watchlist.json.

    Mirrors the user's curated TradingView BOATS-mylist: active holdings
    plus researched watchlist names, minus Canadian and futures symbols.

    Returns:
        Deduplicated list of US equity ticker symbols, order: holdings first.
    """
    seen: set[str] = set()
    tickers: list[str] = []

    if PORTFOLIO_PATH.exists():
        with open(PORTFOLIO_PATH) as f:
            for h in json.load(f).get("holdings", []):
                sym = h.get("symbol", "")
                if sym and _is_scannable(sym) and sym not in seen:
                    seen.add(sym)
                    tickers.append(sym)

    if WATCHLIST_PATH.exists():
        with open(WATCHLIST_PATH) as f:
            for entry in json.load(f).get("watchlist", []):
                sym = entry.get("ticker", "")
                if sym and _is_scannable(sym) and sym not in seen:
                    seen.add(sym)
                    tickers.append(sym)

    return tickers


def _fetch_gap(ticker: str) -> Optional[dict]:
    """Fetch extended-hours gap data for one ticker.

    Args:
        ticker: US equity ticker symbol.

    Returns:
        Gap dict with ticker, prev_close, current, change_pct, direction,
        and market_state — or None if price data is unavailable.
    """
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        current    = getattr(fi, "last_price", None)
        prev_close = getattr(fi, "previous_close", None)
        if not current or not prev_close or prev_close <= 0:
            return None
        change_pct = (current - prev_close) / prev_close * 100
        try:
            market_state = (t.info or {}).get("marketState", "UNKNOWN")
        except Exception:
            market_state = "UNKNOWN"
        return {
            "ticker":       ticker,
            "prev_close":   round(prev_close, 2),
            "current":      round(current, 2),
            "change_pct":   round(change_pct, 2),
            "direction":    "UP" if change_pct > 0 else "DOWN",
            "market_state": market_state,
        }
    except Exception:
        return None


def get_overnight_gaps(
    tickers: list[str] | None = None,
    threshold_pct: float = 2.0,
) -> list[dict]:
    """Return portfolio holdings with extended-hours moves >= threshold_pct.

    Args:
        tickers: Explicit ticker list. If None, loads US equities from portfolio.json.
        threshold_pct: Minimum absolute % move to include in results.

    Returns:
        Gap dicts sorted by abs(change_pct) descending, filtered to >= threshold_pct.
    """
    if tickers is None:
        tickers = _load_tickers()
    us_tickers = [t for t in tickers if _is_scannable(t)]
    if not us_tickers:
        return []
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(len(us_tickers), 8)) as pool:
        futures = {pool.submit(_fetch_gap, t): t for t in us_tickers}
        for future in as_completed(futures, timeout=20):
            result = future.result()
            if result and abs(result["change_pct"]) >= threshold_pct:
                results.append(result)
    return sorted(results, key=lambda x: abs(x["change_pct"]), reverse=True)


def main() -> None:
    args = sys.argv[1:]
    threshold: float = 2.0
    explicit_tickers: list[str] | None = None
    i = 0
    while i < len(args):
        if args[i] == "--threshold" and i + 1 < len(args):
            threshold = float(args[i + 1])
            i += 2
        else:
            explicit_tickers = [t.strip().upper() for t in args[i].split(",") if t.strip()]
            i += 1
    print(json.dumps(get_overnight_gaps(explicit_tickers, threshold), indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run import test — confirm it passes**

```bash
python3 -m pytest investment_screener/backend/tests/py_services/test_overnight_gaps.py::TestImport -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/overnight_gaps.py \
        investment_screener/backend/tests/py_services/test_overnight_gaps.py
git commit -m "feat: add overnight_gaps.py — extended-hours gap scanner for portfolio holdings"
```

---

## Task 2: Write all unit tests for overnight_gaps.py

**Files:**
- Modify: `investment_screener/backend/tests/py_services/test_overnight_gaps.py`

- [ ] **Step 1: Replace the test file with the full suite**

```python
"""Tests for overnight_gaps.py — extended-hours gap scanner.

The gap scanner is the first step of the daily brief. It must:
  - Skip Canadian tickers (.TO, .V) — yfinance has no extended-hours data for them
  - Filter moves below the threshold (default 2%)
  - Sort results by absolute move magnitude descending
  - Gracefully return [] when _fetch_gap returns None (bad data / network error)
  - Default to portfolio.json holdings when no explicit tickers given

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_overnight_gaps.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

import overnight_gaps  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_gap(ticker: str, change_pct: float, market_state: str = "PRE") -> dict:
    prev = 100.0
    current = round(prev * (1 + change_pct / 100), 4)
    return {
        "ticker":       ticker,
        "prev_close":   prev,
        "current":      current,
        "change_pct":   round(change_pct, 2),
        "direction":    "UP" if change_pct > 0 else "DOWN",
        "market_state": market_state,
    }


# ── _is_scannable ───────────────────────────────────────────────────────────────

class TestIsScannable:
    def test_plain_us_ticker_passes(self):
        assert overnight_gaps._is_scannable("NVDA") is True

    def test_tsx_ticker_blocked(self):
        assert overnight_gaps._is_scannable("PSU-U.TO") is False

    def test_tsx_ticker_with_dot_suffix(self):
        assert overnight_gaps._is_scannable("SHOP.TO") is False

    def test_venture_exchange_blocked(self):
        assert overnight_gaps._is_scannable("XYZ.V") is False

    def test_check_is_case_insensitive(self):
        assert overnight_gaps._is_scannable("abc.to") is False

    def test_ticker_with_dot_in_name_but_not_suffix_passes(self):
        # BRK.B ends in .B, not a blocked suffix
        assert overnight_gaps._is_scannable("BRK.B") is True


# ── _load_tickers ─────────────────────────────────────────────────────────────

class TestLoadTickers:
    def test_returns_portfolio_and_watchlist_union(self, tmp_path: Path, monkeypatch):
        portfolio = {"holdings": [{"symbol": "NVDA"}, {"symbol": "AAPL"}]}
        watchlist = {"watchlist": [{"ticker": "AAPL"}, {"ticker": "TSLA"}]}
        port_p = tmp_path / "portfolio.json"
        watch_p = tmp_path / "watchlist.json"
        port_p.write_text(json.dumps(portfolio))
        watch_p.write_text(json.dumps(watchlist))
        monkeypatch.setattr(overnight_gaps, "PORTFOLIO_PATH", port_p)
        monkeypatch.setattr(overnight_gaps, "WATCHLIST_PATH", watch_p)
        assert overnight_gaps._load_tickers() == ["NVDA", "AAPL", "TSLA"]

    def test_missing_both_files_returns_empty(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(overnight_gaps, "PORTFOLIO_PATH", tmp_path / "nope.json")
        monkeypatch.setattr(overnight_gaps, "WATCHLIST_PATH", tmp_path / "nope2.json")
        assert overnight_gaps._load_tickers() == []

    def test_missing_watchlist_still_returns_portfolio(self, tmp_path: Path, monkeypatch):
        portfolio = {"holdings": [{"symbol": "AAPL"}]}
        port_p = tmp_path / "portfolio.json"
        port_p.write_text(json.dumps(portfolio))
        monkeypatch.setattr(overnight_gaps, "PORTFOLIO_PATH", port_p)
        monkeypatch.setattr(overnight_gaps, "WATCHLIST_PATH", tmp_path / "missing.json")
        assert overnight_gaps._load_tickers() == ["AAPL"]


# ── get_overnight_gaps ────────────────────────────────────────────────────────

class TestGetOvernightGaps:
    def test_filters_move_below_threshold(self, monkeypatch):
        """1% move must be excluded when threshold is 2%."""
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", lambda t: _make_gap(t, 1.0))
        result = overnight_gaps.get_overnight_gaps(["AAPL"], threshold_pct=2.0)
        assert result == []

    def test_includes_move_at_threshold(self, monkeypatch):
        """Exactly 2.0% move must be included at 2.0% threshold."""
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", lambda t: _make_gap(t, 2.0))
        result = overnight_gaps.get_overnight_gaps(["NVDA"], threshold_pct=2.0)
        assert len(result) == 1
        assert result[0]["ticker"] == "NVDA"

    def test_includes_negative_move_above_threshold(self, monkeypatch):
        """Threshold is applied on absolute value — a -3% drop must be included."""
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", lambda t: _make_gap(t, -3.0))
        result = overnight_gaps.get_overnight_gaps(["TSLA"], threshold_pct=2.0)
        assert len(result) == 1
        assert result[0]["direction"] == "DOWN"

    def test_sorted_by_absolute_magnitude_descending(self, monkeypatch):
        """Largest absolute move must appear first; direction irrelevant."""
        data = {"NVDA": 2.5, "AAPL": -5.1, "TSLA": 3.0}
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", lambda t: _make_gap(t, data[t]))
        result = overnight_gaps.get_overnight_gaps(list(data.keys()), threshold_pct=2.0)
        magnitudes = [abs(r["change_pct"]) for r in result]
        assert magnitudes == sorted(magnitudes, reverse=True)
        assert result[0]["ticker"] == "AAPL"  # -5.1% is largest absolute

    def test_canadian_tickers_never_reach_fetch(self, monkeypatch):
        """PSU-U.TO must be filtered before _fetch_gap is called."""
        called_with: list[str] = []

        def spy(t: str):
            called_with.append(t)
            return _make_gap(t, 5.0)

        monkeypatch.setattr(overnight_gaps, "_fetch_gap", spy)
        overnight_gaps.get_overnight_gaps(["NVDA", "PSU-U.TO", "SHOP.TO"], threshold_pct=0.0)
        assert "PSU-U.TO" not in called_with
        assert "SHOP.TO" not in called_with
        assert "NVDA" in called_with

    def test_none_from_fetch_does_not_crash(self, monkeypatch):
        """_fetch_gap returning None (network error / bad data) must yield empty list."""
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", lambda t: None)
        result = overnight_gaps.get_overnight_gaps(["NVDA"], threshold_pct=0.0)
        assert result == []

    def test_empty_ticker_list_returns_empty(self, monkeypatch):
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", lambda t: _make_gap(t, 5.0))
        assert overnight_gaps.get_overnight_gaps([], threshold_pct=0.0) == []

    def test_defaults_to_portfolio_plus_watchlist(self, tmp_path: Path, monkeypatch):
        """With tickers=None, reads from both PORTFOLIO_PATH and WATCHLIST_PATH."""
        portfolio = {"holdings": [{"symbol": "MSFT"}]}
        watchlist = {"watchlist": [{"ticker": "COIN"}]}
        port_p = tmp_path / "portfolio.json"
        watch_p = tmp_path / "watchlist.json"
        port_p.write_text(json.dumps(portfolio))
        watch_p.write_text(json.dumps(watchlist))
        monkeypatch.setattr(overnight_gaps, "PORTFOLIO_PATH", port_p)
        monkeypatch.setattr(overnight_gaps, "WATCHLIST_PATH", watch_p)
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", lambda t: _make_gap(t, 4.0))
        result = overnight_gaps.get_overnight_gaps(threshold_pct=0.0)
        tickers_found = {r["ticker"] for r in result}
        assert "MSFT" in tickers_found
        assert "COIN" in tickers_found
```

- [ ] **Step 2: Run the full test suite — confirm all pass**

```bash
python3 -m pytest investment_screener/backend/tests/py_services/test_overnight_gaps.py -v
```

Expected: `8 passed` (1 from Task 1 TestImport + 7 new tests, counting class methods)

> **Note**: All tests mock or monkeypatch `_fetch_gap` and use `tmp_path` for file I/O — no network calls or real yfinance hits. The full suite runs offline in under 2 seconds.

- [ ] **Step 3: Commit**

```bash
git add investment_screener/backend/tests/py_services/test_overnight_gaps.py
git commit -m "test: full unit test suite for overnight_gaps.py"
```

---

## Task 3: Integrate overnight gap scan into daily_brief.py run()

**Files:**
- Modify: `plugins/portfolio-advisor/scripts/daily_brief.py`

- [ ] **Step 1: Add the import and step 0 to run()**

In `daily_brief.py`, locate the `run()` function. The dynamic imports block is at line ~164:

```python
    # Dynamically import py_services modules
    sys.path.insert(0, str(PY_SERVICES))
    from macro_regime import get_macro_regime
    from earnings_calendar import get_earnings_calendar
    from compute_conviction_scores import compute_all
    from brief_recommendations import build_recommendations, load_standing_decisions
```

Add `overnight_gaps` to that import block:

```python
    # Dynamically import py_services modules
    sys.path.insert(0, str(PY_SERVICES))
    from macro_regime import get_macro_regime
    from earnings_calendar import get_earnings_calendar
    from compute_conviction_scores import compute_all
    from brief_recommendations import build_recommendations, load_standing_decisions
    from overnight_gaps import get_overnight_gaps
```

Then immediately after the imports (before `# ── 1. Macro regime`), add step 0:

```python
    # ── 0. Overnight gap scan ─────────────────────────────────────────────────
    print("▶ Overnight gap scan...", file=sys.stderr)
    try:
        gaps = get_overnight_gaps()
    except Exception:
        gaps = []
```

- [ ] **Step 2: Add overnight_gaps to the brief dict**

Find the `brief: dict[str, Any] = {` block (~line 248). Add the new key at the top:

```python
    brief: dict[str, Any] = {
        "date": date.today().isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overnight_gaps": gaps,
        "macro_regime": asdict(macro),
        ...
    }
```

- [ ] **Step 3: Verify the script runs end-to-end without error**

```bash
python3 plugins/portfolio-advisor/scripts/daily_brief.py --skip-ta --json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('overnight_gaps key present:', 'overnight_gaps' in d)
print('type:', type(d['overnight_gaps']))
"
```

Expected:
```
overnight_gaps key present: True
type: <class 'list'>
```

- [ ] **Step 4: Commit**

```bash
git add plugins/portfolio-advisor/scripts/daily_brief.py
git commit -m "feat: add overnight gap scan as step 0 in daily_brief.run()"
```

---

## Task 4: Add overnight gaps section to render()

**Files:**
- Modify: `plugins/portfolio-advisor/scripts/daily_brief.py`

- [ ] **Step 1: Add the render section**

In `render()`, locate the header block (around line 307):

```python
    lines += [f"\n{'═' * W}", f"  DAILY PORTFOLIO BRIEF — {today}  (prev: {yesterday})", f"{'═' * W}"]

    # ── Macro ─────────────────────────────────────────────────────────────────
```

Insert the overnight gaps section between the header and the macro section:

```python
    lines += [f"\n{'═' * W}", f"  DAILY PORTFOLIO BRIEF — {today}  (prev: {yesterday})", f"{'═' * W}"]

    # ── Overnight gaps ────────────────────────────────────────────────────────
    gaps = brief.get("overnight_gaps", [])
    if gaps:
        lines.append(f"\n🌙  OVERNIGHT GAPS — {len(gaps)} mover(s) ≥2%:")
        for g in gaps:
            icon  = "🟢" if g["direction"] == "UP" else "🔴"
            state = g.get("market_state", "")
            lines.append(
                f"    {icon} {g['ticker']:<8}  {g['change_pct']:>+6.1f}%"
                f"  (${g['current']:.2f} vs ${g['prev_close']:.2f})  {state}"
            )

    # ── Macro ─────────────────────────────────────────────────────────────────
```

- [ ] **Step 2: Smoke test render output**

```bash
python3 -c "
import sys
sys.path.insert(0, 'plugins/portfolio-advisor/scripts')
from daily_brief import render

fake_brief = {
    'date': '2026-06-14',
    'yesterday_date': '2026-06-13',
    'overnight_gaps': [
        {'ticker': 'NVDA', 'direction': 'DOWN', 'change_pct': -4.1, 'current': 148.20, 'prev_close': 154.52, 'market_state': 'PRE'},
        {'ticker': 'CRWV', 'direction': 'UP',   'change_pct':  6.2, 'current':  43.10, 'prev_close':  40.59, 'market_state': 'PRE'},
    ],
    'macro_regime': {'regime': 'NEUTRAL', 'score': 0, 'details': []},
    'ta_refreshed': False, 'ta_skip_reason': '', 'conviction_scores': [],
    'recommendations': [], 'total_equity': 0, 'score_deltas': {},
    'pillar_health': [], 'pillar_deltas': {}, 'earnings_flags': [],
}
output = render(fake_brief)
assert '🌙' in output, 'Missing overnight gaps section'
assert 'NVDA' in output
assert 'CRWV' in output
assert '-4.1%' in output
print('render() output OK')
print(output)
"
```

Expected: prints the full brief with the overnight gap section at the top showing NVDA and CRWV.

- [ ] **Step 3: Commit**

```bash
git add plugins/portfolio-advisor/scripts/daily_brief.py
git commit -m "feat: render overnight gaps at top of daily brief output"
```

---

## Task 5: Smoke test the full daily loop integration

**Files:**
- No new files — validates the full pipeline end-to-end.

- [ ] **Step 1: Run the full daily brief and verify gap output**

```bash
python3 plugins/portfolio-advisor/scripts/daily_brief.py --skip-ta 2>&1 | head -30
```

Expected output starts with:
```
▶ Overnight gap scan...
▶ Macro regime...
▶ Conviction scores...
...

════════════════...
  DAILY PORTFOLIO BRIEF — 2026-06-14  (prev: ...)
════════════════...

🌙  OVERNIGHT GAPS — N mover(s) ≥2%:    ← appears if any holdings moved ≥2%
    🔴 TICKER    -X.X%  ($XXX.XX vs $XXX.XX)  PRE
```

> If no holdings have moved ≥2% overnight, the gap section is silently omitted — that's correct behavior.

- [ ] **Step 2: Verify standalone CLI still works**

```bash
python3 investment_screener/backend/py_services/overnight_gaps.py NVDA,AAPL --threshold 0.5 | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Returned {len(data)} results')
for r in data:
    print(f'  {r[\"ticker\"]}: {r[\"change_pct\"]:+.1f}%  ({r[\"market_state\"]})')
"
```

Expected: lists current extended-hours moves for NVDA and AAPL (values depend on live market data).

- [ ] **Step 3: Run full test suite to confirm no regressions**

```bash
python3 -m pytest investment_screener/backend/tests/py_services/ -v
```

Expected: all existing tests + new overnight_gaps tests pass.

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "test: verify overnight gap scanner integration in daily brief pipeline"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Standalone CLI (`overnight_gaps.py NVDA,AAPL --threshold 3.0`) — Task 1
- ✅ Filters Canadian tickers and futures — Task 1 (`_is_scannable`), tested Task 2
- ✅ Threshold filtering — Task 1 (`get_overnight_gaps`), tested Task 2
- ✅ Sort by magnitude descending — Task 1, tested Task 2
- ✅ Graceful None handling — Task 1, tested Task 2
- ✅ Defaults to portfolio.json — Task 1 (`_load_tickers`), tested Task 2
- ✅ Integration in `daily_brief.run()` — Task 3
- ✅ Rendered at top of terminal output — Task 4
- ✅ Full pipeline smoke test — Task 5

**Placeholder scan:** No TBD, TODO, or placeholder text in any step.

**Type consistency:** `get_overnight_gaps` returns `list[dict]`. `brief["overnight_gaps"]` is that same `list[dict]`. `render()` iterates with `g["direction"]`, `g["change_pct"]`, `g["current"]`, `g["prev_close"]`, `g["market_state"]` — all match the `_fetch_gap` return schema.
