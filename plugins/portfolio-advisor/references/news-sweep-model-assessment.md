# News-Sweep Model Assessment — Grok, Gemini Flash, ChatGPT

Judgement of what each model is worth in the `/daily` news sweep, so the daily loop can
request the sweep from one, two or all three and weigh the answers. **Evidence base: one
session (2026-10-01), all three models given the same prompt.** Treat the ratings as a
starting prior, and update this file after each sweep that produces new evidence (see
"Maintenance").

Models as named by the user: **Grok**, **Gemini 3.8 Flash**, **ChatGPT GPT-6.1 SOL**.

## Contents
- [What was actually verified on 2026-10-01](#what-was-actually-verified-on-2026-10-01)
- [Ratings](#ratings-judgement-one-session)
- [Maintenance](#maintenance)

## What was actually verified on 2026-10-01

Checked against market data / primary sources by the agent, not taken from any model:

| Claim | Truth | Grok | Gemini (pass 1) | Gemini (after challenge) | ChatGPT |
|---|---|---|---|---|---|
| US 10-year yield | 5.31% (yfinance `^TNX`) | >5.3% ✅ | 3.84% ❌ | 5.27–5.32% ✅ | 5.27–5.34% ✅ |
| MU latest quarter | FQ4: $54.23B rev, $33.42 EPS, 87% GM, FQ1 guide $61.5B (Micron 8-K / press release) | ✅ | $41.5B "Q3" ❌ (prior quarter, copied from prompt text) | ✅ | ✅ |
| Gemini 4 "Argon" announced 9/30, Fairwind-gated, $2/$10 pricing | consistent across all three | ✅ | ✅ | ✅ | ✅ (and noted 1M is an *output* limit) |
| SA LP MU weight | ~27.5% (13F, 6/30) | no figure | "47%" ❌ | — | 27.5% ✅ |
| SPCX IPO price | $135 (priced 2026-06-11), not the $185 in our prompt | did not question it | repeated $185 as fact | — | **corrected it** ✅ |
| Held positions covered | prompt omitted FOTO, HUMN, KOID (7.93% of the portfolio) | not noticed | not noticed | — | **noticed the 7.9% gap** ✅ |

Everything else each model said (contract values, 13D details, concentration percentages,
etc.) was **not independently verified** and must not be treated as fact.

## Ratings (judgement, one session)

| Dimension | Grok | Gemini Flash | ChatGPT (6.1 SOL) |
|---|---|---|---|
| Accuracy on checkable facts | High | **Low on first two passes**; high after challenge | High |
| Sourcing | Names sources, no links | Claimed "SEC corroboration" it did not have; no links | **Dated links on nearly every claim**; separates "fresh" from "background" |
| Calibration (admits what it can't verify) | Medium — "no material news" often, but missed APLD's earnings date | Low — specific unverifiable figures (e.g. CoWoS wpm, ATM dilution) | **High** — states what it could not verify, e.g. 1M tokens is output not input |
| Independence from the prompt | **Low** — every Action in its table equals the prompt's pre-assigned Action | Medium — deviated on several tickers, but copied stale anchors | **High** — challenged the prompt's own numbers and proposed its own destination weights |
| Error recovery when challenged | not needed | **Good** — corrected figures matched the checks and it withdrew unverified items | not needed |
| **Correction rounds the user had to spend** | 0 | **3+** (wrong answer, "corrected" answer still stale, then a good one); it fixed errors only when told, never by self-checking | 0 |
| Speed / cost | Fast | Fast | Slow (long reasoning), long output |
| Best use | Breaking news / X sentiment, quick cross-check | Challenge or second opinion, **only after the fact-check gate** | Filings, valuation context, prompt/data auditing |

## Addendum 2026-10-01 (later): Claude Opus 5.5 (web) and two more verified facts

The user ran the same prompt on **Claude Opus 5.5** (web) after the first three. Further facts checked afterwards:

| Claim | Truth | Grok | Gemini | ChatGPT | Opus |
|---|---|---|---|---|---|
| SA LP status | Forced to sell its public holdings to Citadel on 2026-07-30 (CNBC, TechCrunch); kept private assets (Anthropic). Its 6/30 13F describes a book that no longer exists. | ✅ reported it | ❌ "reinforces" via stale 13F | ❌ treated 6/30 13F as reinforcing | ✅ reported it, told the user to ignore SA signals until the Q3 13F |
| Fed | Raised 25bp on 2026-09-16 to 3.75–4.00%, one more hike signalled | implied higher-for-longer | ❌ "rate cuts" | not stated | ✅ |
| SNDK 9/30 close | $1,739.89 (market data) | — | — | — | ✅ exact |
| MU after-hours | ~$1,056 (-0.78% from the close) | — | — | — | ✅ |
| 10-year yield / VIX | 5.31% / ~16–17 | ✅ | ✅ after challenge | ✅ | ✅ (5.342% intraday; VIX 16.04 on 9/29) |

**Opus 5.5 (web), one session:** accurate on nearly every figure I checked (SNDK close, MU after-hours, PLTR, BE, NVDA, SYM, PSIX, yield, VIX, Fed, SA LP), with **one material miss**: it put CRDO at "~$150–170, back near your $149 entry" when it closed at $202.66 (+36% above the entry), and its "build to 3.0% now" call rested on that. Always price-check a model's entry-zone claim before acting. It reported "no verified news" rows
explicitly instead of filling them; stated its limits up front (cannot search X; which Gemini 4 specs are *not*
disclosed); corrected its own earlier error unprompted; caught the SA LP liquidation; formed independent views
(e.g. cancel the MU trim, flag the BTDR DCF/fundamentals gap, hold more cash). Weaknesses: **no source links**;
its SPCX valuation reused the prompt's share count (7.57B) and so did not catch the anchor problem ChatGPT found
(at the $135 IPO price and $1.77T valuation the implied share count is ~13B, so the prompt's figure is
unreconciled); its MU "don't trim, target 4.0%" sits below the current 4.3% weight, which is a small internal
inconsistency. Correction rounds needed: 0 (the CRDO price error was found by the agent's own check, not by the user).

**Revised picture (still one session):** ChatGPT = best sourced; Opus = best calibrated and most independent, but
unlinked and wrong on one price; Grok = strong on fresh facts, low independence; Gemini = needs the gate and repeated correction.
The SA LP miss shows ChatGPT's citations do not guarantee it has the latest context — it cited a real 13F that
was stale. Do not read "linked" as "current".

## Cadence: which models run when (decided 2026-10-01)

Cost and effort matter, so not every model runs every day.

- **Daily: Grok alone by default** (fast, strongest on fresh news). It is only acceptable with
  two safeguards that need no second model: the **fact-check gate** (10-year yield, VIX, any
  just-reported earnings vs market data) and the **coverage gate** (every held ticker, ETFs
  included). Treat its Action labels as non-independent and its un-linked claims as leads.
- **Escalate to a second model (ChatGPT first) on the same day when any of these happens:**
  an INITIATE, or an ACCUMULATE/TRIM changing a position by >20% (existing Gate 9); a binary event
  within 7 days on a position being acted on; Grok fails the fact-check gate; Grok's view
  conflicts with the brief's DCF/TA signal on a trade-relevant ticker; or a claim would change
  a trade but has no source link.
- **Weekly: run all available models** (Grok, ChatGPT, Gemini Flash, and Claude Opus when the
  user supplies it) using the weekly template. This is also when the ratings above are re-scored:
  record each model's fact-check pass/fail and any new verified strength or error, and revise
  the table only when a pattern repeats across weeks.
- **Learning cost is near zero:** every daily Grok run still records its fact-check result, so the
  ratings keep accumulating evidence without a daily multi-model run.

## How the daily scan should use them

1. **When more than one model runs (weekly, or on escalation), use the same prompt** and never average them. Their errors differ,
   which is the value. Feed results into the existing `[CONFLUENCE] / [PARTIAL] / [CONFLICT]`
   verdicts. If only one can run, use ChatGPT for the filings/valuation view and Grok for
   news flow.
2. **Fact-check gate before a model's answer counts** (run it right after ingest). Compare the
   model's stated macro numbers against market data: 10-year yield (`^TNX`), VIX (`^VIX`), and for
   any ticker the model says reported earnings in the window, the latest quarterly revenue.
   Also spot-check any price a model quotes for a name we may trade (entry-zone claims especially). A model that misses a gate item by a clear margin is **excluded from the verdicts for that
   day** (its claims become "leads to verify"), not down-weighted. Re-admit it only after it
   restates the figures correctly (Gemini did this after one challenge round).
3. **Silence from a model is not confirmation.** Today Gemini repeated the wrong SPCX $185
   anchor and Grok let it stand; only ChatGPT questioned it. Two models agreeing is not proof
   either, if they share the prompt's anchor.
4. **Treat a model's destination weights and Action labels as opinions**, not signals.
   Grok's actions mirrored the prompt, so they carry no independent information.
5. **User correction time is a real cost.** A model that needs repeated call-outs (Gemini: 3+ rounds on
   2026-10-01, fixing errors only when told) is not worth a daily slot. Keep it to the weekly comparison, and
   if it fails the fact-check gate, exclude it for the day rather than coaching it. The evidence-standard
   bullets in the sweep templates exist to prevent these rounds up front.
5. **Require a source link for any claim that changes a trade.** A claim with no link and no
   second model confirming it is a lead, not evidence.

## Defects in our own prompt/data found this session (fix at the source)

- **Coverage gap:** held tickers FOTO, HUMN, KOID (7.93%) were missing from the sweep tables, so no model covered them.
  The sweep must include every row with `quantity > 0`, checked automatically.
- **Wrong anchor:** SPCX "IPO at $185 / $1.4T market cap" is wrong ($135 IPO, ~$1.77T at pricing).
  The generated thesis text feeds every model, so one bad anchor poisons all three answers.
- **Stale anchors in prompt text:** MU's "Q3 revenue $41.5B" was pre-print; a stale anchor was
  copied by a model as if it were fresh.
- **Pre-labelled Actions** in the table cause models to echo them. Consider withholding the
  Action column and asking for an independent view first.
- **Stale SA LP section (fixed 2026-10-01):** the generated prompt said SA LP's "Q4 2025 top positions" should be flagged as
  reinforcing the portfolio, but SA LP liquidated its public book on 2026-07-30. Two of four models took the bait.
  `generate_grok_prompt.py` and the weekly template now state the liquidation (test added); news-sweep Gates 3/5/10 carry a
  non-signal note until the Q3 13F (mid-November).
- **SPCX share count unreconciled:** the prompt's "7.57B public shares" implies ~$1.1T at $145, but $1.77T at the $135 IPO price
  implies ~13B shares. Rebuild SPCX's valuation inputs from filings before trusting its DCF.
- **Targets over-allocated:** targets total **112.5%** (`update_targets.py --show`): 95.0% on held names plus 17.5% on the six
  uninitiated names (NVDA 5, META 4, VST 3, INTC 2, SYM 2, PSIX 1.5). Initiations cannot all be funded without trims, and any
  `update_targets.py --write` silently rescales every target (see DEBT-20261001-05). (An earlier version of this file said
  14.5% / 109.5%; that was an addition error.)

## Maintenance

After each sweep: (1) run the fact-check gate and record pass/fail per model with the
date, (2) add any new verified error or verified strength here, (3) revise the ratings only
when a pattern repeats across sessions — one bad answer is a data point, not a verdict.
Rule 13 in `AGENTS.md` (refine templates on ingest) still applies to the prompt defects above.

## ETFs are not stocks — the daily loop must treat them differently

Found 2026-10-01: **FOTO, HUMN, KOID** (7.93% of the portfolio) are thematic ETFs. They were
silently missing from every model's sweep because `generate_grok_prompt.py`
(`get_dynamic_exclusions()`) drops every ticker that has a file in
`investment_screener/backend/data/etf_analysis/`. That exclusion is intentional for the stock
tables, but nothing replaced it, so ETFs got no news coverage at all.
In `domain_model.sqlite` they are `asset_class = EQUITY` with `industry` starting `ETF - `
(there is no ETF asset class), so detect an ETF by **either** an `etf_analysis/{TICKER}.json`
file **or** `industry LIKE 'ETF%'`.

**What does not apply to an ETF:** earnings dates, DCF fair value / bear-base-bull, Rule of 40,
Piotroski, customer-concentration or single-company thesis-breaker questions. The brief
currently shows "DCF ACCUMULATE" with `pct_to_fv` 2.1 / 9.5 / 7.4 for FOTO / HUMN / KOID;
**the source of those figures has not been established** (they are not a company DCF), so do
not present them as a valuation. Use the ETF analysis instead.

**What applies (from `etf_analysis`, `fundType = THEMATIC_ETF`):** premium/discount to NAV,
AUM and liquidity (spread, volume), expense ratio, top-holdings composition and concentration,
overlap with stocks held directly or targeted, thesis-alignment score, and the theme's own news.
Latest saved analyses are dated 2026-09-01; if one is older than ~30 days offer `/analyze-etf {TICKER}`.

### ETF card (replaces the stock card for these tickers)
```
─── [N]/[TOTAL] · [SIGNAL]: [TICKER]  (ETF — [theme]) ─────────
  Weight: [X.X]% actual → [X.X]% target ([±X.X]% gap)   P&L: Book $[X] · Now $[Y] ([±W]%)
  NAV:    $[nav] · [premium/discount]% · AUM $[X]M · Expense [X.XX]%   [analysis dated YYYY-MM-DD]
  Top holdings: [top 5 with %] · Overlap with our direct holdings/targets: [tickers + combined weight]
  Theme news: [models' sector findings + confluence verdict]
  → Recommended: [hold / add on pullback to $X / trim to Y%] + reason
```
Never add an earnings line, a DCF line or a fair-value line to an ETF card.

### Overlap is the main ETF-specific risk
Add the ETF's weight in each shared name to the direct position before judging concentration.
Known overlaps from the saved analyses: HUMN holds **NVDA** (4.16% of the fund in the May analysis) and
KOID holds **Symbotic (SYM)**, while NVDA and SYM are both INITIATE targets; FOTO holds **Lumentum, Coherent, Ciena, Fabrinet**
while we hold **CRDO** directly (same optical-interconnect theme). Re-read the current holdings
from `etf_analysis` rather than trusting this list.

### Sector questions to put in the sweep for each ETF theme
Add these as a separate "ETF / theme" part of the sweep prompt, once per theme. Ground them in
the ETF's own current top holdings.

**Robotics & physical AI (HUMN, KOID)**
1. Humanoid deployment status: Tesla Optimus production/shipment timing and any customer orders; Ubtech, Rainbow Robotics, Robotis and other listed humanoid makers' recent orders or guidance.
2. Component bottlenecks: harmonic reducers/actuators (Harmonic Drive, Leader Harmonious), sensors and precision modules (Hexagon, Teledyne, Sensata, Amphenol) — capacity, lead times, pricing.
3. China policy and subsidy changes affecting the Chinese/Korean constituents; export-control or tariff effects.
4. Is physical-AI demand tracking the narrative (orders, unit shipments, cost per unit) or still mostly announcements? Cite numbers.
5. ETF-level: net flows, AUM, premium/discount trend, recent index reconstitution, and what the two funds hold that the other doesn't.
6. Overlap: how much of our exposure is really NVDA / SYM through these funds.

**Photonics (FOTO)**
1. Co-packaged optics (CPO) adoption timeline and which hyperscalers/switch vendors have committed; 800G → 1.6T → 3.2T transceiver demand.
2. Laser and component supply constraints (InP lasers, EML capacity, packaging) and who is allocation-constrained.
3. Latest results/guidance from the top constituents (Lumentum, Coherent, Ciena, Fabrinet and any others now in the top ten) within the sweep window.
4. Pricing and competition: pressure from copper/AEC (our direct CRDO position) vs optics; any hyperscaler design wins or losses.
5. ETF-level: why it persistently trades at a discount to NAV (about −8% on 2026-09-01), AUM trend, bid-ask spread/liquidity, expense ratio (0.85%).
6. Overlap with CRDO, and with LITE/COHR on the watchlist.

Prompt-generator follow-up (not yet built; needs a failing test first): emit an "ETF / theme"
section containing the above for every held ETF, and add a coverage assertion that every
`quantity > 0` ticker appears in either the stock tables or the ETF section.
