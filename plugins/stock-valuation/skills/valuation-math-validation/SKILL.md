---
name: valuation_math_validation
description: >
  Detect and prevent computational bugs in the DCF / scenario valuation engine that produce nonsensical target prices. Enforce deterministic math validation on every valuation run — catching unit mismatches, percent/decimal errors, double-discounting, share count explosions, and other silent failures that cause bear/base/bull scenarios to diverge by orders of magnitude.
has_tools: false
allowed-tools: Read, Write
---

# Valuation Math Validation Skill

## Purpose
Detect and prevent computational bugs in the DCF / scenario valuation engine that produce nonsensical target prices. This skill enforces deterministic math validation on every valuation run — catching unit mismatches, percent/decimal errors, double-discounting, share count explosions, and other silent failures that cause bear/base/bull scenarios to diverge by orders of magnitude.

## Problem Statement
The valuation engine frequently produces target prices that are mathematically inconsistent with the stated inputs. Common symptoms include:
- Bear case collapses to near-zero ($0.23) despite positive revenue growth and margins
- Base case implies 80%+ downside despite strong growth assumptions
- Bull case is 100x–200x the bear case (spread ratio is absurd)
- Fair value does not change proportionally when a single input is adjusted
- Scenarios with HIGHER growth produce LOWER target prices (monotonicity violation)

These are not "different opinions" — they are **computation bugs** that destroy the credibility of every analysis.

## When This Skill Activates
This skill MUST activate on **every single valuation run**, regardless of ticker, sector, or model type. It is not optional. It runs as a post-computation validation gate before any results are displayed or saved.

---

## Validation Rules

### Rule 1: Input Normalization — Percent vs Decimal
All percentage inputs MUST be normalized to decimal form before computation.

**Validation check:**
```
if revCAGR > 3.0:
    ERROR: "revCAGR appears to be in percent form (got {revCAGR}), expected decimal (e.g., 0.65 for 65%)"
if netMargin > 1.0 or netMargin < -1.0:
    ERROR: "netMargin appears to be in percent form (got {netMargin}), expected decimal (e.g., 0.10 for 10%)"
if discountRate > 1.0:
    ERROR: "discountRate appears to be in percent form (got {discountRate}), expected decimal (e.g., 0.10 for 10%)"
```

**Accepted ranges:**
| Input | Min | Max | Format |
|-------|-----|-----|--------|
| revCAGR | -0.50 | 3.00 | decimal (0.65 = 65%) |
| netMargin | -1.00 | 1.00 | decimal (0.10 = 10%) |
| grossMargin | -0.50 | 1.00 | decimal |
| discountRate | 0.01 | 0.50 | decimal (0.10 = 10%) |
| exitPE | 1 | 100 | absolute multiple |
| exitEVRevenue | 0.5 | 50 | absolute multiple |
| probabilityWeight | 0.01 | 0.99 | decimal (0.35 = 35%) |

If ANY input falls outside these ranges, HALT and report the violation before proceeding.

### Rule 2: Revenue Unit Consistency
Revenue values must use consistent units throughout the entire calculation chain.

**Validation check:**
```
if rev_t0 < 1_000_000 and company_market_cap > 1_000_000_000:
    WARNING: "rev_t0 may be in millions/billions shorthand — verify units"
if rev_t0 > 1_000_000_000_000:
    ERROR: "rev_t0 exceeds $1T — likely a units error"
```

**Required labeling:**
Every revenue variable MUST carry a unit label in the computation trace:
- `rev_t0_usd: 144_000_000` (raw dollars)
- `rev_t0_M: 144` (millions)
- `rev_t0_B: 0.144` (billions)

**Critical rule:** Never mix units within a single calculation chain. If rev_t0 is in raw USD, then rev_t5, earnings_t5, terminal_value, and equity_value must ALL be in raw USD.

### Rule 3: Monotonicity Checks (THE most important validation)
Holding all other inputs constant, these relationships MUST hold:

| If this increases... | Target price must... | Violation means... |
|----------------------|----------------------|-------------------|
| revCAGR ↑ | increase ↑ | sign error or compounding bug |
| netMargin ↑ | increase ↑ | margin applied incorrectly |
| exitPE ↑ | increase ↑ | multiple applied to wrong base |
| discountRate ↑ | decrease ↓ | discounting applied backwards |
| shares ↑ | decrease ↓ | dilution not dividing correctly |
| probability ↑ (for higher scenario) | fair value increase ↑ | weighting error |

**Implementation:**
After computing all three scenarios, run a quick sensitivity perturbation:
```
base_price = computeScenario(base_inputs)
test_price = computeScenario({...base_inputs, revCAGR: base_inputs.revCAGR + 0.05})

if test_price <= base_price:
    ERROR: "Monotonicity violation — increasing revCAGR by 5% did not increase target price"
    ERROR: "base_price={base_price}, test_price={test_price}"
```

Run this for ALL key inputs. If any monotonicity check fails, the valuation is INVALID.

### Rule 4: Scenario Ordering
Target prices MUST be ordered: bear < base < bull.

```
if not (bear_target < base_target < bull_target):
    ERROR: "Scenario ordering violation: bear={bear_target}, base={base_target}, bull={bull_target}"
```

Additionally, the inputs must be consistently ordered:
```
if not (bear_revCAGR <= base_revCAGR <= bull_revCAGR):
    WARNING: "Growth assumptions not ordered across scenarios"
if not (bear_margin <= base_margin <= bull_margin):
    WARNING: "Margin assumptions not ordered across scenarios"
if not (bear_exitPE <= base_exitPE <= bull_exitPE):
    WARNING: "Exit multiple assumptions not ordered across scenarios"
```

### Rule 5: Spread Ratio Bounds
```
spread_ratio = bull_target / bear_target
```

| Spread Ratio | Interpretation | Action |
|--------------|---------------|--------|
| 2x – 5x | Normal (established company) | Pass |
| 5x – 20x | Acceptable (speculative growth) | Pass with note |
| 20x – 50x | Suspicious | WARNING: review inputs |
| > 50x | Almost certainly a bug | ERROR: halt and review |
| > 100x | Definitely a bug | ERROR: do not display results |

**Your APLD example:** $44.48 / $0.23 = **193x spread** → this is a computation bug, not a valuation opinion.

### Rule 6: Probability-Weighted Fair Value Reconciliation
The displayed fair value MUST equal the probability-weighted sum of scenario targets:

```
computed_fv = (bear_prob * bear_target) + (base_prob * base_target) + (bull_prob * bull_target)

if abs(computed_fv - displayed_fv) > 0.01:
    ERROR: "Fair value mismatch — displayed={displayed_fv}, computed={computed_fv}"
```

Also verify probabilities sum to 1.0 (or 100%):
```
total_prob = bear_prob + base_prob + bull_prob
if abs(total_prob - 1.0) > 0.01:
    ERROR: "Probabilities do not sum to 100%: {total_prob}"
```

### Rule 7: Terminal Value Sanity
Terminal value is the largest component of most DCFs and the most common source of errors.

**Check 1: Terminal value formula consistency**
```
# If using P/E exit method:
terminal_value = earnings_t5 * exitPE

# Verify:
earnings_t5 = rev_t5 * netMargin
rev_t5 = rev_t0 * (1 + revCAGR) ^ horizon

# All three must be consistent
```

**Check 2: Terminal value as % of enterprise value**
```
tv_pct = pv_terminal / enterprise_value

if tv_pct > 0.95:
    WARNING: "Terminal value is {tv_pct*100}% of EV — near-term cash flows are negligible"
if tv_pct < 0.30:
    WARNING: "Terminal value is only {tv_pct*100}% of EV — unusual for 5-year DCF"
```

**Check 3: Implied terminal growth**
```
implied_terminal_growth = (terminal_value / pv_terminal) ^ (1/horizon) - 1

if implied_terminal_growth > 0.25:
    WARNING: "Implied terminal growth rate is {implied_terminal_growth*100}% — verify this is intentional"
```

### Rule 8: Share Count Validation
```
if shares_used <= 0:
    ERROR: "Share count is zero or negative"
if shares_used > shares_outstanding * 5:
    ERROR: "Share count is >5x current outstanding — extreme dilution assumption must be explicitly justified"
if shares_used != shares_outstanding and dilution_rate == 0:
    ERROR: "Share count differs from outstanding but no dilution rate specified"
```

**Required output:**
Always display:
- `shares_current`: current shares outstanding
- `shares_t5`: shares used in terminal calculation
- `annual_dilution_%`: assumed dilution rate
- `dilution_source`: "assumed" | "guided" | "modeled"

### Rule 9: Double-Discount Detection
A common bug is discounting cash flows AND THEN discounting the terminal value again, or applying the discount rate as both a DCF rate and a risk premium.

**Check:**
```
# Method 1: Direct computation verification
manual_pv = terminal_value / (1 + discountRate) ^ horizon
if abs(manual_pv - pv_terminal) / manual_pv > 0.01:
    ERROR: "PV of terminal value does not match single-discount calculation"
    ERROR: "Expected={manual_pv}, Got={pv_terminal}"
    ERROR: "Possible double-discounting detected"
```

**Check:**
```
# Method 2: Ratio test
if pv_terminal < terminal_value * 0.3 and horizon <= 5 and discountRate <= 0.15:
    ERROR: "PV terminal is <30% of terminal value with moderate discount rate — possible double-discount"
```

### Rule 10: Negative Value Handling
```
if earnings_t5 < 0 and exitPE > 0:
    WARNING: "Negative earnings with positive P/E — target price will be negative"
    ACTION: "Use revenue multiple (EV/Rev) instead of P/E for unprofitable scenarios"

if equity_value < 0:
    ACTION: "Set target price to $0.00 and label scenario as 'equity wipeout / restructuring'"
    ACTION: "Do NOT produce small positive values like $0.23 — that implies residual equity that doesn't exist"

if target_price < 0:
    ERROR: "Negative target price is not valid — clamp to $0.00"
```

---

## Required Computation Trace

Every valuation run MUST produce and log a full computation trace for EACH scenario. This trace must be available for debugging and should be displayable in the UI on demand.

### Trace Schema
```json
{
  "scenario": "base",
  "inputs": {
    "rev_t0": 144000000,
    "rev_unit": "USD",
    "revCAGR": 0.65,
    "netMargin": 0.10,
    "exitPE": 18,
    "discountRate": 0.10,
    "horizon": 5,
    "shares_current": 260000000,
    "annual_dilution": 0.02,
    "shares_t5": 286520000
  },
  "derived": {
    "rev_t1": 237600000,
    "rev_t2": 392040000,
    "rev_t3": 646866000,
    "rev_t4": 1067329000,
    "rev_t5": 1761093000,
    "earnings_t5": 176109300,
    "terminal_value": 3169967400,
    "pv_terminal": 1967948000,
    "pv_cashflows": 312500000,
    "enterprise_value": 2280448000,
    "net_debt": 150000000,
    "equity_value": 2130448000,
    "target_price": 7.44
  },
  "validation": {
    "input_ranges": "PASS",
    "unit_consistency": "PASS",
    "monotonicity": "PASS",
    "scenario_ordering": "PASS",
    "spread_ratio": 12.4,
    "spread_check": "PASS",
    "probability_sum": 1.00,
    "fv_reconciliation": "PASS",
    "tv_pct_of_ev": 0.86,
    "double_discount_check": "PASS",
    "share_count_check": "PASS"
  }
}
```

### Trace Display
The UI should include a "Show Valuation Trace" or "Show Advanced" toggle that displays this trace per scenario. This allows the user to:
- Verify every intermediate step
- Identify exactly where a divergence occurs
- Compare scenarios side-by-side at every computation step

---

## Error Handling Protocol

### Severity Levels
| Level | Meaning | Action |
|-------|---------|--------|
| ERROR | Math is provably wrong | HALT — do not display results |
| WARNING | Results are suspicious | Display with warning banner |
| INFO | Notable but not wrong | Log for review |

### On ERROR:
1. Do NOT display the valuation results
2. Display the specific error(s) with the computation trace
3. Suggest which input(s) likely caused the issue
4. Allow the user to correct inputs and re-run

### On WARNING:
1. Display results with a visible warning indicator
2. List the specific warnings in a collapsible section
3. Highlight the suspicious values in the scenario table

---

## Integration with Forward-Looking Valuation Challenge Skill

This skill (math validation) runs AFTER the forward-looking challenge skill has adjusted inputs. The pipeline is:

```
1. Raw model generates bear/base/bull inputs
2. Forward-Looking Challenge Skill adjusts inputs for demand signals
3. Valuation engine computes target prices
4. THIS SKILL validates the math
5. Results displayed only if validation passes
```

Both skills are complementary:
- **Forward-Looking Challenge**: ensures inputs reflect reality
- **Math Validation**: ensures computation is correct

Together they prevent both "garbage in" (backward-looking inputs) and "garbage out" (buggy math on good inputs).

---

## Quick Reference: Common Bugs and Their Signatures

| Symptom | Likely Bug | Fix |
|---------|-----------|-----|
| Bear target near $0 despite positive growth/margins | Percent vs decimal (margin=10 instead of 0.10) | Normalize inputs |
| Base target implies >80% downside with strong growth | Revenue units mismatch (millions vs dollars) | Standardize units |
| Bull is 100x+ bear target | Multiple bugs compounding | Run monotonicity checks |
| Increasing growth decreases price | Sign error in CAGR compounding | Check (1+g)^n formula |
| All scenarios produce same price | Inputs not varying across scenarios | Verify scenario differentiation |
| Fair value doesn't match weighted scenarios | Probability weights wrong or not summing to 1 | Check probability normalization |
| Terminal value is >99% of EV | Near-term cash flows computed as zero | Check interim CF formula |
| Target price is negative | Negative earnings × positive P/E | Switch to revenue multiple |
| Small positive target ($0.10–$1.00) | Equity wipeout not handled | Clamp to $0 and label |
| Price doesn't change when slider moves | Stale cache or wrong variable binding | Check UI reactivity |

---

## Test Suite (automated, run on every valuation)

### Test 1: Identity Test
```
Given: rev_t0=100M, CAGR=0%, margin=10%, PE=15x, discount=10%, horizon=5
Expected: target_price ≈ rev_t0 * margin * PE / (1.10^5) / shares
Tolerance: ±1%
```

### Test 2: Growth Scaling Test
```
Given: same as Test 1 but CAGR=50%
Expected: target_price > Test 1 result (monotonicity)
Expected: target_price ≈ Test 1 result * (1.50^5) (within ±5%)
```

### Test 3: Margin Scaling Test
```
Given: same as Test 1 but margin=20% (2x)
Expected: target_price ≈ Test 1 result * 2 (within ±1%)
```

### Test 4: Multiple Scaling Test
```
Given: same as Test 1 but PE=30x (2x)
Expected: target_price ≈ Test 1 result * 2 (within ±1%)
```

### Test 5: Discount Rate Inverse Test
```
Given: same as Test 1 but discount=20%
Expected: target_price < Test 1 result
```

### Test 6: Probability Weight Test
```
Given: bear=$10, base=$50, bull=$100, weights=0.25/0.50/0.25
Expected: fair_value = 0.25*10 + 0.50*50 + 0.25*100 = $52.50
Tolerance: ±$0.01
```

### Test 7: Share Dilution Test
```
Given: same as Test 1 but shares doubled
Expected: target_price ≈ Test 1 result / 2 (within ±1%)
```

### Test 8: Zero Edge Cases
```
Given: CAGR=0%, margin=0%
Expected: target_price = $0.00 (not negative, not NaN, not undefined)
```

---
*Last updated: May 2026*
*Companion to: forward-valuation-challenge.skill.md*
