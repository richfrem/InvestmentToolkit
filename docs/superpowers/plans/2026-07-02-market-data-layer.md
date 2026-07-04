# Market Data Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `py_services/market_data.py` — a single, cached, source-tagged, quality-gated interface for prices, quotes, estimates, and fundamentals — with SEC EDGAR as a point-in-time-correct fundamentals source alongside yfinance.

**Architecture:** `market_data.py` exposes four pure-ish functions (`get_prices`, `get_quote`, `get_estimates`, `get_fundamentals`). Only `get_fundamentals()` has a real multi-provider waterfall (EDGAR primary, yfinance supplement); the other three are cached, quality-gated wrappers around their one real provider. Every returned field carries `{"value", "source", "asOf"}`. Caching (`cache.py`) and quality-gating (`data_quality.py`) are shared internal modules, not part of the public interface.

**Tech Stack:** Python stdlib + `yfinance` (existing dependency) + `requests` (existing dependency, already pinned in `requirements.txt` — no `pip-compile` needed) + `pytest`.

## Global Constraints

- TDD: every function has a failing test written first (per `.agent/rules/test-driven-development.md`).
- No inline math/logic duplication: all financial calculation lives in `py_services/`, never recomputed inline by an agent.
- No new dependencies: `requests` and `yfinance` are already pinned; do not run `pip install` or edit `requirements.in` for this plan.
- Missing data must never silently become `0` or get dropped — per `.agent/rules/no-silent-nan-to-zero.md`. A missing field is *absent from the response dict*, never present-and-wrong.
- Source-tagging convention: `{"value": X, "source": "edgar"|"yfinance"|"tv_cdp"|"cache", "asOf": "<iso date>"}` on every returned field — matches the `totalSource` pattern already shipped in `portfolioSnapshot.ts`.
- SEC EDGAR fair-access: declared `User-Agent` header, ≤10 requests/second.
- This plan covers the **core data layer only** (Tasks 1–8). The 13-file migration of existing callers (`fetch_financials.py`, `portfolio_performance.py`, etc.) onto this layer is intentionally a **separate follow-up plan** — those migrations need each file read fresh to write accurate before/after steps, and at least one (`fetch_financials.py`) has its own bespoke cache (`plugins/stock-valuation/scripts/cache/`, 1hr TTL) that must be *replaced*, not duplicated, by the shared `cache.py` — a decision for that plan, not this one.

---

### Task 1: `cache.py` — shared TTL cache

**Files:**
- Create: `investment_screener/backend/py_services/cache.py`
- Test: `investment_screener/backend/tests/py_services/test_cache.py`

**Interfaces:**
- Produces: `cache_get(key: str, data_class: str) -> dict | None`, `cache_set(key: str, data_class: str, value: dict) -> None`, `CACHE_TTL_SECONDS: dict[str, int]` (module-level constant: `{"quote": 900, "ohlcv": 86400, "fundamentals": 86400, "edgar": 604800}`).
- Consumes: nothing (no dependencies on other new modules).

- [ ] **Step 1: Write the failing tests**

```python
# investment_screener/backend/tests/py_services/test_cache.py
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from cache import cache_get, cache_set, CACHE_TTL_SECONDS  # noqa: E402


def test_cache_set_then_get_returns_the_value(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    cache_set("AAPL", "quote", {"price": 200.0})
    result = cache_get("AAPL", "quote")
    assert result == {"price": 200.0}


def test_cache_get_returns_none_when_key_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    assert cache_get("MISSING", "quote") is None


def test_cache_get_returns_none_when_entry_is_older_than_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    cache_set("AAPL", "quote", {"price": 200.0})
    # quote TTL is 900s — simulate an entry written 1000s ago
    cache_file = tmp_path / "quote_AAPL.json"
    old_time = time.time() - 1000
    import os
    os.utime(cache_file, (old_time, old_time))
    assert cache_get("AAPL", "quote") is None


def test_cache_ttl_seconds_has_all_four_data_classes():
    assert CACHE_TTL_SECONDS["quote"] == 900
    assert CACHE_TTL_SECONDS["ohlcv"] == 86400
    assert CACHE_TTL_SECONDS["fundamentals"] == 86400
    assert CACHE_TTL_SECONDS["edgar"] == 604800


def test_cache_set_creates_cache_dir_if_missing(tmp_path, monkeypatch):
    target_dir = tmp_path / "nested" / "cache"
    monkeypatch.setattr("cache.CACHE_DIR", target_dir)
    cache_set("AAPL", "quote", {"price": 200.0})
    assert target_dir.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/richardfremmerlid/Projects/InvestmentToolkit && python3 -m pytest investment_screener/backend/tests/py_services/test_cache.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cache'`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/cache.py
"""
cache.py (Python Service)
=====================================

Purpose:
    Shared TTL-based JSON file cache for market_data.py. One cache entry per
    (key, data_class) pair. Callers pass --no-cache upstream to bypass reads
    (still writes, so a subsequent call is warm).

Layer: Backend / Python Services / Data Layer
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "data" / "cache"

CACHE_TTL_SECONDS = {
    "quote": 900,          # 15 min
    "ohlcv": 86400,         # 24h
    "fundamentals": 86400,  # 24h
    "edgar": 604800,        # 7d
}


def _cache_path(key: str, data_class: str) -> Path:
    safe_key = "".join(c for c in key if c.isalnum() or c in ("-", "."))
    return CACHE_DIR / f"{data_class}_{safe_key}.json"


def cache_get(key: str, data_class: str) -> Optional[dict]:
    path = _cache_path(key, data_class)
    if not path.exists():
        return None
    ttl = CACHE_TTL_SECONDS.get(data_class, 3600)
    age = time.time() - os.path.getmtime(path)
    if age > ttl:
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def cache_set(key: str, data_class: str, value: dict) -> None:
    path = _cache_path(key, data_class)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(value, f)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_cache.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/cache.py investment_screener/backend/tests/py_services/test_cache.py
git commit -m "feat: add shared TTL cache for market_data.py"
```

---

### Task 2: `market_data.py` skeleton + `get_prices()`

**Files:**
- Create: `investment_screener/backend/py_services/market_data.py`
- Test: `investment_screener/backend/tests/py_services/test_market_data_prices.py`

**Interfaces:**
- Consumes: `cache_get`, `cache_set` from `cache.py` (Task 1).
- Produces: `get_prices(tickers: list[str], period: str, interval: str = "1d") -> dict[str, dict]`. Each value: `{"data": list[dict], "source": "yfinance"|"cache", "asOf": iso_date}`. `data` is a list of `{"date": iso_date, "open": float, "high": float, "low": float, "close": float, "volume": int}` rows.

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_market_data_prices.py
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import get_prices  # noqa: E402


def _fake_yf_download():
    idx = pd.to_datetime(["2026-07-01", "2026-07-02"])
    cols = pd.MultiIndex.from_tuples(
        [("Open", "AAPL"), ("High", "AAPL"), ("Low", "AAPL"), ("Close", "AAPL"), ("Volume", "AAPL")]
    )
    return pd.DataFrame(
        [[199.0, 201.0, 198.0, 200.0, 1000000], [200.0, 203.0, 199.5, 202.0, 1200000]],
        index=idx, columns=cols,
    )


def test_get_prices_returns_source_tagged_ohlcv(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    with patch("market_data.yf.download", return_value=_fake_yf_download()):
        result = get_prices(["AAPL"], period="5d")

    assert result["AAPL"]["source"] == "yfinance"
    assert len(result["AAPL"]["data"]) == 2
    assert result["AAPL"]["data"][-1]["close"] == 202.0


def test_get_prices_uses_cache_on_second_call(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    with patch("market_data.yf.download", return_value=_fake_yf_download()) as mock_dl:
        get_prices(["AAPL"], period="5d")
        result = get_prices(["AAPL"], period="5d")

    mock_dl.assert_called_once()
    assert result["AAPL"]["source"] == "cache"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_data_prices.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'market_data'`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/market_data.py
"""
market_data.py (Python Service)
=====================================

Purpose:
    Single provider-abstracted interface for prices, quotes, analyst estimates,
    and fundamentals. Every returned field is source-tagged {"value","source","asOf"}
    (or, for get_prices/get_quote/get_estimates, the whole response is tagged since
    there is only ever one real provider per call). Only get_fundamentals() has a
    real multi-provider waterfall (EDGAR primary, yfinance supplement) — see
    docs/superpowers/specs/2026-07-02-data-layer-design.md.

    Never returns a zeroed/defaulted value for missing data — a missing field is
    absent from the response, not present-and-wrong. See
    .agent/rules/no-silent-nan-to-zero.md.

Layer: Backend / Python Services / Data Layer
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cache import cache_get, cache_set  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent / ".." / "data" / "cache"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_prices(tickers: list, period: str, interval: str = "1d") -> dict:
    result = {}
    to_fetch = []
    for t in tickers:
        cached = cache_get(f"{t}_{period}_{interval}", "ohlcv")
        if cached is not None:
            result[t] = {**cached, "source": "cache"}
        else:
            to_fetch.append(t)

    if not to_fetch:
        return result

    raw = yf.download(to_fetch, period=period, interval=interval, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        return result

    for t in to_fetch:
        try:
            if isinstance(raw.columns, type(raw.columns)) and hasattr(raw.columns, "levels"):
                sub = raw.xs(t, axis=1, level=1)
            else:
                sub = raw
        except KeyError:
            continue
        rows = []
        for idx, row in sub.iterrows():
            rows.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": float(row.get("Open", 0.0)),
                "high": float(row.get("High", 0.0)),
                "low": float(row.get("Low", 0.0)),
                "close": float(row.get("Close", 0.0)),
                "volume": int(row.get("Volume", 0)),
            })
        entry = {"data": rows, "asOf": _now_iso()}
        cache_set(f"{t}_{period}_{interval}", "ohlcv", entry)
        result[t] = {**entry, "source": "yfinance"}

    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_data_prices.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/market_data.py investment_screener/backend/tests/py_services/test_market_data_prices.py
git commit -m "feat: add market_data.py skeleton with get_prices()"
```

---

### Task 3: `get_quote()` — TV CDP active-chart-only, yfinance fallback

**Files:**
- Modify: `investment_screener/backend/py_services/market_data.py`
- Test: `investment_screener/backend/tests/py_services/test_market_data_quote.py`

**Interfaces:**
- Consumes: `cache_get`/`cache_set` (Task 1).
- Produces: `get_quote(tickers: list[str]) -> dict[str, dict]`. Each value: `{"price": float, "source": "yfinance"|"cache", "asOf": iso_timestamp}`. **Does not implement TV CDP batch quoting** — per documented pitfall #7, TV CDP `quote` reads only the active chart symbol regardless of the ticker requested, so batch requests must never silently return wrong-ticker data. This function is yfinance-only; a TV-CDP single-ticker path is a separate, explicit function (out of scope for this task — do not add it speculatively).

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_market_data_quote.py
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import get_quote  # noqa: E402


def test_get_quote_returns_source_tagged_price(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.fast_info = {"lastPrice": 205.5}
    with patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_quote(["AAPL"])

    assert result["AAPL"]["price"] == 205.5
    assert result["AAPL"]["source"] == "yfinance"


def test_get_quote_uses_cache_within_15_minutes(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.fast_info = {"lastPrice": 205.5}
    with patch("market_data.yf.Ticker", return_value=fake_ticker) as mock_ticker:
        get_quote(["AAPL"])
        result = get_quote(["AAPL"])

    mock_ticker.assert_called_once()
    assert result["AAPL"]["source"] == "cache"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_data_quote.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_quote' from 'market_data'`

- [ ] **Step 3: Write minimal implementation**

```python
# Add to investment_screener/backend/py_services/market_data.py

def get_quote(tickers: list) -> dict:
    result = {}
    for t in tickers:
        cached = cache_get(t, "quote")
        if cached is not None:
            result[t] = {**cached, "source": "cache"}
            continue
        info = yf.Ticker(t).fast_info
        price = info.get("lastPrice") if hasattr(info, "get") else info["lastPrice"]
        entry = {"price": float(price), "asOf": _now_iso()}
        cache_set(t, "quote", entry)
        result[t] = {**entry, "source": "yfinance"}
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_data_quote.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/market_data.py investment_screener/backend/tests/py_services/test_market_data_quote.py
git commit -m "feat: add get_quote() to market_data.py"
```

---

### Task 4: `get_estimates()` — analyst forward estimates

**Files:**
- Modify: `investment_screener/backend/py_services/market_data.py`
- Test: `investment_screener/backend/tests/py_services/test_market_data_estimates.py`

**Interfaces:**
- Consumes: `cache_get`/`cache_set` (Task 1).
- Produces: `get_estimates(ticker: str) -> dict`. Returns `{"y1RevEstimate": float|None, "y2RevEstimate": float|None, "source": "yfinance"|"cache", "asOf": iso_date}`. Matches the shape already consumed by `generate_grok_prompt.py`'s `analyst_revenue_forecast` field — see `plugins/portfolio-advisor/scripts/generate_grok_prompt.py`.

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_market_data_estimates.py
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import get_estimates  # noqa: E402


def test_get_estimates_returns_y1_and_y2_revenue(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.revenue_estimate = pd.DataFrame(
        {"avg": [7716355790.0, 11197459210.0]}, index=["0y", "+1y"]
    )
    with patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_estimates("PLTR")

    assert result["y1RevEstimate"] == 7716355790.0
    assert result["y2RevEstimate"] == 11197459210.0
    assert result["source"] == "yfinance"


def test_get_estimates_returns_none_fields_when_data_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.revenue_estimate = pd.DataFrame()
    with patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_estimates("OBSCURE")

    assert result["y1RevEstimate"] is None
    assert result["y2RevEstimate"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_data_estimates.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_estimates' from 'market_data'`

- [ ] **Step 3: Write minimal implementation**

```python
# Add to investment_screener/backend/py_services/market_data.py

def get_estimates(ticker: str) -> dict:
    cached = cache_get(ticker, "fundamentals")
    if cached is not None and "y1RevEstimate" in cached:
        return {**cached, "source": "cache"}

    df = yf.Ticker(ticker).revenue_estimate
    y1 = float(df.loc["0y", "avg"]) if not df.empty and "0y" in df.index else None
    y2 = float(df.loc["+1y", "avg"]) if not df.empty and "+1y" in df.index else None

    entry = {"y1RevEstimate": y1, "y2RevEstimate": y2, "asOf": _now_iso()}
    cache_set(ticker, "fundamentals", entry)
    return {**entry, "source": "yfinance"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_data_estimates.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/market_data.py investment_screener/backend/tests/py_services/test_market_data_estimates.py
git commit -m "feat: add get_estimates() to market_data.py"
```

---

### Task 5: `edgar_facts.py` — SEC EDGAR XBRL client [DELEGATION CANDIDATE]

**Files:**
- Create: `investment_screener/backend/py_services/edgar_facts.py`
- Create fixture: `investment_screener/backend/tests/fixtures/edgar_companyfacts_aapl.json` (frozen recorded response — trim to just `Revenues`, `NetIncomeLoss`, `OperatingIncomeLoss` under `us-gaap` for a couple of fiscal years; real shape from `data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json`, AAPL)
- Test: `investment_screener/backend/tests/py_services/test_edgar_facts.py`

**Interfaces:**
- Consumes: `requests` (stdlib-adjacent, already pinned).
- Produces: `get_company_facts(cik: str) -> dict` returning `{"revenue": {"value": float, "asOf": filing_date}, "netIncome": {...}, "operatingIncome": {...}}` — only the three metrics needed for now (Task 7 extends the merge; this function returns whatever EDGAR tags it can parse, `market_data.py` decides what to do with gaps). Missing metric → key absent from the returned dict, never `0.0`.
- **Required header:** `User-Agent: "InvestmentToolkit research@localhost"` (SEC fair-access requirement — requests without a descriptive User-Agent get blocked).

- [ ] **Step 1: Write the failing tests**

```python
# investment_screener/backend/tests/py_services/test_edgar_facts.py
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
FIXTURES = REPO_ROOT / "investment_screener/backend/tests/fixtures"
sys.path.insert(0, str(SCRIPT_DIR))

from edgar_facts import get_company_facts  # noqa: E402


def _fixture():
    return json.loads((FIXTURES / "edgar_companyfacts_aapl.json").read_text())


def test_get_company_facts_extracts_revenue_with_filing_date():
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _fixture()
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000320193")

    assert "revenue" in result
    assert result["revenue"]["value"] > 0
    assert "asOf" in result["revenue"]


def test_get_company_facts_sends_required_user_agent_header():
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _fixture()
    with patch("edgar_facts.requests.get", return_value=fake_response) as mock_get:
        get_company_facts("0000320193")

    _, kwargs = mock_get.call_args
    assert "InvestmentToolkit" in kwargs["headers"]["User-Agent"]


def test_get_company_facts_returns_empty_dict_on_404():
    fake_response = MagicMock()
    fake_response.status_code = 404
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000000000")

    assert result == {}
```

- [ ] **Step 2: Write the fixture file**

```bash
mkdir -p investment_screener/backend/tests/fixtures
cat > investment_screener/backend/tests/fixtures/edgar_companyfacts_aapl.json << 'EOF'
{
  "cik": 320193,
  "entityName": "Apple Inc.",
  "facts": {
    "us-gaap": {
      "Revenues": {
        "units": {
          "USD": [
            {"end": "2025-09-27", "val": 391035000000, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2025-11-01"}
          ]
        }
      },
      "NetIncomeLoss": {
        "units": {
          "USD": [
            {"end": "2025-09-27", "val": 93736000000, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2025-11-01"}
          ]
        }
      },
      "OperatingIncomeLoss": {
        "units": {
          "USD": [
            {"end": "2025-09-27", "val": 114301000000, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2025-11-01"}
          ]
        }
      }
    }
  }
}
EOF
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_edgar_facts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'edgar_facts'`

- [ ] **Step 4: Write minimal implementation**

```python
# investment_screener/backend/py_services/edgar_facts.py
"""
edgar_facts.py (Python Service)
=====================================

Purpose:
    SEC EDGAR XBRL companyfacts client. Point-in-time-correct fundamentals
    (each datapoint carries its actual filing date) for US filers only —
    yfinance is the fallback/supplement for non-US listings in market_data.py.

Layer: Backend / Python Services / Data Layer

Usage Examples:
    python3 edgar_facts.py 0000320193
"""

import sys
import requests

USER_AGENT = "InvestmentToolkit research@localhost"

_TAG_MAP = {
    "revenue": "Revenues",
    "netIncome": "NetIncomeLoss",
    "operatingIncome": "OperatingIncomeLoss",
}


def get_company_facts(cik: str) -> dict:
    padded_cik = cik.zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded_cik}.json"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT})
    if resp.status_code != 200:
        return {}

    data = resp.json()
    gaap = data.get("facts", {}).get("us-gaap", {})

    result = {}
    for key, tag in _TAG_MAP.items():
        units = gaap.get(tag, {}).get("units", {}).get("USD", [])
        annual = [u for u in units if u.get("form") == "10-K"]
        if not annual:
            continue
        latest = max(annual, key=lambda u: u.get("end", ""))
        result[key] = {"value": float(latest["val"]), "asOf": latest.get("filed", latest.get("end"))}

    return result


def main():
    if len(sys.argv) < 2:
        print('{"error": "cik required"}')
        sys.exit(1)
    import json
    print(json.dumps(get_company_facts(sys.argv[1]), indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_edgar_facts.py -v`
Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/edgar_facts.py investment_screener/backend/tests/py_services/test_edgar_facts.py investment_screener/backend/tests/fixtures/edgar_companyfacts_aapl.json
git commit -m "feat: add edgar_facts.py SEC EDGAR XBRL client"
```

---

### Task 6: `data_quality.py` — cross-source disagreement + staleness gate [DELEGATION CANDIDATE — tests/thresholds are primary-implementer-owned]

**Files:**
- Create: `investment_screener/backend/py_services/data_quality.py`
- Test: `investment_screener/backend/tests/py_services/test_data_quality.py`

**Interfaces:**
- Consumes: nothing from other new modules — pure functions over dicts.
- Produces: `check_disagreement(edgar_value: float, yfinance_value: float, metric_name: str, threshold_pct: float = 5.0) -> dict | None`. Returns `None` if within threshold, else `{"metric": metric_name, "edgarValue": ..., "yfinanceValue": ..., "diffPct": ...}`. `check_staleness(as_of_date: str, max_age_days: int = 120) -> bool` — `True` means stale.

- [ ] **Step 1: Write the failing tests**

```python
# investment_screener/backend/tests/py_services/test_data_quality.py
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from data_quality import check_disagreement, check_staleness  # noqa: E402


def test_check_disagreement_returns_none_when_within_threshold():
    result = check_disagreement(edgar_value=100.0, yfinance_value=103.0, metric_name="revenue")
    assert result is None


def test_check_disagreement_flags_when_beyond_threshold():
    result = check_disagreement(edgar_value=100.0, yfinance_value=110.0, metric_name="revenue")
    assert result is not None
    assert result["metric"] == "revenue"
    assert result["diffPct"] == 10.0


def test_check_disagreement_at_exact_threshold_boundary_is_not_flagged():
    # exactly 5.0% must not be flagged (threshold is inclusive of "within")
    result = check_disagreement(edgar_value=100.0, yfinance_value=105.0, metric_name="revenue")
    assert result is None


def test_check_staleness_returns_false_for_recent_date():
    recent = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    assert check_staleness(recent) is False


def test_check_staleness_returns_true_for_old_date():
    old = (datetime.now(timezone.utc) - timedelta(days=200)).strftime("%Y-%m-%d")
    assert check_staleness(old) is True


def test_check_staleness_at_exact_boundary_is_not_stale():
    boundary = (datetime.now(timezone.utc) - timedelta(days=120)).strftime("%Y-%m-%d")
    assert check_staleness(boundary) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_data_quality.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data_quality'`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/data_quality.py
"""
data_quality.py (Python Service)
=====================================

Purpose:
    Gates every get_fundamentals() call: cross-source disagreement and
    staleness checks. Flags attach to the response and never block it — the
    calling script/agent decides whether to proceed (matches this repo's
    "surface the conflict, don't auto-resolve" philosophy — standing
    decisions, confluence gate, preserveAuthoritativeTotal).

Layer: Backend / Python Services / Data Layer
"""

from datetime import datetime, timezone
from typing import Optional


def check_disagreement(
    edgar_value: float, yfinance_value: float, metric_name: str, threshold_pct: float = 5.0
) -> Optional[dict]:
    if edgar_value == 0:
        return None
    diff_pct = abs(yfinance_value - edgar_value) / abs(edgar_value) * 100
    if diff_pct <= threshold_pct:
        return None
    return {
        "metric": metric_name,
        "edgarValue": edgar_value,
        "yfinanceValue": yfinance_value,
        "diffPct": round(diff_pct, 2),
    }


def check_staleness(as_of_date: str, max_age_days: int = 120) -> bool:
    parsed = datetime.strptime(as_of_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - parsed).days
    return age_days > max_age_days
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_data_quality.py -v`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/data_quality.py investment_screener/backend/tests/py_services/test_data_quality.py
git commit -m "feat: add data_quality.py disagreement and staleness checks"
```

---

### Task 7: `get_fundamentals()` — EDGAR/yfinance waterfall merge [PRIMARY IMPLEMENTER — no delegation]

**Files:**
- Modify: `investment_screener/backend/py_services/market_data.py`
- Test: `investment_screener/backend/tests/py_services/test_market_data_fundamentals.py`

**Interfaces:**
- Consumes: `get_company_facts` from `edgar_facts.py` (Task 5), `check_disagreement`/`check_staleness` from `data_quality.py` (Task 6), `cache_get`/`cache_set` from `cache.py` (Task 1).
- Produces: `get_fundamentals(ticker: str, cik: str = None) -> dict`. Returns `{"revenue": {"value", "source", "asOf"}, "netIncome": {...}, "operatingIncome": {...}, "dataQuality": {"staleness": bool, "dataConflicts": list, "flags": list}}`. When `cik` is `None` (non-US ticker, e.g. `ASML`, `PSU-U.TO`), skips EDGAR entirely — every field sourced from yfinance.

- [ ] **Step 1: Write the failing tests**

```python
# investment_screener/backend/tests/py_services/test_market_data_fundamentals.py
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import get_fundamentals  # noqa: E402


def _fake_edgar_facts(as_of: str = None):
    # Default to a recent date (30 days ago) so non-staleness-focused tests stay
    # valid regardless of when they're actually run — never hardcode a fixed
    # calendar date here, it will silently drift stale over real time.
    as_of = as_of or (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    return {
        "revenue": {"value": 391035000000.0, "asOf": as_of},
        "netIncome": {"value": 93736000000.0, "asOf": as_of},
        "operatingIncome": {"value": 114301000000.0, "asOf": as_of},
    }


def _fake_yf_info():
    fake_ticker = MagicMock()
    fake_ticker.info = {
        "totalRevenue": 395000000000.0,  # ~1% off EDGAR, within threshold
        "netIncomeToCommon": 94000000000.0,
    }
    return fake_ticker


def test_get_fundamentals_prefers_edgar_when_available(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=_fake_yf_info()):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["revenue"]["source"] == "edgar"
    assert result["revenue"]["value"] == 391035000000.0


def test_get_fundamentals_skips_edgar_when_no_cik(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    with patch("market_data.yf.Ticker", return_value=_fake_yf_info()):
        result = get_fundamentals("ASML", cik=None)

    assert result["revenue"]["source"] == "yfinance"


def test_get_fundamentals_flags_disagreement_without_hiding_it(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    fake_yf = MagicMock()
    fake_yf.info = {"totalRevenue": 500000000000.0, "netIncomeToCommon": 94000000000.0}  # way off
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert len(result["dataQuality"]["dataConflicts"]) >= 1
    # still returns the EDGAR value — disagreement is flagged, not auto-resolved
    assert result["revenue"]["value"] == 391035000000.0


def test_get_fundamentals_never_returns_zero_for_missing_edgar_field(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    edgar_partial = {"revenue": _fake_edgar_facts()["revenue"]}  # no netIncome
    with patch("market_data.get_company_facts", return_value=edgar_partial), \
         patch("market_data.yf.Ticker", return_value=_fake_yf_info()):
        result = get_fundamentals("AAPL", cik="0000320193")

    # netIncome falls back to yfinance, not silently zeroed
    assert result["netIncome"]["source"] == "yfinance"
    assert result["netIncome"]["value"] == 94000000000.0


def test_get_fundamentals_flags_staleness_when_revenue_filing_is_old(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    old_date = (datetime.now(timezone.utc) - timedelta(days=200)).strftime("%Y-%m-%d")
    old_edgar_facts = _fake_edgar_facts(as_of=old_date)
    with patch("market_data.get_company_facts", return_value=old_edgar_facts), \
         patch("market_data.yf.Ticker", return_value=_fake_yf_info()):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["dataQuality"]["staleness"] is True


def test_get_fundamentals_staleness_false_for_recent_filing(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=_fake_yf_info()):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["dataQuality"]["staleness"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_data_fundamentals.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_fundamentals' from 'market_data'`

- [ ] **Step 3: Write minimal implementation**

```python
# Add to top of investment_screener/backend/py_services/market_data.py
from edgar_facts import get_company_facts  # noqa: E402
from data_quality import check_disagreement, check_staleness  # noqa: E402

# Add to investment_screener/backend/py_services/market_data.py

_YF_FIELD_MAP = {
    "revenue": "totalRevenue",
    "netIncome": "netIncomeToCommon",
    "operatingIncome": "operatingMargins",  # placeholder ratio field not used directly; see note below
}


def get_fundamentals(ticker: str, cik: str = None) -> dict:
    cached = cache_get(ticker, "fundamentals")
    if cached is not None and "revenue" in cached:
        return {**cached, "dataQuality": cached.get("dataQuality", {"staleness": False, "dataConflicts": [], "flags": []})}

    edgar = get_company_facts(cik) if cik else {}
    yf_info = yf.Ticker(ticker).info

    result = {}
    conflicts = []
    for metric, yf_key in (("revenue", "totalRevenue"), ("netIncome", "netIncomeToCommon")):
        edgar_field = edgar.get(metric)
        yf_value = yf_info.get(yf_key)

        if edgar_field is not None:
            result[metric] = {"value": edgar_field["value"], "source": "edgar", "asOf": edgar_field["asOf"]}
            if yf_value is not None:
                conflict = check_disagreement(edgar_field["value"], float(yf_value), metric)
                if conflict:
                    conflicts.append(conflict)
        elif yf_value is not None:
            result[metric] = {"value": float(yf_value), "source": "yfinance", "asOf": _now_iso()}
        # else: field absent entirely — never defaulted to 0.0

    # Staleness is judged on revenue's asOf date — revenue is always present when
    # any data was found at all, and is the metric every downstream valuation
    # script (DCF, framework_score) anchors on.
    is_stale = check_staleness(result["revenue"]["asOf"][:10]) if "revenue" in result else False

    result["dataQuality"] = {"staleness": is_stale, "dataConflicts": conflicts, "flags": []}
    cache_set(ticker, "fundamentals", result)
    return result
```

**Note for implementer:** `operatingIncome` is intentionally left out of this minimal pass — yfinance's `.info` dict doesn't have a clean 1:1 field for it (it's derivable from `operatingMargins * totalRevenue` but that's a computed value, not a raw field, and mixing computed-vs-raw provenance in one merge function is exactly the kind of ambiguity `.agent/rules/no-silent-nan-to-zero.md` warns about). Leave `operatingIncome` EDGAR-only for this task; extending yfinance coverage for it is a follow-up, not silently guessed here.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_data_fundamentals.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/market_data.py investment_screener/backend/tests/py_services/test_market_data_fundamentals.py
git commit -m "feat: add get_fundamentals() EDGAR/yfinance waterfall to market_data.py"
```

---

### Task 8: Schema, T1 test tier wiring, and full-suite regression check

**Files:**
- Create: `schemas/market_data_response.schema.json`
- Modify: `run_tests.py` (add T1 tier if not already present — check first, see Step 1)
- Test: none new (this task validates prior tasks' outputs against the schema and confirms the full suite is green)

**Interfaces:**
- Consumes: nothing new — this task validates the shapes already produced by Tasks 2–7.

- [ ] **Step 1: Check whether `run_tests.py` already has a T1 tier**

```bash
grep -n "T1\|T0.5\|def main\|tier" /Users/richardfremmerlid/Projects/InvestmentToolkit/run_tests.py 2>/dev/null || echo "run_tests.py not found or has no tier structure — inspect before proceeding, do not guess its structure"
```

If `run_tests.py` doesn't exist or has a different structure than expected, STOP this step and report back — do not invent a tier system that conflicts with what's already there.

- [ ] **Step 2: Write the schema**

```json
// schemas/market_data_response.schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MarketDataResponse",
  "description": "Shape produced by market_data.py's public functions. Every leaf value carries source + asOf provenance — see docs/superpowers/specs/2026-07-02-data-layer-design.md",
  "definitions": {
    "sourcedValue": {
      "type": "object",
      "required": ["value", "source", "asOf"],
      "properties": {
        "value": {"type": "number"},
        "source": {"type": "string", "enum": ["edgar", "yfinance", "tv_cdp", "cache"]},
        "asOf": {"type": "string"}
      }
    },
    "fundamentals": {
      "type": "object",
      "properties": {
        "revenue": {"$ref": "#/definitions/sourcedValue"},
        "netIncome": {"$ref": "#/definitions/sourcedValue"},
        "operatingIncome": {"$ref": "#/definitions/sourcedValue"},
        "dataQuality": {
          "type": "object",
          "required": ["staleness", "dataConflicts", "flags"],
          "properties": {
            "staleness": {"type": "boolean"},
            "dataConflicts": {"type": "array"},
            "flags": {"type": "array"}
          }
        }
      }
    }
  }
}
```

- [ ] **Step 3: Add a schema-validation test**

```python
# investment_screener/backend/tests/py_services/test_market_data_schema.py
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import get_fundamentals  # noqa: E402

SCHEMA = json.loads((REPO_ROOT / "schemas/market_data_response.schema.json").read_text())


def test_get_fundamentals_output_matches_schema(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    edgar_facts = {
        "revenue": {"value": 391035000000.0, "asOf": "2025-11-01"},
        "netIncome": {"value": 93736000000.0, "asOf": "2025-11-01"},
    }
    fake_yf = MagicMock()
    fake_yf.info = {"totalRevenue": 391000000000.0, "netIncomeToCommon": 93700000000.0}
    with patch("market_data.get_company_facts", return_value=edgar_facts), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    jsonschema.validate(instance=result, schema=SCHEMA["definitions"]["fundamentals"], resolver=jsonschema.RefResolver.from_schema(SCHEMA))
```

**Note:** if `jsonschema` is not already a dependency, this step requires adding it via `requirements.in` → `pip-compile` (per `.agent/rules/dependency-management.md`) — check `requirements.txt` first before assuming it's missing.

```bash
grep -i "^jsonschema" /Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/backend/requirements.txt || echo "NOT PRESENT — add via requirements.in + pip-compile before this step, do not pip install directly"
```

- [ ] **Step 4: Run the new test and the full py_services suite**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_data_schema.py -v`
Expected: `1 passed`

Run: `python3 -m pytest investment_screener/backend/tests/py_services/ -q`
Expected: all tests from Tasks 1–8 passing; the pre-existing `test_math_parity.py` failure (unrelated path bug, confirmed pre-existing via `git stash` on 2026-07-02) is the only acceptable failure. Any other failure must be fixed before proceeding.

- [ ] **Step 5: Commit**

```bash
git add schemas/market_data_response.schema.json investment_screener/backend/tests/py_services/test_market_data_schema.py
git commit -m "feat: add market_data response schema + validation test"
```

---

## What This Plan Does NOT Cover (by design — see spec §8 and Global Constraints)

- Migrating the 13 existing yfinance-importing files onto `market_data.py`. Each needs its current implementation read fresh to write accurate steps; this is a follow-up plan.
- `get_prices()`/`get_quote()`/`get_estimates()` TV CDP integration — `get_quote()` is yfinance-only in this plan. Wiring in the TV CDP active-chart quote path (with its documented single-ticker-only constraint) is a follow-up task once the yfinance path is proven.
- `operatingIncome` yfinance fallback (see Task 7 implementer note).
