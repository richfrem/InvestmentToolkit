# API Reference — stock-valuation Backend

> Reference documentation for the Investment Screener backend API and scripts used by the `stock_valuation` skill. These scripts are **owned by the web app** — do not move or duplicate them.

---

## fetch_financials.py

**Path**: `investment_screener/backend/py_services/fetch_financials.py`  
**Interface**: CLI — takes ticker as positional arg, writes JSON to stdout

```bash
python3 investment_screener/backend/py_services/fetch_financials.py {TICKER} > /tmp/{TICKER}_raw.json
```

### Output Schema

```json
{
  "metrics": {
    "price": 185.0,
    "currency": "USD",
    "shares_outstanding": 15400,
    "revenue": 391035,
    "marketCap": 2850000,
    "trailingPE": 28.5,
    "grossMargin": 0.462,
    "netMargin": 0.262
  },
  "financials": {
    "history": [
      { "year": 2021, "revenue": 365817, "netIncome": 94680, "fcf": 92953 }
    ]
  },
  "estimates": {
    "revenue_growth": 8.5,
    "profit_margin": 26.0,
    "numberOfAnalysts": 38
  },
  "profile": {
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "description": "..."
  }
}
```

### Error Handling
| Exit Code | Meaning | Agent Action |
|-----------|---------|--------------|
| 0 | Success | Parse stdout as JSON |
| 1 | Ticker not found / network error | Invoke FB-01 from `references/fallback-tree.md` |
| 2 | yfinance dependency missing | Ask user to `pip install yfinance` and retry |

---

## persist_projection.py

**Path**: `investment_screener/backend/py_services/persist_projection.py`  
**Interface**: CLI — reads Projection JSON from stdin

```bash
cat /tmp/{TICKER}_projection.json | python3 investment_screener/backend/py_services/persist_projection.py
```

### Options
| Flag | Description |
|------|-------------|
| *(none)* | Default: saves; 409 if ticker+model already exists |
| `--replace` | Overwrites existing projection for same ticker+model |

### HTTP-Style Response Codes (exit codes)

| Exit Code | Meaning | Agent Action |
|-----------|---------|--------------|
| 0 | Saved successfully | Confirm path to user |
| 1 | 400 Validation error | Fix payload (check weights, types); retry once |
| 2 | 409 Conflict | Increment `version` field; retry once |
| 3 | 500 Filesystem error | Invoke FB-03 from `references/fallback-tree.md` |

---

## validate_projection.py (Plugin-owned)

**Path**: `plugins/stock-valuation/skills/stock_valuation/scripts/validate_projection.py`  
**Purpose**: Pre-flight validation before calling persist_projection.py

```bash
cat /tmp/{TICKER}_projection.json | python3 plugins/stock-valuation/skills/stock_valuation/scripts/validate_projection.py --verbose
echo $?  # 0 = valid, 1 = errors found
```

Use this **before** persistence to catch schema violations early (weight sums, type errors, ordering violations).

---

## Backend Health Check

```bash
curl -sf http://localhost:3001/health
```

| Result | Meaning |
|--------|---------|
| HTTP 200 + body | Backend running — proceed normally |
| Connection refused / timeout | Invoke FB-02 from `references/fallback-tree.md` (standalone mode) |
