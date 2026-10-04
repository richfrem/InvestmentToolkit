---
name: external-review
plugin: portfolio-advisor
description: Prepares a standalone adversarial review bundle of the investment thesis, DCF projections, and proposed weights for external LLM evaluation.
---

# External Review

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- Review bundles must start with the critical analyst prompt template before any artifacts.
- Target payload bundle must be written to `temp/bundles/payload.md` or `.zip`.
- Never mutate underlying thesis files or database records during bundling.

## Quick start
```bash
python3 plugins/portfolio-advisor/skills/external-review/scripts/bundle.py --manifest temp/bundles/file-manifest.json --bundle temp/bundles/payload.md
```

## Workflow
1. **Scope Review**: Ask the user to select review focus (full thesis, DCF assumptions, concentration risk, or specific tickers) and output format (Markdown or ZIP).
2. **Compile Prompt**: Load `assets/templates/thesis-challenge-prompt.md` and customize focus areas into `temp/bundles/prompt.md`.
3. **Build Manifest**: Assemble file list including prompt, `investment_thesis.md`, `target-portfolio.json`, and relevant projections into `temp/bundles/file-manifest.json`.
4. **Generate Payload**: Execute `bundle.py` to create the standalone bundle file.
5. **Deliver**: Present the generated file path and clipboard instructions for external pasting.

## Verification
```bash
test -s temp/bundles/payload.md && wc -l temp/bundles/payload.md
```
