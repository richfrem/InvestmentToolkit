---
name: x_news_sweep
plugin: portfolio-advisor
description: >
  Generates a live Grok/X.com prompt from the current target-portfolio.json,
  receives Grok's structured response, gates each recommendation against DCF
  and the 8 hard gates, then applies approved target changes with a full
  refresh chain. Trigger on /x-news-sweep, /grok-sweep, or "run grok sweep".
allowed-tools: Bash, Read, Write
---

# X.com News Sweep Skill

## What This Skill Does

1. **Generates** a Grok prompt from live `target-portfolio.json` — always reflects current targets, actions, and DCF signals (never stale)
2. **Receives** Grok's structured table pasted back by the user
3. **Gates** every recommendation against DCF projections and the 8 hard gates (no blind applies)
4. **Applies** approved changes + updates `agentRationale` and projection `catalystUpdate` fields
5. **Runs** the full refresh chain: blueprint → review JSON → verify

---

## Phase 1 — Generate the Grok Prompt

```bash
# Standard: print to terminal for copy-paste
python3 scripts/generate_grok_prompt.py

# macOS: send directly to clipboard
python3 scripts/generate_grok_prompt.py --clipboard

# Write to file
python3 scripts/generate_grok_prompt.py --output /tmp/grok_prompt.md
```

After running, say to the user:

```
✅ Grok prompt generated — {N} active holdings, {N} INITIATE targets, {N} EXIT positions.

Paste this into x.com/i/grok (or any Grok interface) and send.
Then paste Grok's full response back here — I'll gate each recommendation
against our DCF projections and the 8 hard gates before applying anything.
```

---

## Phase 2 — Receive Grok's Response

When the user pastes Grok's table back, parse each row to extract:

```
ticker | news | thesis_impact | action_rec | target_change
```

Build an in-memory **recommendation ledger**:

```python
ledger = [
  { ticker, news, thesis_impact, action_rec, target_change_str,
    current_target, current_actual, dcf_action, dcf_upside,
    gate_status,   # APPROVED | BLOCKED | FLAGGED | CONFIRM
    gate_reason }
]
```

Load current state:

```bash
python3 scripts/portfolio_action.py --all \
  --portfolio investment_screener/frontend/src/data/portfolio.json \
  --target investment_screener/backend/data/theses/target-portfolio.json
```

---

## Phase 3 — Gate Every Recommendation

Apply all 8 gates to each recommendation **before showing the user**:

### Gate 1 — No INITIATE on DCF SELL-rated
If `action_rec = INITIATE` and DCF upside < 0%:
→ `gate_status = BLOCKED`
→ `gate_reason = "Gate 1: DCF {upside:+.1f}% — no INITIATE on SELL-rated without explicit user override"`

### Gate 2 — No unsolicited new positions
If ticker not in `target-portfolio.json` holdings at all:
→ `gate_status = CONFIRM`
→ `gate_reason = "Gate 2: {ticker} not in thesis — confirm before adding"`

### Gate 3 — SA LP put closure ≠ bullish signal
If Grok's news mentions "SA LP closed puts" or "covered puts":
→ `gate_status = FLAGGED`
→ `gate_reason = "Gate 3: Closed put = neutral hedge removal, not a long signal"`

### Gate 4 — State DCF before any INITIATE
If `action_rec = INITIATE`, prepend DCF action + upside to the display row.

### Gate 5 — SA LP exhaustive check
Note: SA LP data comes from the 13F CSV — Grok does not have the raw 13F.
Flag any SA LP claim that contradicts known Q4 2025 13F data in `target-portfolio.json`.

### Gate 6 — agentRationale required
For every approved change, `agentRationale` will be updated with catalyst note before writing.

### Gate 7 — Re-lock no-change positions
After any normalization, immediately re-lock:
`GOOG, HUMN, KOID, ETHA, IBIT, COIN, CRCL` to their actual weights.

### Gate 8 — SA/DCF conflicts require user confirmation
If `action_rec = ACCUMULATE/INITIATE` and DCF upside < -15% AND ticker not in known-conflicts list:
→ `gate_status = CONFIRM`
→ `gate_reason = "Gate 8: SA/DCF conflict — DCF {upside:+.1f}% — confirm before applying"`

**Known SA/DCF conflict allowlist** (Gate 8 waived, warns only):
`CORZ, LITE, BE, EQT, INTC`

---

## Phase 4 — Present Gated Summary

Show the user a single table before writing anything:

```
╔══════════════════════════════════════════════════════════════════╗
║         GROK SWEEP — GATED RECOMMENDATIONS                      ║
╚══════════════════════════════════════════════════════════════════╝

Ticker  Current%  New Target%   Action      Gate      News Summary
------  --------  -----------   ------      ----      ------------
CRWV    4.30%     → 5.50%       ACCUMULATE  ✅ APPROVED  Meta $21B deal...
BE      0.94%     → 3.50%       ACCUMULATE  ⚠️ WARN (SA/DCF)  Oracle 2.8 GW...
AVGO    0.00%     → 2.00%       INITIATE    🚫 BLOCKED (G1: DCF -32%)  ...
NEWT    0.00%     → 1.00%       INITIATE    ❓ CONFIRM (G2: not in thesis)  ...

Approved:  {N}  |  Warned:  {N}  |  Blocked:  {N}  |  Needs confirm:  {N}
Total weight delta if all approved: {delta:+.2f}pp
```

Then ask:
```
Apply all APPROVED changes?
Confirm any WARN/CONFIRM items above, or say "skip [TICKER]" to exclude.
Type "apply" to proceed, or adjust individual items.
```

---

## Phase 5 — Apply Approved Changes

For each approved/confirmed target change:

```bash
# 1. Apply targets + blueprint (all in one)
python3 scripts/update_targets.py \
  --set TICKER1=X.XX TICKER2=Y.YY \
  --write --blueprint

# 2. Re-lock no-change positions
python3 scripts/update_targets.py \
  --set GOOG={actual} HUMN={actual} KOID={actual} ETHA={actual} \
        IBIT={actual} COIN={actual} CRCL={actual} \
  --write --blueprint

# 3. Generate today's review JSON
python3 scripts/generate_review_json.py

# 4. Self-check — must pass before committing
python3 scripts/verify_refresh.py
```

---

## Phase 6 — Update Projection JSONs (for material catalysts)

For each ticker where Grok's news is a **material catalyst** (major contract, earnings beat,
regulatory decision, SA LP position change) — run `apply_catalyst.py`. This applies even
when no target change is made (e.g. hold confirmed after regulatory positive).

```bash
# Choose preset or use custom shifts:
#   design_win       +10pp bull / -5pp bear
#   major_contract   +8pp bull  / -5pp bear
#   funding_secured  +7pp bull  / -4pp bear
#   partnership      +5pp bull  / -3pp bear
#   earnings_beat    +5pp bull  / -3pp bear
#   thesis_breaker  -10pp bull  / +15pp bear
#   custom           requires --shift-bull and --shift-bear

python3 scripts/apply_catalyst.py \
  --ticker TICKER \
  --type PRESET \
  --note "one-line catalyst description" \
  --write \
  --update-thesis

# For custom weight shifts (e.g. regulatory):
python3 scripts/apply_catalyst.py \
  --ticker TICKER \
  --type custom \
  --shift-bull 10 --shift-bear -10 \
  --note "one-line catalyst description" \
  --write \
  --update-thesis
```

**When to run vs. skip:**

| Situation | Run apply_catalyst.py? |
|-----------|----------------------|
| Major contract / design win announced | ✅ Yes — major_contract or design_win preset |
| Regulatory risk removed (e.g. SEC dismissal) | ✅ Yes — custom bear shift |
| Earnings beat + raise | ✅ Yes — earnings_beat preset |
| Thesis breaker event | ✅ Yes — thesis_breaker preset |
| Smart money reconfirms existing hold (no new trade) | ❌ No — not a new catalyst |
| Analyst maintains price target, no new data | ❌ No — existing known info |
| Rumour / unconfirmed X post | ❌ No — wait for confirmation |

---

## Phase 7 — Session Close

```
╔══════════════════════════════════════════════════════════════════╗
║              GROK SWEEP COMPLETE                                ║
╚══════════════════════════════════════════════════════════════════╝

✅ {N} targets updated  (Investment Thesis v{version})
✅ {N} projection JSONs updated with catalystUpdate
✅ investment_thesis.md rebuilt
✅ Review JSON generated: PortfolioAnalysis/strategic-reviews/{date}-*.json
✅ verify_refresh.py: All checks passed ({N} warnings)

Changes:
  CRWV   3.32% → 5.50%   (+2.18pp)  Meta $21B deal
  BE     3.19% → 3.50%   (+0.31pp)  Oracle 2.8 GW
  ...

Next: git add / commit / push when satisfied.
```

---

## Hard Rules — Never Violate

1. **Never apply** a recommendation without running Phase 3 gates first
2. **Never skip** `verify_refresh.py` — it is the final gate
3. **Never add** a ticker not in `target-portfolio.json` without Gate 2 user confirmation
4. **Always update** `agentRationale` when changing a target
5. **Always re-lock** no-change positions after normalization (Gate 7)
6. **One prompt per session** — re-run `generate_grok_prompt.py` each session for fresh targets

---

## Sources Checked Declaration

At session end:
```
## Sources Checked
- generate_grok_prompt.py:     [✅ Generated from live target-portfolio.json]
- Grok response:               [✅ Received and parsed — {N} rows]
- DCF cross-check:             [✅ {N}/{M} projections on file]
- Gates 1-8:                   [✅ Applied — {N} blocked, {N} flagged, {N} confirmed]
- update_targets.py:           [✅ {N} targets written]
- generate_review_json.py:     [✅ Review JSON updated]
- verify_refresh.py:           [✅ All checks passed]
```
