---
name: x-news-sweep
plugin: portfolio-advisor
description: Generates live Grok/X.com prompts from target-portfolio.json, gates responses against DCF and technical levels, and applies approved target updates.
---

# X.com News Sweep

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- Gate every recommendation against DCF fair values, live technicals, and the 8 hard gates before applying.
- Label each ticker as CONFLUENCE, PARTIAL, or CONFLICT before presenting changes.
- Never apply target changes without updating `agentRationale` and catalyst fields.
- Complete full refresh chain after applying approved modifications.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/generate_grok_prompt.py --output /tmp/grok_sweep_prompt.md
```

## Workflow
1. **Generate Prompt**: Compile live prompt from `target-portfolio.json` using tiered deep-dive formatting.
2. **Run Sweep**: Dispatch prompt via browser automation (`grok_sweep.py`) or manual copy-paste into Grok.
3. **Gate Responses**: Cross-check Grok recommendations against DCF models, technical levels, and 13F filings.
4. **Present Actions**: Display categorized changes with confluence badges and required user confirmations.
5. **Apply & Refresh**: Update targets with `update_targets.py --write --blueprint` and run verification suite.

## Verification
```bash
python3 plugins/portfolio-advisor/scripts/verify_refresh.py
```

## References
- [News Sweep Model Assessment](references/news-sweep-model-assessment.md) - Model scoring criteria, accuracy benchmarks, and historical performance evaluations.
