# Mode: external-review

This mode combines `adversarial-review` and `external-review`.

## Part: adversarial-review

Prepares a comprehensive adversarial review bundle of the investment thesis, DCF projections, target weights, and daily loop recommendations for external frontier LLMs.

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

## Part: external-review

Prepares a standalone adversarial review bundle of the investment thesis, DCF projections, and proposed weights for external LLM evaluation.

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
3. **Build Manifest**: Assemble file list including prompt, `investment_thesis.md`, an export of the current thesis from `domain_model.sqlite`, and relevant projections into `temp/bundles/file-manifest.json`.
4. **Generate Payload**: Execute `bundle.py` to create the standalone bundle file.
5. **Deliver**: Present the generated file path and clipboard instructions for external pasting.

## Verification
```bash
test -s temp/bundles/payload.md && wc -l temp/bundles/payload.md
```
