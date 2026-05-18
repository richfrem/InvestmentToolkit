# TA + Pine Script Test Prompts

Test suite for the new TradingView skills shipped 2026-05-18.
Run in this order — each prompt builds on capabilities verified by the prior one.

## Suggested Test Order

| # | File | Skill tested | Complexity |
|---|------|-------------|-----------|
| 1 | `prompt-1-ta-guide-interactive.txt` | `ta-guide` agent — interactive guided session, indicator education, position sizing | Medium |
| 2 | `prompt-2-author-pine-script-squeeze.txt` | `/author-pine-script` — full workflow: source research → lint → inject → save | High |
| 3 | `prompt-3-tv-ta-deep-view-construction.txt` | `/tv-ta-deep` — view construction, multi-timeframe (1W→1D), community source research | High |
| 4 | `prompt-4-source-reader-study-and-author.txt` | `pine_source_reader.py` direct + cross-indicator synthesis + Map update | High |
| 5 | `prompt-5-self-evolution-stress-test.txt` | `self-evolution` — Gap + Regression tiers, DOM snapshot, evolution-log | Very High |
| 6 | `prompt-6-ta-plus-dcf-to-order.txt` | `ta-guide` → `/place-order` pipeline on a real portfolio position (PSU-U.TO) | High |

## Original Prompts (superseded)

The three original prompts are still in the folder but have been replaced:
- `prompt-1-ta-expert.txt` → replaced by `prompt-1-ta-guide-interactive.txt`
- `prompt-2-pine-injector.txt` → replaced by `prompt-2-author-pine-script-squeeze.txt`
- `prompt-3-full-loop.txt` → replaced by `prompt-3-tv-ta-deep-view-construction.txt`

## What's Being Tested

New skills shipped this session that these prompts exercise:

| Skill/File | What it does |
|---|---|
| `ta-guide` agent | Interactive TA tutor + Pine Script architect — guided session with indicator education |
| `/author-pine-script` | Full authoring: Phase 0 source research, lint gate, inject, save to library |
| `pine_source_reader.py` | Fetches live community indicator source from TV Indicators dialog |
| `pine_linter.py` | Static v6 analysis — version, declaration, lookahead, drawing var checks |
| `self-evolution` skill | Gap / Failure / Regression taxonomy, evidence collection, autonomous CDP repair |
| `self-evolution-profile.md` | TV-specific allowed dirs + error classification table for the skill |
| `evolution-log.md` | Append-only record of every autonomous fix |

## Prerequisites

- TradingView Desktop running with `--remote-debugging-port=9222`
- `cd tradingview-cdp && npm ci` (already done if using shared runtime)
- `agent-agentic-os` plugin reinstalled (includes `self-evolution` skill)
- PSU-U.TO, NVDA, AMD on TradingView watchlist for prompts 1, 3, 6
