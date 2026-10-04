---
name: weekly-review
plugin: portfolio-advisor
description: Runs weekend drift audits, calculates week-over-week performance moves across holdings, and generates weekly research sweep prompts for Grok.
---

# Weekly Review

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- Weekend drift audit evaluates holdings against target weights and DCF signals.
- Prompt output file must be written to `temp/weekly_grok_prompt.md`.
- Never execute live trade orders during weekly reviews; review is strictly analytical.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/weekly_review.py --prompt-output temp/weekly_grok_prompt.md
```

## Workflow
1. **Drift Audit**: Evaluate week-over-week price changes and allocation drift across all active holdings.
2. **Compile Prompt**: Generate structured Grok research prompt covering high-drift holdings and emerging macro catalysts.
3. **Export Prompt**: Save prompt output to `temp/weekly_grok_prompt.md` for external evaluation.
4. **Calibrate**: Review Grok findings and flag candidate weight or pillar adjustments for user consideration.

## Verification
```bash
test -s temp/weekly_grok_prompt.md && head -n 20 temp/weekly_grok_prompt.md
```
