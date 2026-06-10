---
name: adversarial_review
plugin: portfolio-advisor
description: >
  Prepares a comprehensive adversarial review bundle of the investment thesis,
  DCF projections, target weights, and the latest daily loop recommendations
  for paste into a frontier LLM (Grok, ChatGPT, Gemini). Automatically generates
  the prompt, creates the manifest, and executes the bundler to temp/bundles/payload.md.
  Trigger on /adversarial-review or "run adversarial review".
allowed-tools: Bash, Read, Write
---

# Adversarial Review Skill

## Purpose
This skill automates the packaging of the portfolio's core thesis and daily recommendations for external adversarial review by a frontier model (Grok, ChatGPT, Gemini). It writes the prompt, manifest, and output bundle to `temp/bundles/` so the user can easily copy and paste it.

---

## Core Workflow

### Phase 1 — Prompt & Manifest Generation
1. Extract the latest daily brief data (macro regime, recommendations, standing decisions) using `daily_brief.py --json`.
2. Generate a structured adversarial prompt at `temp/bundles/prompt.md`. The prompt must instruct the reviewer to evaluate:
   - **Thesis Integrity**: Pillar independence, concentration risk, DCF assumption quality.
   - **Daily Actions**: Verifying recommendations (CLSK, IONQ, VRT, DRAM, CRWV, PSIX).
   - **Standing Decisions**: Challenging excuses/biases keeping positions in CORZ, OKLO, PANW, and BE.
   - **Sizing Inconsistencies**: Challenging why high-conviction monopolies (NVDA, AVGO, etc.) are watchlist-only while speculative second-order names have allocations.
3. Create `temp/bundles/file-manifest.json` pointing to:
   - `temp/bundles/prompt.md` (instructions must be first)
   - `investment_screener/backend/data/theses/investment_thesis.md`
   - `investment_screener/backend/data/theses/target-portfolio.json`
   - `investment_screener/backend/data/projections/`
   - `PortfolioAnalysis/strategic-reviews/`

### Phase 2 — Execute Bundle
Locate the bundler script and run it to compile the context into `temp/bundles/payload.md`. The script location depends on how the `context-bundler` or `thesis-challenge-bundler` is installed:

- **Local Plugin Path**:
  ```bash
  python3 plugins/portfolio-advisor/skills/thesis-challenge-bundler/scripts/bundle.py \
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
