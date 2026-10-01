# News-Sweep Model Assessment — Grok, Gemini Flash, ChatGPT

Judgement of what each model is worth in the `/daily` news sweep, so the daily loop can
request the sweep from one, two or all three and weigh the answers. **Evidence base: one
session (2026-10-01), all three models given the same prompt.** Treat the ratings as a
starting prior, and update this file after each sweep that produces new evidence (see
"Maintenance").

Models as named by the user: **Grok**, **Gemini 3.8 Flash**, **ChatGPT GPT-6.1 SOL**.

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
| Speed / cost | Fast | Fast | Slow (long reasoning), long output |
| Best use | Breaking news / X sentiment, quick cross-check | Challenge or second opinion, **only after the fact-check gate** | Filings, valuation context, prompt/data auditing |

## How the daily scan should use them

1. **Default: run all three on the same prompt**, but never average them. Their errors differ,
   which is the value. Feed results into the existing `[CONFLUENCE] / [PARTIAL] / [CONFLICT]`
   verdicts. If only one can run, use ChatGPT for the filings/valuation view and Grok for
   news flow.
2. **Fact-check gate before a model's answer counts** (run it right after ingest). Compare the
   model's stated macro numbers against market data: 10-year yield (`^TNX`), VIX (`^VIX`), and for
   any ticker the model says reported earnings in the window, the latest quarterly revenue.
   A model that misses a gate item by a clear margin is **excluded from the verdicts for that
   day** (its claims become "leads to verify"), not down-weighted. Re-admit it only after it
   restates the figures correctly (Gemini did this after one challenge round).
3. **Silence from a model is not confirmation.** Today Gemini repeated the wrong SPCX $185
   anchor and Grok let it stand; only ChatGPT questioned it. Two models agreeing is not proof
   either, if they share the prompt's anchor.
4. **Treat a model's destination weights and Action labels as opinions**, not signals.
   Grok's actions mirrored the prompt, so they carry no independent information.
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
- **Targets over-allocated:** held targets sum to 95.0% and the INITIATE targets add 14.5%
  (109.5% total before any watchlist rows). Initiations cannot all be funded without trims.

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
