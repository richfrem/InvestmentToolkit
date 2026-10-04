---
name: adversarial-review
plugin: portfolio-advisor
description: Prepares a comprehensive adversarial review bundle of the investment thesis, DCF projections, target weights, and daily loop recommendations for external frontier LLMs.
---

# Adversarial Review

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- Always bundle the full daily-brief-driven payload without interactive scoping prompts.
- Never hardcode ticker symbols in prompt generation; derive tickers fresh from `daily_brief.py --json`.
- Output prompt and manifest strictly to `temp/bundles/`.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/external-review/scripts/bundle.py --manifest temp/bundles/file-manifest.json --bundle temp/bundles/payload.md
```

## Workflow
1. **Extract State**: Query `daily_brief.py --json` to identify active REDUCE, EXIT, ACCUMULATE recommendations and standing decisions.
2. **Generate Prompt**: Compile adversarial challenge prompt covering thesis integrity, action verification, and sizing inconsistencies at `temp/bundles/prompt.md`.
3. **Assemble Manifest**: Write `temp/bundles/file-manifest.json` referencing prompt, thesis markdown, target portfolio, projections, and strategic reviews.
4. **Execute Bundle**: Package files into `temp/bundles/payload.md` using the canonical bundler script.
5. **Handoff**: Provide the user with the payload file for submission to Grok, ChatGPT, or Gemini.

## Verification
```bash
test -s temp/bundles/payload.md && head -n 25 temp/bundles/payload.md
```
