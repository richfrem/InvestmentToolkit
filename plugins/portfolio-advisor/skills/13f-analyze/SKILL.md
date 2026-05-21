---
name: 13f_analyze
plugin: portfolio-advisor
description: >
  Surgical 13F analysis skill. Cross-references the latest SA LP 13F filing diff
  against target-portfolio.json to produce gated INITIATE/ACCUMULATE/TRIM/EXIT
  recommendations. Applies approved changes using update_targets.py. Trigger on
  "/13f-analyze", "analyze SA LP filing", "what does the new 13F mean for my portfolio",
  or "should I act on the 13F".
allowed-tools: Bash, Read, Write
---

# 13F Analyze Skill

## What This Skill Does

1. **Polls** for the latest SA LP 13F (runs fetch_13f.py --poll first — catches new filings automatically)
2. **Cross-references** SA LP holdings diff against `target-portfolio.json` targets and actions
3. **Gates** every signal through DCF + conflict rules (same discipline as x-news-sweep)
4. **Presents** a gated recommendation table — EXIT/TRIM/ACCUMULATE/INITIATE/HOLD/CONFLICT
5. **Applies** approved changes via `update_targets.py` with `agentRationale` updates

---

## When to Run

- **After `/13f-tracker --poll` detects a new filing** — run `/13f-analyze` immediately
- **At session start during filing windows**: May 1–15, Aug 1–15, Nov 1–15, Feb 1–15
- **To verify pending actions**: "does the SA LP filing change my plan for X?"

**To refresh / poll for new filing:**
```bash
venv/bin/python3 plugins/portfolio-advisor/scripts/fetch_13f.py --cik 0002045724 --poll
```
If new filing detected, it downloads automatically, then run `/13f-analyze`.

---

## Phase 1 — Poll and Load

```bash
# Step 1: check for and download any new filing
venv/bin/python3 plugins/portfolio-advisor/scripts/fetch_13f.py \
  --cik 0002045724 --poll

# Step 2: load diff and portfolio
cat investment_screener/backend/data/13f/0002045724_diff.json
cat investment_screener/backend/data/theses/target-portfolio.json
```

Load both files. Build a lookup: `{ ticker → { targetWeight, action, dcfSignal } }` from target-portfolio.json.

---

## Phase 2 — Cross-Reference Signals

For each SA LP position change, produce a signal:

### SA LP CLOSED a position
```
If ticker in my portfolio:
  → Signal: EXIT or TRIM (depending on conviction)
  If ticker is an INITIATE target (targetWeight > 0, not yet owned):
  → Signal: DO NOT INITIATE — SA LP exited
```

### SA LP OPENED a new position (large: >$50M)
```
If ticker NOT in my portfolio:
  → Signal: REVIEW FOR INITIATE
If ticker already in portfolio at MAINTAIN/HOLD:
  → Signal: Consider increasing target
If ticker already targeted for TRIM:
  → Signal: CONFLICT — SA initiating while you plan to trim (flag for user decision)
```

### SA LP INCREASED significantly (>+50%)
```
  → ACCUMULATE signal — reinforces any existing ACCUMULATE action
  If current action is TRIM or REVIEW:
  → CONFLICT — flag; SA may have information you don't
```

### SA LP DECREASED significantly (>-30%)
```
  → TRIM signal — reinforces any existing TRIM action
  If current action is ACCUMULATE:
  → CONFLICT — flag
```

---

## Phase 3 — Gate Every Recommendation

Apply these gates before showing the user anything:

### Gate A — No EXIT on SA call/option positions
SA LP holding only calls (put_call == "Call") is an options position, not a long equity signal.
Do NOT recommend EXIT on the underlying based on options alone.
Example: INTC — SA has $747M in calls but closed common. Flag as NUANCED, not EXIT.

### Gate B — No INITIATE on DCF SELL-rated if SA also closed
If SA closed AND DCF upside < 0%: BLOCKED — doubly bearish.

### Gate C — SA close ≠ immediate exit if high conviction thesis
If SA closed a position but the holding has a strong independent thesis (e.g. a pillar-core position):
→ gate_status = CONFIRM (user must decide)
→ gate_reason = "SA closed but thesis still intact — confirm exit intent"

### Gate D — Weight constraints
No single recommendation should push any position above 15% of portfolio.
No single recommendation should push total portfolio weight above 100%.

### Gate E — INTC special rule
SA LP holds $747M in INTC calls (13.5% of fund). They converted equity → options (Terafab upside capture).
Your INTC equity position at 9.2% → trim to 7.5% is CONSISTENT with SA's move (reduce equity, maintain thesis exposure).
Do not flag as conflict.

---

## Phase 4 — Present Gated Table

```
╔══════════════════════════════════════════════════════════════════════════╗
║          13F ANALYSIS — SA LP Q{quarter} {year}                         ║
║          Filing: {filing_date}  |  Period: {period_of_report}           ║
╚══════════════════════════════════════════════════════════════════════════╝

Ticker  Your%→Target%   Rec         Gate         SA LP Signal
------  -------------   ---         ----         ------------
VST     2.1% → 1.2%    EXIT        ✅ APPROVED   SA closed entire $252M position
TSM     0%  → 2.2%     DON'T INIT  ✅ APPROVED   SA closed $75M position
NVDA    2.1% → 2.8%    HOLD/WAIT   ⚠️ CONFLICT   SA closed $299M; your thesis says accumulate
BE      2.2% → 5.2%    ACCELERATE  ✅ APPROVED   SA #1 position $875M (15.9%)
CRWV    4.0% → 5.8%    ACCELERATE  ✅ APPROVED   SA +336%, combined 21.9% of fund
SNDK    0%  → 0.7%     INITIATE    ✅ APPROVED   SA +817% ($250M)
LITE    2.3% → 2.1%    ↑ TARGET    ❓ CONFIRM    SA new $479M (8.7%) — your target may be too low
COHR    1.2% → 0.9%    HOLD TRIM   ⚠️ CONFLICT   SA +211% while you plan to trim
INTC    9.2% → 7.5%    TRIM        ✅ NUANCED    SA converted equity→calls; trim equity consistent
PANW    5.5% → 4.8%    TRIM        ✅ APPROVED   Not in SA LP; own DCF confirms trim

Approved: {N} | Conflicts: {N} | Blocked: {N} | Confirm: {N}
```

Then ask:
```
Apply all APPROVED changes?
Confirm CONFLICT and CONFIRM items above, or say "skip [TICKER]".
Type "apply" to proceed, or adjust individual items.
```

---

## Phase 5 — Apply Approved Changes

```bash
# Apply target weight changes
python3 scripts/update_targets.py \
  --set TICKER1=X.XX TICKER2=Y.YY \
  --write --blueprint

# Re-lock no-change positions
python3 scripts/update_targets.py \
  --set GOOG={actual} HUMN={actual} KOID={actual} COIN={actual} CRCL={actual} \
  --write --blueprint

# Update agentRationale for each changed ticker
# Format: "SA LP Q{N} {year}: {specific signal — closed/new/+X%}. {action taken}."

# Generate review JSON and verify
python3 scripts/generate_review_json.py
python3 scripts/verify_refresh.py
python3 investment_screener/backend/py_services/verify_thesis_sync.py
```

---

## Phase 6 — Session Close

Print summary:
```
╔══════════════════════════════════════════════════════════════════════════╗
║              13F ANALYSIS COMPLETE                                       ║
╚══════════════════════════════════════════════════════════════════════════╝

✅ {N} targets updated  (Investment Thesis v{version})
✅ agentRationale updated for {N} tickers
✅ verify_refresh.py: All checks passed
✅ verify_thesis_sync.py: All synchronization checks passed

Changes applied:
  VST    2.1% → 0.0%   EXIT   (SA closed)
  BE     2.2% → 5.2%   ACCUM  (SA #1 position)
  ...

Deferred (confirm required):
  NVDA — SA closed but DCF strong; no change made
  LITE — target increase pending your decision
```

---

## Hard Rules

1. **Never apply** without Phase 3 gates
2. **SA calls ≠ equity signal** — distinguish options vs common stock positions
3. **Never blindly follow SA** — if your thesis contradicts SA, flag as CONFLICT, not auto-apply
4. **Always update agentRationale** — future sessions need to know why targets changed
5. **Run verify_refresh.py and verify_thesis_sync.py** — final gates before reporting done
6. **Always verify synchronization** — never leave target-portfolio.json, investment_thesis.md, or projections/ out of sync

---

## Refresh Trigger (How to Check for New Filings)

Say any of:
- "check for new SA LP 13F"
- "poll for new 13F filing"
- "any new SA LP filings?"

This runs:
```bash
venv/bin/python3 plugins/portfolio-advisor/scripts/fetch_13f.py \
  --cik 0002045724 --poll
```

If new filing found → automatically runs `/13f-analyze`.

**Filing windows:** Poll daily from May 1–15, Aug 1–15, Nov 1–15, Feb 1–15.
Q1 2026 (Jan-Mar period): filing due by ~May 15, 2026 — check now.
