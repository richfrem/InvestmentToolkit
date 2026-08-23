---
name: thesis_challenge_bundler
plugin: portfolio-advisor
description: >
  Prepares a standalone adversarial review bundle of the investment thesis, DCF
  projections, and proposed weights for paste into an external LLM (Grok, ChatGPT,
  Gemini). Generates a targeted critical-analyst prompt, compiles all live thesis
  artifacts into a single Markdown payload, and writes it to temp/. Trigger on
  /bundle-thesis-review, /external-review, or "bundle for external review".
allowed-tools: Bash, Read, Write
---

# Thesis Challenge Bundler Skill

## Purpose

Packages the live portfolio thesis for **adversarial external review** — designed to
be pasted into Grok, ChatGPT, or Gemini and sent with zero extra context. The
external LLM receives a structured critical-analyst prompt first, then all relevant
artifacts. It returns a scored critique, blind-spot flags, and challenge questions
that Claude cannot self-generate objectively.

---

## Core Workflow

### Phase 1 — Scope the Review

Ask the user one question to set focus:

```
What should the external reviewer prioritize?

  1. Full thesis challenge  — conviction sizing, pillar balance, DCF conflicts, bias flags
  2. DCF assumptions only  — stress-test the fair values and scenario weights
  3. Concentration / risk  — position sizing, correlation, max drawdown exposure
  4. SA/DCF conflicts       — where smart-money conviction and DCF disagree
  5. Specific ticker(s)    — e.g. "just challenge INTC and CRWV"

Type a number, a custom focus, or "all" for the full review.
```

Wait for the user's choice. Default to option 1 if they say "all" or skip.

Also confirm output format:
```
Format: Markdown payload (paste into web UI) or ZIP (for offline/email)?
Default is Markdown. Type "zip" to get a ZIP instead.
```

---

### Phase 2 — Generate the Prompt

Write a focused adversarial prompt to
`temp/thesis-challenge-{YYYY-MM-DD}/prompt.md`.

Use the template in `assets/templates/adversarial-prompt-template.md` as the
base, then inject the user's focus area from Phase 1. Pull live values:

```bash
# Get thesis name and version
python3 -c "
import json
from pathlib import Path
t = json.loads(Path('investment_screener/backend/data/theses/target-portfolio.json').read_text())
print(t['name'], '|', len(t['holdings']), 'holdings |', len(t.get('pillars',[])), 'pillars')
"

# Get current portfolio total value
python3 plugins/portfolio-advisor/scripts/validate_weights.py \
  --mode both \
  --portfolio investment_screener/backend/data/portfolio.json \
  --target investment_screener/backend/data/theses/target-portfolio.json

# Get actions summary (ACCUMULATE/TRIM/EXIT counts)
python3 plugins/portfolio-advisor/scripts/portfolio_action.py --all \
  --portfolio investment_screener/backend/data/portfolio.json \
  --target investment_screener/backend/data/theses/target-portfolio.json
```

The prompt must include:
- **Persona**: adversarial buy-side analyst, not a coach or cheerleader
- **Rules of engagement**: challenge every assumption, name every risk explicitly
- **Focus area**: injected from Phase 1
- **Required output format**: structured table + severity scores + top recommendations
- See template for full structure

---

### Phase 3 — Build the Manifest

Create `temp/thesis-challenge-{YYYY-MM-DD}/file-manifest.json`.

**The prompt.md MUST be first in the files array.**

```json
{
  "title": "Investment Thesis Challenge — {thesis_name} — {date}",
  "description": "Adversarial review bundle: investment thesis, DCF projections, proposed weights, and research reports. Focus: {focus_area}.",
  "excludes": ["*.pyc", "__pycache__", "node_modules", "*.png", "*.zip"],
  "files": [
    {
      "path": "temp/thesis-challenge-{YYYY-MM-DD}/prompt.md",
      "note": "PRIMARY INSTRUCTIONS — read this first before any other file"
    },
    {
      "path": "investment_screener/backend/data/theses/investment_thesis.md",
      "note": "Full investment thesis with version history, sub-strategies, holdings tables"
    },
    {
      "path": "investment_screener/backend/data/theses/target-portfolio.json",
      "note": "Live thesis JSON: all holdings, target weights, agentRationale, pillar structure"
    },
    {
      "path": "investment_screener/backend/data/projections",
      "note": "DCF projections for all tickers: bear/base/bull scenarios, fair values, analyst logs"
    },
    {
      "path": "PortfolioAnalysis/strategic-reviews",
      "note": "Latest portfolio review JSON: action recommendations, drift analysis"
    }
  ]
}
```

If the user requested a specific-ticker focus (Phase 1 option 5), replace the full
`projections` directory entry with individual files:
```json
{ "path": "investment_screener/backend/data/projections/INTC.json", "note": "INTC DCF" },
{ "path": "investment_screener/backend/data/projections/CRWV.json", "note": "CRWV DCF" }
```

Optionally include research reports if they exist and the focus is a specific ticker:
```json
{ "path": "investment_screener/backend/data/research", "note": "Deep-dive research reports" }
```

---

### Phase 4 — Execute Bundle

```bash
# Create temp directory
mkdir -p temp/thesis-challenge-{YYYY-MM-DD}

# Run the canonical bundler
python3 plugins/portfolio-advisor/skills/thesis-challenge-bundler/scripts/bundle.py \
  --manifest temp/thesis-challenge-{YYYY-MM-DD}/file-manifest.json \
  --bundle   temp/thesis-challenge-{YYYY-MM-DD}/payload.md
```

For ZIP output:
```bash
python3 .agents/skills/red-team-bundler/scripts/bundle_zip.py \
  --manifest temp/thesis-challenge-{YYYY-MM-DD}/file-manifest.json \
  --bundle   temp/thesis-challenge-{YYYY-MM-DD}/payload.zip
```

---

### Phase 5 — Handoff

```
╔══════════════════════════════════════════════════════════════════╗
║         THESIS CHALLENGE BUNDLE READY                           ║
╚══════════════════════════════════════════════════════════════════╝

✅ Payload: temp/thesis-challenge-{date}/payload.md
   ~{N} files  |  ~{tokens:,} tokens  |  Focus: {focus_area}

To use:
  1. Open the file: open temp/thesis-challenge-{date}/payload.md
  2. Select all → copy
  3. Paste into x.com/i/grok, chat.openai.com, or gemini.google.com
  4. Send — no additional prompt needed (instructions are embedded)

The reviewer will return:
  • Thesis challenge table (Pillar | Verdict | Score | Key Risk)
  • DCF assumption flags (any bear/base/bull weights that look off)
  • Blind spot / bias flags
  • Top 5 recommended changes with specific weight adjustments

Paste the response back here — I'll gate each recommendation through
the 8 hard gates before applying anything.
```

---

## Hard Rules

1. **Prompt always first** in the manifest — the receiving LLM must read instructions before data
2. **Never include** `portfolio.json` (contains broker account details — use thesis JSON instead)
3. **Never include** `.broker_cache`, `.env`, or any credential files
4. **Always confirm** the manifest plan with the user before running bundle.py
5. **Re-run generate_grok_prompt.py** is NOT needed here — this skill bundles the full raw data,
   not a curated Grok prompt
