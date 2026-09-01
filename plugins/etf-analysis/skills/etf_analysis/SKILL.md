---
name: etf_analysis
plugin: etf-analysis
description: >
  Perform autonomous ETF and fund analysis. Handles three fund types:
  CLOSED_END (NAV premium analysis, private holdings), THEMATIC_ETF (holdings
  composition, thesis alignment score), and CASH_FUND (yield, dividend timing).
  Saves structured JSON to backend/data/etf_analysis/{TICKER}.json and updates
  agentRationale in target-portfolio.json. Trigger on /analyze-etf or
  natural language: "analyze [TICKER]", "evaluate [TICKER] ETF".
allowed-tools: Bash, Read, Write
---

# ETF Analysis Skill

## Quick Reference
- **Trigger**: `/analyze-etf {TICKER}`
- **Output (JSON)**: `investment_screener/backend/data/etf_analysis/{TICKER}.json`
- **Scripts**: `plugins/etf-analysis/skills/etf_analysis/scripts/`
  - `fetch_fund_data.py {TICKER}` — yfinance metadata + holdings
  - `validate_etf_analysis.py` — pre-persistence schema check
  - `persist_etf_analysis.py` — write to etf_analysis/ with versioning
- `assets/templates/`:
  - `etf_analysis_template.json` — The official schema template for your output

## Fund Type Detection

| fundType | Characteristics | Key Analysis |
|----------|----------------|-------------|
| `CLOSED_END` | quoteType=EQUITY, no NAV on yfinance | NAV premium %, private holdings valuation |
| `THEMATIC_ETF` | quoteType=ETF, sector/theme focus | Holdings alignment, expense drag, concentration |
| `CASH_FUND` | quoteType=ETF, currency/treasury focus | Yield, dividend cycle timing, currency exposure |

---

## Step 1 — Fetch Market Data

```bash
python3 plugins/etf-analysis/skills/etf_analysis/scripts/fetch_fund_data.py {TICKER} > temp/evaluations/{TICKER}_raw.json
cat temp/evaluations/{TICKER}_raw.json
```

Use `snapshot.quoteType` and fund name to classify fund type.

---

## Step 2 — Analyze by Fund Type

### CLOSED_END (e.g., DXYZ)

DCF does not apply. Key outputs:

**NAV Analysis:**
- Estimate `navPerShare` from known private company valuations × fund's stake %
- `premiumPct = (marketPrice / navPerShare - 1) × 100`
- `historicalPremiumRange`: use 52-week price range vs estimated NAV range
- `premiumRisk`: HIGH if premium > 150%, MODERATE if 50-150%, LOW if < 50%
- `premiumPercentile`: where current premium sits in historical range (0=at low, 100=at high)

**Holdings Analysis:**
- List top private holdings with % of NAV and last known private valuation
- Flag IPO catalyst timeline for each major holding (IPO = premium compression event)
- Thesis alignment: does the holdings basket match portfolio thesis?

**Action Logic:**
- `BUY`: premium < 100% AND thesis alignment HIGH AND no imminent IPO compression
- `HOLD`: premium 100–200% with strong thesis alignment
- `TRIM`: premium > 300% OR major holding IPO imminent (premium compression risk)
- `AVOID`: premium > 400% with no near-term catalyst

### THEMATIC_ETF (e.g., KOID, HUMN)

**Holdings Analysis:**
- List top 10 holdings with weight %
- For each: does it align DIRECTLY, PARTIALLY, or TANGENTIALLY with portfolio thesis?
- `thesisAlignmentScore` (0-100): % of AUM in DIRECT + 0.5×PARTIAL thesis-aligned holdings
- `concentration`: top5Pct, top10Pct — high concentration = more targeted, less diversified drag
- Expense ratio drag: annualized cost at target weight

**Overlap Check:**
- Flag holdings that duplicate existing individual stock positions (e.g., HUMN holds NVDA which is already a direct holding)

**Action Logic:**
- `ACCUMULATE`: alignment > 70% + no excessive concentration risk + low overlap with existing holdings
- `HOLD`: alignment 50-70%
- `TRIM`: alignment < 50% or significant overlap with individual positions
- `AVOID`: alignment < 30% or pure diversification play inconsistent with concentrated thesis

### CASH_FUND (e.g., PSU-U.TO)

- Yield: annualized distribution / price
- Dividend timing rule: buy 1-2 days after ex-dividend date
- Currency exposure: USD/CAD or other
- `action`: always `HOLD` for thesis reserve funds (not a conviction play)

---

## Step 3 — Build the JSON

Construct the analysis object using the official template provided in:
`assets/templates/etf_analysis_template.json`

Read this template, fill in the fields based on your analysis, and use the exact schema structure.

**Important Note on Fields**:
- For CLOSED_END funds, `holdingsAnalysis` is optional.
- For THEMATIC_ETF funds, `navAnalysis` is optional.

## Step 4 — Validate and Persist

```bash
# Validate
cat temp/evaluations/{TICKER}_etf.json | python3 plugins/etf-analysis/skills/etf_analysis/scripts/validate_etf_analysis.py --verbose

# Persist (only if validation passes)
python3 plugins/etf-analysis/skills/etf_analysis/scripts/persist_etf_analysis.py --input temp/evaluations/{TICKER}_etf.json
```

---

## Step 5 — Verify Domain Model State & Research Timeline

1. **Automatic SQLite Persistence**: `persist_etf_analysis.py` automatically synchronizes:
   - `data/etf_analysis/{TICKER}.json` (versioned history)
   - `domain_model.sqlite` (`projection_version` table for Dashboard AI Thesis UI)
   - `domain_model.sqlite` (`investment` table: `target_action`, `agent_rationale`, and `last_deep_analysis_at`)

2. **Verify Holdings State**:
   ```bash
   python3 investment_screener/backend/py_services/portfolio_io.py --ticker {TICKER} --json
   ```

3. **Research Timeline**:
   Prepend a dated ETF analysis memo to `investment_screener/backend/data/research/{TICKER}.timeline.md` (creating the file if it does not exist) to ensure all qualitative research and thematic changes are tracked consistently with individual equities.

---

## Hard Rules

1. **Never use DCF** for fund analysis — there is no revenue or earnings to model
2. **Always state NAV premium** for closed-end funds before any action recommendation
3. **Always check expense ratio drag** for thematic ETFs at the target weight
4. **Flag overlap** with existing individual stock positions
5. **DXYZ NAV estimate** must cite the source/method (private_stake_sum, last_known_filing, etc.)
6. **Single Source of Truth**: All target actions and rationales are stored in `domain_model.sqlite` — never write to retired JSON files (e.g. `target-portfolio.json`).

