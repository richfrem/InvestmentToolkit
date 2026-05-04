---
name: strategic_review
plugin: portfolio-advisor
description: >
  Challenge and stress-test the investment thesis against current AI valuation
  evidence, pillar performance, and market reality. Produces a structured
  assessment of which pillars are working, which are failing, and specific
  formula improvement proposals. Trigger when the user wants to review thesis
  health, question pillar sizing, or challenge underperforming positions.
  Also trigger on /strategic-review or /challenge-thesis.
allowed-tools: Bash, Read, Write
---

## Foundation Context — Load Before Running

Before executing any step, check memory for these files if they exist:
- `memory/project_dcf_analysis_corpus.md` — Full-corpus BUY/SELL/HOLD scorecard from the most recent analysis sweep. **PRIMARY INPUT** for Phase 1 Opportunity Scan.
- `memory/project_portfolio_thesis_state.md` — known EXIT-flagged positions still held, undeployed INITIATE targets, and thesis/DCF strategic conflicts. Pre-populates Step 0 gap analysis.

If memory files are absent, scan `investment_screener/backend/data/projections/` directly — load all JSON files and extract the latest AI_AGENT projection for each ticker.

---

## 🔄 Target Portfolio Lifecycle — How Targets Work

**The single source of truth for all portfolio targets is:**
`investment_screener/backend/data/theses/target-portfolio.json`

**Key rules:**
- Targets must **always sum to 100%**. After any edit, run: `python3 plugins/portfolio-advisor/scripts/validate_weights.py --normalize --write`
- After updating targets, regenerate the thesis blueprint: `python3 plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py --write`
- The web table (`ScreenerTable`) reads from the same JSON via the backend API — it is automatically in sync
- All actions (INITIATE, ACCUMULATE, TRIM, EXIT) are **derived by Python** by comparing `portfolio.json` (actual broker holdings) against `target-portfolio.json` (thesis targets). No TypeScript mirrors this logic.
- `USD_CASH` in `portfolio.json` maps to the `PSU-U.TO` thesis slot — the scripts alias this automatically

**As agent you SHOULD update target-portfolio.json multiple times per conversation** as analysis evolves. The expected pattern:
1. User starts a review → agent reads current targets and actuals
2. Agent runs DCF analysis, surfaces conflicts → proposes target changes with reasoning
3. User approves or adjusts → agent edits `target-portfolio.json` directly
4. Agent runs full refresh chain → targets reflected everywhere
5. Loop: more analysis → more target updates → re-run chain

**Do not treat existing targets as ground truth.** They are the current hypothesis. Your job is to challenge and improve them.

### ⚠️ Full Refresh Chain — Run After Every Target Change

```bash
# 1. Apply changes — --blueprint updates ALL table formats in investment_thesis.md
python3 plugins/portfolio-advisor/scripts/update_targets.py --set TICKER=X --write --blueprint

# 2. Re-lock no-change positions after any normalization
python3 plugins/portfolio-advisor/scripts/update_targets.py \
  --set GOOG=4.98 HUMN=2.86 KOID=2.69 ETHA=3.79 IBIT=2.60 COIN=3.11 CRCL=2.27 \
  --write --blueprint

# 3. Verify — confirm actions are clean
python3 plugins/portfolio-advisor/scripts/portfolio_action.py --all \
  --portfolio investment_screener/frontend/src/data/portfolio.json \
  --target investment_screener/backend/data/theses/target-portfolio.json
```

What `--blueprint` updates:
- `investment_thesis.md` Section IV (full portfolio blueprint)
- All 6-column early-section tables (Ticker | Action | Current % | Target % | Role | Conviction Note)
- All 7-column enriched tables (Ticker | Thesis Action | AI Signal | Actual % | Target % | Role | Conviction Note)

The webapp reads `investment_thesis.md` directly — every `--blueprint` run is immediately live after backend restart.

---

## 🚫 HARD GATES — Never Violate These When Proposing Target Changes

These rules override all thesis narratives and conversational momentum. No exceptions.

### Gate 1 — No INITIATE on SELL-rated holdings
- ❌ Never propose or raise a target weight for a stock where DCF action = SELL (upside < 0%)
- ✅ If the thesis narrative is compelling but price > fair value: status = WATCHLIST. Add a note: *"Strong thesis; re-evaluate when price approaches $X fair value."*
- This includes holdings the user does not currently own. A good thesis ≠ a good entry price.

### Gate 2 — No unsolicited new positions
- ❌ Never add a new INITIATE target for a stock the user has not mentioned, unless you first ask: *"I found {TICKER} compelling based on {reason} — would you like me to add it as an INITIATE target?"*
- ✅ Surface new ideas in the Opportunity Scan section. Wait for user buy-in before writing any target.

### Gate 3 — SA LP signal discipline
- ❌ Never treat an exited SA LP put (short hedge closed) as a bullish signal for a long position
- ✅ SA LP conviction = active **long** position in their 13F. Closed puts = neutral, not bullish.
- When checking SA LP alignment: only count rows in the 13F with no "Option Type" or blank option type and positive Q4 share count.

### Gate 4 — Price discipline before conviction
- Before any INITIATE proposal, state: `DCF: {action} | FV: ${X} | Current: ${Y} | Gap: {Z}%`
- If gap is negative (price > FV), block INITIATE regardless of conviction narrative.

### Gate 5 — SA LP 13F analysis must be exhaustive
- ❌ Never say "I checked the 13F" after reviewing only familiar tickers
- ✅ Parse every row in the CSV. Check every ticker against the thesis. No exceptions.
- SA LP long = common equity rows with blank Option Type and positive Q4 share count
- SA LP puts/calls that were exited are NOT bullish signals — they are neutral
- For each SA LP long NOT in the thesis, document it explicitly as MISSING or WATCHLIST

### Gate 6 — Every target requires a documented rationale
- Every holding in `target-portfolio.json` must have an `agentRationale` field before being written
- Format: `DCF: {action} | FV $X vs $Y price | {Z}% upside. SA LP: {status}. {conflict flag if any}.`
- Targets without documented rationale are not valid — add the field first, then write the target

### Gate 7 — "No change" positions must be explicitly re-locked after every normalization
- When the user says "no change" to a position, record its exact actual% and re-apply after any batch edit
- After every `--set` or `--add` command that triggers normalization, re-run `--set` on all locked positions
- Locked positions: GOOG, HUMN, KOID, ETHA, IBIT, COIN, CRCL (user-confirmed no change)
- If normalization pushes a locked position above its actual%, it will generate a false ACCUMULATE — fix immediately

### Gate 8 — SA LP conflict positions require explicit user confirmation before raising targets
- When SA LP holds a stock long but DCF shows negative upside (SELL-rated), flag as SA/DCF CONFLICT
- ❌ Do not raise the INITIATE/ACCUMULATE target for a conflict position without surfacing it to the user first
- ✅ Present the conflict: `SA LP holds {X}K shares (+Y%) BUT DCF shows {Z}% downside. Hold current target or follow SA LP?`
- Wait for user direction before adjusting the target

---

## ⭐ Phase 1: Opportunity Scan & Action Subsections

> **This section is pre-populated by `generate_review.py` using the `scan_opportunities.py` data engine.**

When you run `generate_review.py`, it automatically scans the **full DCF corpus** and your live portfolio to generate these subsections in the report:
1. **🚀 Top Profit Opportunities (INITIATE)** — Unowned BUY-rated stocks ranked by upside × confidence.
2. **🚨 EXIT Queue** — Holdings with a 0% target weight (zombies and thesis exits).
3. **✂️ TRIM Queue** — Holdings that are overweight vs their thesis target.
4. **🔵 ACCUMULATE Queue** — Holdings that are underweight AND have DCF upside.
5. **⚔️ Strategic Conflicts** — Core holdings where the DCF says SELL but the thesis says HOLD.
6. **⚠️ Stale Analyses** — Tickers needing a refresh (older than 90 days).

**Your job as the agent:** Read these pre-populated tables to inform your subsequent analysis. You do **not** need to manually scan the `projections/` directory for Phase 1.

---

## ⭐ Phase 2: Thesis Gap Analysis — What These Opportunities Reveal About Your Formula

> This answers: *"Based on what the AI found compelling outside your thesis, what does your current thesis formula appear to be missing?"*

After presenting Phase 1, analyze the opportunity list against the current thesis structure to identify systematic blind spots:

### Phase 2a: Detect Missing Themes

Analyze the top 10 tickers from the **🚀 Top Profit Opportunities (INITIATE)** table provided in the review document. 

1. For each ticker, check if its sector/theme is covered by any existing pillar in `target-portfolio.json`.
2. If it is NOT covered, group it into a "Theme Gap" (e.g., "Enterprise SaaS", "AI Infrastructure", etc.).

### Phase 2b: Present Gap Analysis

```
📊 THESIS GAP ANALYSIS — What Your Formula Appears to Be Missing
════════════════════════════════════════════════════════════════════

Based on the top unowned BUY opportunities, your current thesis has these uncovered themes:

Theme Gap 1: Enterprise SaaS / AI Workflow
  → Tickers with strong DCF conviction: CRM (+53%, conf 0.87), NOW (+45%, conf 0.82), ORCL (+52%, conf 0.77)
  → Your current thesis has no pillar covering enterprise AI workflow tooling
  → Question: Is this an intentional omission (you prefer infrastructure over SaaS layer)?
    Or a gap worth closing?

Theme Gap 2: [next theme...]

⚠️ Overlaps with your EXIT-flagged holdings: CRM, NOW are held but thesis-EXIT.
   The DCF strongly disagrees with your exit decision on these. This tension requires resolution.
```

### Phase 2c: Ask the User to React

Before proceeding to thesis-specific analysis, ask a single targeted question:

```
🔍 BEFORE I ANALYSE YOUR THESIS WEIGHTS: A few reactions needed.

The opportunity scan surfaced {N} compelling stocks you don't own (or own but thesis-EXIT).
The highest-conviction ones are: {top 3 tickers with upsides}

① Are any of these stocks you've already decided against for a reason not in the model?
  (e.g. you don't want SaaS exposure, you have a macro view against a sector)
  → This will tell me which opportunities to keep as recommendations vs. filter out.

② Do any of these represent a theme you've been MEANING to add to your thesis but haven't?
  → I'll incorporate those into the formula improvement proposals.

③ Are there major stocks you want analyzed that AREN'T in the projections corpus yet?
  (I'll note them for a `/evaluate-stock` follow-up run)
  → Answer "none" to skip.
```

> ✅ Wait for user response before proceeding to Phase 3.
> ✅ Apply user filters to all subsequent recommendations — if user says "no SaaS", suppress CRM/NOW/ORCL from proposals.

---

## ⭐ Phase 3: Sub-Strategy & Conviction Interview

> This answers: *"Are your current pillar weightings actually aligned with your conviction, or have they just drifted there by default?"*

**Run this BEFORE looking at drift/valuation numbers.** The goal is to get conviction inputs from the user *independently* of what the numbers say — so you can compare stated conviction vs. actual allocation vs. valuation.

### Phase 3a: Present Current Sub-Strategy Weights

```
📐 YOUR CURRENT FORMULA vs STATED TARGETS
════════════════════════════════════════════════════════════════════

Sub-Strategy          | Thesis Target | Actual Today | Drift    | # Holdings
----------------------|---------------|--------------|----------|----------
SA / ASI Race         | 66.0%         | 51.5%        | -14.5pp  | 12
AI-Native Security    | 8.5%          | 10.8%        | +2.3pp   | 3
Sovereign Finance     | 12.6%         | 13.1%        | +0.5pp   | 5
Quality SaaS          | 0.0%          | 1.8%         | +1.8pp   | 2 (EXIT-flagged)
Frontier Bets         | 0.0%          | 6.0%         | +6.0pp   | 3 (EXIT-flagged)
Strategic Reserve     | 13.0%         | 16.8%        | +3.8pp   | 1
```

### Phase 3b: Conviction Interview — Ask All Questions in One Message

```
💭 CONVICTION CHECK — Answer these before I score your formula:

━━━ SUB-STRATEGY CONVICTION ━━━

① SA/ASI Race is your biggest bet at 66% target. On a scale of 1-10, 
  how convicted are you in this theme RIGHT NOW (vs. 6 months ago)?
  → If conviction has decreased: which sub-sector has faded most 
    (chips / hyperscalers / physical infrastructure)?

② Sovereign Finance (crypto/stablecoin) at 12.6% target — has the 
  regulatory/macro environment changed your view here?
  → Higher conviction (ETF approvals, USDC adoption)?
  → Lower conviction (cycle risk, thin moats)?

③ Are there any sub-strategies you've been MEANING to add but haven't 
  formalized? (Based on the opportunity scan, candidates are: {themes from Phase 2})

━━━ POSITION-LEVEL CONVICTION ━━━

④ Rank your TOP 3 highest-conviction holdings right now (the ones 
  you'd be most comfortable doubling down on):
  → This will tell me where to concentrate freed capital.

⑤ Which holding has your LOWEST conviction right now — beyond the 
  obvious EXIT-flagged positions?
  → This is the first cut when we need to free capital.

⑥ Any conviction changes since the last review that aren't reflected 
  in the current thesis weights?
  → e.g. "I've gotten more bullish on INTC after the earnings call"
  → e.g. "I've lost conviction in CEG after the regulatory ruling"
```

> ✅ Wait for user response.
> ✅ Map answers to specific formula adjustment proposals in the review output.
> ✅ When user names a TOP conviction holding → raise its target weight proposal.
> ✅ When user names a LOW conviction holding → reduce its target or flag for trim.


---

## Quick Reference

- **Trigger**: `/strategic-review` or `/challenge-thesis`
- **Persona**: Adversarial Thesis Challenger — objective, data-grounded, does not protect user bias
- **Strategic Prompt**: `references/strategic_review_prompt.md` ← LLM prompt for structured output
  - **Fallback path** (if not installed alongside skill): `.agents/skills/portfolio-advisor/references/strategic_review_prompt.md`
- **Thesis Doc**: `plugins/portfolio-advisor/references/investment_thesis.md`
- **Output Dir**: `PortfolioAnalysis/strategic-reviews/` ← persisted review files for human feedback loop
- **Output Template**: `plugins/portfolio-advisor/assets/templates/PortfolioAnalysisRecommendations.md` ← canonical structure for all review files
- **Report Bootstrap Script**: `plugins/portfolio-advisor/scripts/generate_review.py` ← scaffolds a dated review file from the template with live portfolio metadata and opportunity scan pre-populated
- **Fallbacks**: `references/fallback-tree.md`

> 🚀 **First step before running any analysis:** scaffold the review file:
> ```bash
> python3 plugins/portfolio-advisor/scripts/generate_review.py
> # Creates: PortfolioAnalysis/strategic-reviews/YYYY-MM-DD-PortfolioAnalysisRecommendations.md
> # Pre-populates: portfolio header, opportunity leaderboard, and sources table
> # Agent then fills: formula score, pillar audit, conflicts, proposals
> ```

## ⚠️ Adversarial Review Constraint
> This skill is designed to **challenge** the thesis, not validate it.

- ❌ NEVER soften SELL findings because the user has conviction in a holding
- ❌ NEVER avoid naming a pillar as CRITICAL because it may be uncomfortable
- ❌ NEVER propose formula improvements that preserve current weights without evidence
- ✅ If valuation evidence contradicts thesis sizing, say so explicitly
- ✅ Distinguish between "thesis intact but entry was wrong" vs "thesis structurally broken"
- ✅ Surface performance failure (negative price return + SELL rating) as compound evidence

---

## ⚠️ Action Label Rules — MUST Follow Before Assigning Any Action

These rules are **non-negotiable**. Apply them to every holding before writing any recommendation:

| Rule | Condition | Correct Action |
|---|---|---|
| **Not in portfolio** | `shares == 0` or ticker absent from `portfolio.json` | `INITIATE` |
| **Held, underweight** | `shares > 0` AND `actualPct < targetPct` | `ACCUMULATE` |
| **Held, on target** | `shares > 0` AND `actualPct ≈ targetPct` (within 0.5pp) | `MAINTAIN` |
| **Held, overweight** | `shares > 0` AND `actualPct > targetPct` | `TRIM` |
| **Held, thesis broken** | thesis breaker triggered | `EXIT` |
| **Not held, monitoring** | not in portfolio, thesis not yet confirmed | `WATCHLIST` |

> ❌ NEVER assign `INITIATE` to a ticker the user already holds — even one share.
> ❌ NEVER assign `ACCUMULATE` to a ticker the user doesn't hold — that's `INITIATE`.
> ❌ NEVER assign `MAINTAIN` when `actualPct` differs from `targetPct` by more than 0.5pp.

The actual holdings are in `investment_screener/frontend/src/data/portfolio.json` — the canonical source, dynamically populated by the Questrade broker sync.

---

## ⚠️ Target Weightportfolio-advisorRD GATE

> **The agent MUST ensure `target-portfolio.json` targetWeights sum to exactly 100% before completing any review.**

Every time the agent proposes, adjusts, or confirms target allocations:
portfolio-advisor
1. **Validate first** — run before making changes:
   ```bash
   python3 plugins/portfolio-advisor/scripts/validate_weights.py --mode target
   ```

2. **After any allocation change** — normalize and write:
   ```bash
   python3 plugins/portfolio-advisor/scripts/validate_weights.py --normalize --write
   ```

3. **Verify** — confirm the output shows `target.total ≈ 100%` before proceeding.

> ❌ NEVER complete a strategic review without verifying target weights sum to 100%.portfolio-advisor
> ❌ NEVER manually set a `targetWeight` without running `--normalize --write` afterwards.portfolio-advisor
> ✅ The web app screener footer will show **green ✓ 100%** when the target column is corportfolio-advisor

**Canonical scripts for this skill:**

| Script | Purpose | Command |
|---|---|---|
| `update_targets.py` | **Edit target weights** — set/add/remove tickers, auto-normalizes to 100%, optional blueprint regen | `python3 plugins/portfolio-advisor/scripts/update_targets.py --set NVDA=6.5 META=4.5 --write --blueprint` |
| `generate_review.py` | **Bootstrap review file from template** — pre-populates header, opportunity scan | `python3 plugins/portfolio-advisor/scripts/generate_review.py [--date YYYY-MM-DD]` |
| `validate_weights.py` | Verify/normalize both JSONs sum to 100% | `python3 plugins/portfolio-advisor/scripts/validate_weights.py --mode both` |
| `generate_portfolio_blueprint.py` | Regenerate Section IV of `investment_thesis.md` | `python3 plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py --write` |
| `relabel_actions.py` | Correct action labels against live holdings | `python3 plugins/portfolio-advisor/scripts/relabel_actions.py --recs {json} --portfolio ...` |

**Canonical assets for this skill:**

| Asset | Purpose | Path |
|---|---|---|
| `PortfolioAnalysisRecommendations.md` | Master template for all review output files | `plugins/portfolio-advisor/assets/templates/PortfolioAnalysisRecommendations.md` |

> ⚠️ **Never hand-write a review from scratch.** Always call `generate_review.py` first to get a correctly-structured file with live metadata, then populate the AI sections.

---

## Step 0: Load Actual Portfolio Holdings

**Do this before anything else.** The actual portfolio is the ground truth.

```python
import json

# Load actual holdings from live portfolio file
with open('investment_screener/frontend/src/data/portfolio.json') as f:
    raw_holdings = json.load(f)

# Build lookup: ticker → {shares, currentValue, currentPct, bookPrice, name}
total_value = sum(h['shares'] * h['price'] for h in raw_holdings)
actual_portfolio = {}
for h in raw_holdings:
    val = h['shares'] * h['price']
    actual_portfolio[h['symbol']] = {
        'shares':      h['shares'],
        'price':       h['price'],
        'bookPrice':   h.get('book_price', 0),
        'currentValue': round(val, 2),
        'currentPct':  round(val / total_value * 100, 2),
        'name':        h.get('name', h['symbol']),
    }

print(f"Total portfolio value: ${total_value:,.0f}")
print(f"Holdings ({len(actual_portfolio)}): {sorted(actual_portfolio.keys())}")
```

# Also cross-reference with memory/project_portfolio_thesis_state.md if available
# to pre-populate known conflicts and EXIT-flagged positions before the interview

Cross-reference with thesis targets to find:
- **Thesis holdings you own** → eligible for ACCUMULATE / MAINTAIN / TRIM / EXIT
- **Thesis holdings you DON'T own** → eligible for INITIATE / WATCHLIST only
- **Portfolio holdings NOT in thesis** → flag as untracked → run Step 0b before continuing
- **INITIATE-target holdings not yet purchased** → these are your *watch list*. Cross-reference their DCF analysis from `projections/` to confirm the thesis INITIATE aligns with current valuation before deploying capital.

---

## Step 0b: Thesis Gap Analysis (Untracked Holdings Interview)

If `untrackedHoldings` is non-empty, **pause the review and run this interview before proceeding.**

For each untracked holding, present a one-line summary and ask three questions. Do all untracked tickers in a single message — don't ask one at a time.

### Presentation Format

```
📋 THESIS GAP ANALYSIS — {N} holdings need classification before review proceeds.

For each, I'll need 3 answers:

──────────────────────────────────────────────────────────────
NBIS  |  1.00%  |  P&L: +12.3%  |  No thesis on file
──────────────────────────────────────────────────────────────
  1. Is there a thesis for holding NBIS?
     → If YES: What is it in one sentence?
     → If NO: Should this be flagged for EXIT?
  2. Which pillar does it belong to?
     (Compute / AI Titans / Power / Sovereign Finance / Data Infra / Security / Applied AI / New Pillar)
  3. What's your target weight? (current: 1.00%)

[repeat for each untracked ticker]
```

### After User Responds — Apply Outcomes

| User Answer | Action |
|---|---|
| Has thesis + pillar + target | Add to `target-portfolio.json` under correct pillar; add row to `investment_thesis.md` Section IV |
| Has thesis but needs new pillar | Create new pillar in `target-portfolio.json`; add new `### Pillar N` section to `investment_thesis.md` Section II |
| No thesis | Set `action: EXIT` in the review; add to thesis breaker list in Section VII |
| "Skip for now" | Include in review as WATCHLIST with note "thesis pending" |

### Update investment_thesis.md Section IV

After the interview, add confirmed untracked holdings to the holdings table in Section IV:
```markdown
| **{Pillar}** | {TICKER} | {actual}% | {user-provided thesis sentence} |
```

### Update target-portfolio.json

For holdings with confirmed thesis + pillar:
```bash
# Read the file, add the holding to the correct pillar's holdings array:
# { "ticker": "NBIS", "targetPct": {user_target}, "role": "speculative", "thesisNote": "{sentence}" }
```

> ⚠️ Only update these files AFTER user confirms. Show a diff-style preview first:
> "I'll add NBIS to the **Compute** pillar at 1.0% target. Confirm?"

---

## Step 0c: Thesis Clarity Interview (Framework Gaps)

Run this **after Step 0b** (untracked holdings) and **before the full review**.

This step surfaces whether the thesis framework itself needs refactoring — separate from individual holdings. It checks four gap categories. Skip any category where no gaps are detected.

### Gap Detection — What to Check Automatically

```python
# Compute these from the loaded thesis + portfolio before asking questions:

thesis_version   = thesis['version']          # e.g. "7.3"
last_updated     = thesis['lastUpdated']       # e.g. "2026-05-02"
days_since_update = (today - last_updated).days

pillar_count     = len(thesis['pillars'])
pillars_over_30  = [p for p in pillars if p['targetPct'] > 30]   # concentration risk
pillars_under_2  = [p for p in pillars if p['targetPct'] < 2]    # rounding noise
unassigned_weight = 100 - sum(p['targetPct'] for p in pillars)   # formula leak

thesis_tickers  = {h['ticker'] for p in pillars for h in p['holdings']}
held_tickers    = set(actual_portfolio.keys()) - {'USD_CASH'}
not_yet_bought  = thesis_tickers - held_tickers                  # INITIATE candidates
orphaned_held   = held_tickers - thesis_tickers                  # already handled in 0b
```

### Interview Message Format

Present detected gaps in a single message — not one question at a time:

```
🔍 THESIS CLARITY CHECK — Before I run the full review, a few framework questions:

━━━ MACRO / CONVICTION ━━━
① The thesis was last updated {N} days ago. Has anything materially changed
  in your macro conviction since then? (e.g. geopolitical shift, new catalyst,
  position you've lost conviction in)
  → Answer "no change" to skip, or describe what shifted.

━━━ PILLAR STRUCTURE ━━━  [skip section if no gaps detected]
② [IF unassigned_weight > 2pp]:
  The formula has {unassigned_weight:.1f}pp unallocated. Where should this go?
  Current pillars: {pillar_names_and_weights}

③ [IF any pillar > 30%]:
  {pillar_name} is at {pct}% — above the 30% concentration limit.
  Is this intentional conviction sizing, or should it be capped?

━━━ POSITIONS WITHOUT THESIS ━━━  [skip if none]
④ [IF not_yet_bought is non-empty]:
  These are in your thesis formula but you haven't bought them yet:
  {not_yet_bought_with_targets}
  Still planning to INITIATE, or should any be removed from the formula?

━━━ CONVICTION CHANGES ━━━
⑤ Is there any holding you've changed your mind on since the last review —
  either higher conviction (want to increase target) or lower
  (considering exit or reducing target weight)?
  → Name the ticker and what changed.
```

### Applying Answers — Refactoring the Thesis

After the user responds, determine the required changes:

| Gap Type | Refactor Action |
|---|---|
| Macro conviction shift | Update thesis `## I. Core Premise` section; bump version if material |
| Pillar weight change | Update `target-portfolio.json` pillar `targetPct`; recalculate formula totals |
| Pillar restructure (merge/split/rename) | Update both `target-portfolio.json` pillars array AND `investment_thesis.md` Section II |
| Remove thesis-only holding (never bought) | Remove from `target-portfolio.json`; remove from Section IV table |
| Conviction increase/decrease on held ticker | Update `targetPct` in thesis; re-run relabeler to refresh action labels |
| Version bump required (material change) | Increment thesis version; add row to Version History table |

### Version Bump Rules

Bump the thesis version when:
- A pillar is added, removed, or renamed → **minor version** (e.g. 7.3 → 7.4)
- Core premise or macro narrative changes → **minor version**
- Only weights or individual holdings adjusted → **patch** (e.g. 7.3 → 7.3.1, or just update `lastUpdated`)

### Show Changes Before Writing

Always preview the full set of changes as a diff before writing any file:

```
📝 PROPOSED THESIS UPDATES — confirm to apply:

  investment_thesis.md:
    • Section I: [2 sentences updated — macro conviction]
    • Version History: new row 7.4 | {today} | {new theme name if changed}

  target-portfolio.json:
    • Pillar "Sovereign Finance": targetPct 18% → 20%
    • Pillar "Security": targetPct 10% → 8%
    • Holding CRWD: removed from formula (thesis broken)

  Version bump: 7.3 → 7.4

  Apply all? (yes / edit / skip)
```

> ✅ Only write files after explicit confirmation.
> ✅ After writing, re-run `relabel_actions.py` on the recommendations JSON to refresh action labels.

---

## Step 1: Load Thesis + All Valuations
```bash
# Load thesis
curl -s http://localhost:3001/api/theses | python3 -c "
import json, sys
theses = json.load(sys.stdin)
for i, t in enumerate(theses):
    print(f'{i+1}. {t[\"id\"]} — {t[\"name\"]} (v{t.get(\"version\",1)})')
"

# Load health check
curl -s "http://localhost:3001/api/theses/{THESIS_ID}/health" | python3 -m json.tool

# Load all AI projections for thesis holdings
python3 << 'EOF'
import subprocess, json

thesis_tickers = []  # populate from thesis holdings above
valuations = {}
missing = []

for ticker in thesis_tickers:
    r = subprocess.run(['curl','-s',f'http://localhost:3001/api/projections/{ticker}'],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        ai = [p for p in d if p.get('source')=='AI_AGENT']
        if ai:
            p = max(ai, key=lambda x: x.get('savedAt',''))
            th = p.get('aiThesis',{})
            sn = p.get('snapshot',{})
            fv = th.get('fairValue',0)
            price = sn.get('price',0)
            upside = round((fv - price)/price*100, 1) if price else None
            valuations[ticker] = {
                'action': th.get('action'),
                'fairValue': fv,
                'price': price,
                'upside': upside,
                'confidence': p.get('analyticsLog',{}).get('confidenceBreakdown',''),
                'model': th.get('model'),
                'analyzedAt': th.get('analyzedAt','')[:10]
            }
        else:
            missing.append(ticker)
    except:
        missing.append(ticker)

print("=== VALUATIONS ===")
print(json.dumps(valuations, indent=2))
print(f"\n=== MISSING ({len(missing)}) ===")
print(missing)
EOF
```

---

## Step 2: Build Pillar Conviction Audit
For each pillar in the thesis, aggregate valuation signals weighted by each holding's `targetWeight`:

```python
for each pillar:
    buy_weight = sum(h.targetWeight for h in pillar.holdings if valuations[h.ticker].action == 'BUY')
    sell_weight = sum(h.targetWeight for h in pillar.holdings if valuations[h.ticker].action == 'SELL')
    hold_weight = sum(h.targetWeight for h in pillar.holdings if valuations[h.ticker].action == 'HOLD')
    no_data_weight = sum(h.targetWeight for h in pillar.holdings if h.ticker not in valuations)
    total_valued = buy_weight + sell_weight + hold_weight

    if sell_weight / total_valued >= 0.5:
        signal = "CRITICAL"
    elif sell_weight > buy_weight:
        signal = "UNDER_PRESSURE"
    else:
        signal = "ALIGNED"
```

---

## Step 3: Compute Thesis Formula Health Score (0–100)
```python
score = 100
for pillar in pillars:
    holdings = get_pillar_holdings(pillar)
    sell_w = sum(h.targetWeight for h in holdings if valuations.get(h.ticker,{}).get('action')=='SELL')
    total_w = sum(h.targetWeight for h in holdings if h.ticker in valuations)
    if total_w > 0:
        sell_ratio = sell_w / total_w
        score -= sell_ratio * pillar.targetWeight * 0.5
```
> Score < 70 → thesis requires structural review. Surface this to the user prominently.

---

## Step 4: Build Valuation Gap Ranking
```python
gaps = []
for ticker, val in valuations.items():
    holding = get_holding(ticker)
    gap = (val['fairValue'] - val['price']) / val['price'] * holding['targetWeight']
    gaps.append({'ticker': ticker, 'gap': gap, 'upside': val['upside'], 'action': val['action']})

gaps.sort(key=lambda x: x['gap'], reverse=True)
thesis_confirmed = gaps[:5]   # most positive gap × weight
thesis_challenged = gaps[-5:] # most negative gap × weight
```

---

## Step 5: Identify Underperforming Pillar Patterns
For any pillar flagged UNDER PRESSURE or CRITICAL, investigate:

1. **Is the SELL pressure concentrated (1 large holding) or systemic (multiple holdings)?**
   - Concentrated → position sizing problem; the thesis idea may still be valid
   - Systemic → the pillar thesis itself may be wrong

2. **What is the actual price performance of pillar holdings since thesis inception?**
   - If multiple holdings are down significantly AND SELL-rated → compounding evidence: thesis is failing
   - If price down but fair value UP → dislocation opportunity (buy the dip case)
   - If price up but SELL-rated → entry was at wrong price, thesis overshot

3. **Specific pillar challenges to always surface:**
   - **Crypto / Bitcoin Mining** (IREN, CORZ, CIFR, CLSK, BITF, BTDR): Cyclical exposure to BTC price; thin margins at BTC trough; SELL ratings at current BTC cycle highs are a mean-reversion signal, not thesis failure
   - **Cybersecurity** (CRWD, PANW, ZS): Crowding risk; after CrowdStrike outage, execution record matters — CRWD SELL at −66% is structural, not cyclical
   - **Energy / Power** (VST, CEG, OKLO): Policy-dependent; OKLO pre-revenue, speculative — SELL at −93% reflects DCF reality on pre-revenue nuclear; CEG regulatory compression

---

## Step 6: Submit to Strategic Review LLM Prompt
Assemble the full payload and process through `references/strategic_review_prompt.md`:

```python
# Untracked = in portfolio but not in any thesis pillar
thesis_tickers = set(t for p in pillars_with_holdings for t in p.get('holdings', []))
untracked = {k: v for k, v in actual_portfolio.items() if k not in thesis_tickers}

review_payload = {
    "thesis": { "name": thesis_name, "pillars": pillars_with_holdings, "version": version },
    "actualPortfolio": actual_portfolio,          # ← LIVE positions: shares, currentPct, currentValue
    "untrackedHoldings": untracked,               # ← in portfolio but not in thesis — flag for review
    "totalPortfolioValue": total_value,
    "pillarConvictionAudit": pillar_audit,
    "valuationGapRanking": { "thesisConfirmed": thesis_confirmed, "thesisChallenged": thesis_challenged },
    "thesisFormulaScore": formula_score,
    "holdingValuations": valuations,
    "missingValuations": missing,
    "strategicConflicts": [h for h in valuations if valuations[h]['action']=='SELL' and is_core(h)]
}portfolio-advisor
```
Use `references/strategic_review_prompt.md` as the system prompt to produce structured JSON output.
**Reminder:** apply the Action Label Rules from the top of this skill before assigning any action in the output JSON.

---

## Step 6b: Refresh Portfolio Blueprint in investment_thesis.md
portfolio-advisor
After completing the analysis and before saving the review, regenerate Section IV of the thesis doc so it reflects the current broker holdings and latest action labels.

```bash
python3 plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py --write
```

This script:
- Reads `investment_screener/frontend/src/data/portfolio.json` (live Questrade holdings)
- Reads `investment_screener/backend/data/theses/target-portfolio.json` (thesis targets + subStrategyId)
- Groups holdings by sub-strategy
- Assigns INITIATE / ACCUMULATE / MAINTAIN / TRIM / EXIT per holding
- Writes the updportfolio-advisor directly into `plugins/portfolio-advisor/references/investment_thesis.md`

The web app modal reads this file — the Portfolio Blueprint section will be live-accurate after each review.
portfolio-advisor
---

## Step 6c: Valiportfolio-advisorals

Before finalising any review or updating target weights, always verify that both JSONs sum correctly using the canonical validation script.
portfolio-advisor
```bash
# Dry-run: check both JSONs, print totals to stdout
python3 plugins/portfolio-advisor/scripts/validate_weights.py --mode both

# Check current holdings only (from portfolio.json — shares × price / total)
python3 plugins/portfolio-advisor/scripts/validate_weights.py --mode current

# Check target weights only (from target-portfolio.json — sum of targetWeight fields)
python3 plugins/portfolio-advisor/scripts/validate_weights.py --mode target

# Fix: rescale all targetWeight values so they sum to exactly 100%, then write
python3 plugins/portfolio-advisor/scripts/validate_weights.py --normalize --write
```

**Expected output:**
- `current.total` → should be **~100%** (portfolio.json is the source of truth for actual holdings)
- `target.total` → should be **100%** exactly (target-portfolio.json thesis targets)

**When to run:**
- After adding, removing, or changing any `targetWeight` in `target-portfolio.json`
- After any `/rebalance` or `/strategic-review` that changes recommended allocations
- After adding a new holding to the thesis

**What the script surfaces:**
- Holdings in `portfolio.json` with no target weight (untracked positions)
- Holdings in `target-portfolio.json` not yet purchased (INITIATE candidates)
- Symbol mismatches (`USD_CASH` vs `PSU-U.TO`) that cause screener display gaps

> ⚠️ **Rule:** Never manually adjust individual targetWeights without running `--normalize --write` afterwards. The screener totals footer will show red until the sum reaches 100%.

---

## Step 7: Save Review to PortfolioAnalysis

Before presenting the report in chat, write the full review to a dated markdown file so the user can review it, annotate it, and provide feedback for follow-up research.

```python
import datetime, os, subprocess

review_date = datetime.date.today().isoformat()   # e.g. "2026-05-02"
out_dir  = "PortfolioAnalysis/strategic-reviews"
md_path  = f"{out_dir}/{review_date}-PortfolioAnalysisRecommendations.md"
json_path = f"{oportfolio-advisor_date}-PortfolioAnalysisRecommendations.json"

os.makedirs(out_dir, exist_ok=True)
# Write the full markdown report (see template below) to md_path
# Write the structured JSON companion to json_path
```

### Step 7a: Relabel Actions Using Actual Holdings

After writing the JSON companion, immediately run `relabel_actions.py` to correct all action verbs based on what the investor actually holds. This ensures INITIATE/ACCUMULATE/TRIM/EXIT/MAINTAIN are derived from the live portfolio, not guessed by the LLM.

```bash
python3 plugins/portfolio-advisor/scripts/relabel_actions.py \
  --recs "{json_path}" \
  --portfolio investment_screener/frontend/src/data/portfolio.json
```

The script applies these rules automatically:
- **Not held + buy signal** → `INITIATE`
- **Held + actual < recommended** → `ACCUMULATE`
- **Held + actual ≈ recommended** (within 0.5pp) → `MAINTAIN`
- **Held + actual > recommended** → `TRIM`
- **Held + `EXIT` already set** → `EXIT` (thesis breaker, preserved)
- **Not held + no buy signal** → `WATCHLIST`

Print the relabeling summary to chat so the user can see what changed.

**File template** — write this structure to the output file:
```markdown
# Strategic Review — {THESIS_NAME}
**Date:** {YYYY-MM-DD}
**Thesis Formula Score:** {X}/100 — {status label}
**Portfolio Value:** ${value} USD
**Status:** {one-line status}

---

## 🚀 Top Profit Opportunities — Stocks Analyzed But Not Owned
{Opportunity leaderboard table: Rank | Ticker | Upside | FV | Price | Conf | Analyzed | Key Thesis}
{Capital required note}
{⚠️ STALE flags for analyses > 90 days old}

## 📊 Thesis Gap Analysis — What Your Formula Appears to Be Missing
{Theme gaps detected from opportunity scan: each gap with tickers, conviction scores, and question for user}
{Overlap callouts: tickers held but thesis-EXIT that DCF rates BUY}

## 💭 Conviction Check Summary
{Summary of user's answers from Phase 3 interview, mapped to specific weight proposals}
{TOP conviction holdings identified → raised target proposals}
{LOW conviction holdings identified → trim/exit flags}

---

## Overall Assessment
{2–3 sentence strategicAssessment from JSON output}

## 🏛️ Pillar Conviction Audit
{table: Pillar | Target% | Actual% | Drift% | Signal | BUY% | SELL% | No Data%}

## ⚡ Thesis-Challenged Positions
{table: all SELL-rated holdings sorted by weighted gap ascending}

## 🎯 Thesis-Confirmed Opportunities
{table: all BUY-rated holdings sorted by weighted gap descending}

## ⚠️ Thesis Breaker Alerts
{For each triggered/probable/watch breaker: ticker, condition, status, required action}

## 🚨 Strategic Conflicts (SELL-rated Core Holdings)
{Per conflict: thesis rationale, valuation evidence, tension, resolution}

## 📋 Formula Improvement Proposals
{Numbered proposals with before/after weight tables}

## 🎯 Suggested Priority Actions
{Numbered action list}

## ❓ Open Questions / Feedback Requested
> These items require your input or additional research before recommendations
> can be confirmed. Edit this section and run /strategic-review again to
> incorporate your answers.

{Numbered open questions — one per item of genuine uncertainty}

## 📊 Sources Checked
{sources list}

---
*Generated by `/strategic-review` skill — {THESIS_NAME} — {date}*
```


After writing the file, tell the user:
> "I've saved the full review to `PortfolioAnalysis/strategic-reviews/{date}-PortfolioAnalysisRecommendations.md`.
> Review it, answer the **Open Questions** section, and run `/strategic-review` again — I'll incorporate your feedback and validate any contested findings with additional research."

---

## Step 8: Present Strategic Review Report
```
**Strategic Review — {THESIS_NAME}**
*Thesis Formula Score: {X}/100 — {HEALTHY / UNDER PRESSURE / REQUIRES RESTRUCTURE}*

🏛️ Pillar Conviction Audit:
| Pillar        | Target% | Signal           | BUY%  | HOLD% | SELL% | No Data |
|---------------|---------|------------------|-------|-------|-------|---------|
| AI Titans     | 12.40%  | ✅ ALIGNED        | 100%  | 0%    | 0%    | 0%      |
| Compute       | 27.65%  | 🔴 CRITICAL       | 18%   | 0%    | 52%   | 30%     |
| Power         | 9.97%   | ⚠️ UNDER PRESSURE | 27%   | 0%    | 43%   | 30%     |
| ...           | ...     | ...              | ...   | ...   | ...   | ...     |

⚡ Thesis-Challenged Positions (valuation vs thesis most misaligned):
1. {TICKER}: −{X}% FV gap, {target_weight}% target — {thesis_role}
   Thesis says: {rationale}. Valuation says: {verdict}. Tension: {one sentence}

🎯 Thesis-Confirmed Opportunities:
1. {TICKER}: +{X}% FV upside, {target_weight}% target — thesis conviction validated

📋 Formula Improvement Proposals:
{N} proposals from strategic review (see full JSON output)

⚠️ Thesis Breakers Triggered: {list or "None"}

Want me to apply any formula improvements to the thesis, or run a rebalance
recommendation using the updated weights?
```

---

## Sources Checked Declaration
```
## Sources Checked
- Thesis API: [✅ Loaded / ❌ Failed]
- All Valuations: [✅ {N}/{M} holdings / ⚠️ Missing: {list}]
- Pillar Conviction Audit: [✅ Completed / ⚠️ Partial]
- Thesis Formula Score: [✅ {X}/100]
- Strategic Review Prompt: [✅ references/strategic_review_prompt.md]
- Valuation Gap Ranking: [✅ Completed]

## Sources Unavailable
- [any failures]
```
