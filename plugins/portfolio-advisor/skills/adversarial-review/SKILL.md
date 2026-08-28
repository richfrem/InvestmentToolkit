---
name: adversarial_review
plugin: portfolio-advisor
description: >
  Prepares a comprehensive adversarial review bundle of the investment thesis,
  DCF projections, target weights, and the latest daily loop recommendations
  for paste into a frontier LLM (Grok, ChatGPT, Gemini). Automatically generates
  the prompt, creates the manifest, and executes the bundler to temp/bundles/payload.md.
  Trigger on /adversarial-review or "run adversarial review". Unlike
  external-review's interactive Phase 1, this skill NEVER asks a scoping
  question -- it always bundles the current daily-brief-driven payload
  (whatever holdings/standing-decisions are live today), and reuses
  external-review's bundler script rather than a separate implementation.
allowed-tools: Bash, Read, Write
---

# Adversarial Review Skill

## Purpose
This skill automates the packaging of the portfolio's core thesis and daily recommendations for external adversarial review by a frontier model (Grok, ChatGPT, Gemini). It writes the prompt, manifest, and output bundle to `temp/bundles/` so the user can easily copy and paste it. No interactive scoping question — that's what distinguishes it from `external-review` (see that skill's Phase 1 for the scoped/interactive variant); this one is the fast, always-full, daily-loop-integrated path.

---

## Core Workflow

### Phase 1 — Prompt & Manifest Generation (data-driven, no hardcoded tickers)
1. Extract the latest daily brief data using `daily_brief.py --json` — this is the ONLY source for which
   tickers appear in the prompt below. **Never hardcode ticker symbols in this file** (fixed 2026-08-28:
   this section previously named specific tickers like `CLSK, IONQ, VRT, DRAM, CRWV, PSIX` and
   `CORZ, OKLO, PANW, BE` directly in the skill doc — those went stale as the portfolio changed, exactly
   like `portfolio.json`'s staleness bug elsewhere in this project. Derive them fresh every run instead.)
2. From the parsed JSON, extract:
   - `recommendations` where `signal` is `REDUCE`/`EXIT`/`ACCUMULATE` → "Daily Actions" section
   - `thesis_breakers_triggered` and any ticker with a `standing_decision_type` set → "Standing Decisions" section (challenge the excuse for holding despite the signal)
   - The highest-conviction watchlist-only tickers (from `investment.is_watchlisted=1` with the top DCF/conviction scores, per `list_investments()`) vs. currently-funded lower-conviction tickers → "Sizing Inconsistencies" section
3. Generate a structured adversarial prompt at `temp/bundles/prompt.md` covering:
   - **Thesis Integrity**: Pillar independence, concentration risk, DCF assumption quality.
   - **Daily Actions**: Verifying today's actual REDUCE/EXIT/ACCUMULATE recommendations (from step 2, not hardcoded).
   - **Standing Decisions**: Challenging excuses/biases keeping today's actual flagged positions (from step 2).
   - **Sizing Inconsistencies**: Challenging why today's actual highest-conviction watchlist names are unfunded while lower-conviction ones are (from step 2).
4. Create `temp/bundles/file-manifest.json` pointing to:
   - `temp/bundles/prompt.md` (instructions must be first)
   - `investment_screener/backend/data/theses/investment_thesis.md`
   - `investment_screener/backend/data/theses/target-portfolio.json`
   - `investment_screener/backend/data/projections/`
   - `PortfolioAnalysis/strategic-reviews/`

### Phase 2 — Execute Bundle
Reuse `external-review`'s own bundler script (renamed 2026-08-28 from `thesis-challenge-bundler` — see
`docs/architecture/skill-renames-2026-08-28.md`) rather than a separate implementation:

- **Local Plugin Path**:
  ```bash
  python3 plugins/portfolio-advisor/skills/external-review/scripts/bundle.py \
    --manifest temp/bundles/file-manifest.json \
    --bundle   temp/bundles/payload.md
  ```
- **Marketplace / `.agents/` Installation**:
  ```bash
  python3 .agents/skills/context-bundler/scripts/bundle.py \
    --manifest temp/bundles/file-manifest.json \
    --bundle   temp/bundles/payload.md
  ```
- **On-Demand Execution (No Installation)**:
  If the bundler scripts are not installed locally, you can run or install them via `uvx`:
  ```bash
  uvx --from git+https://github.com/richfrem/agent-plugins-skills plugin-add richfrem/agent-plugins-skills/plugins/context-bundler -y
  ```

### Phase 3 — Handoff
Present the user with the copy-paste card pointing to `temp/bundles/payload.md`.
