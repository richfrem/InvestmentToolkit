# Self-Evolution Profile — InvestmentToolkit TradingView Plugin

**Used by:** `self-evolution` skill (agent-agentic-os)
**Purpose:** Defines the boundaries, error classifications, and reference locations
for autonomous self-healing and self-evolving behaviour within the tradingview plugin.

---

## Allowed Edit Directories

The agent may autonomously edit files in these directories (relative to repo root):

```
tradingview-cdp/core/          # Node.js CDP functions (pine.js, chart.js, alerts.js, etc.)
plugins/tradingview/scripts/   # Python wrappers (tv_pine_inject.py, pine_linter.py, etc.)
plugins/tradingview/references/ # Domain reference files and playbooks (Map, not Diary)
```

Files **outside** these directories require explicit user confirmation before any edit.

---

## Error Pattern → Tier Classification

| Error pattern | Tier | Notes |
|---------------|------|-------|
| `Cannot read properties of null` on a DOM selector | Regression | TV likely updated its DOM |
| `querySelectorAll` returns empty NodeList for known selector | Regression | Selector gone from DOM |
| `subprocess.TimeoutExpired` on a previously working command | Regression | Timing or TV load change |
| `element not found` / `not visible` / `not attached` | Regression | DOM structure changed |
| `is not a function` / `is not exported` / `has no member` | Gap | Missing capability |
| `module not found` / `Cannot find module` | Gap | Missing import or file |
| `TypeError` inside our own code (not from DOM query) | Failure | Logic/argument bug |
| `SyntaxError` in Pine Script compilation response | Failure | Script content issue |
| `JSON.parse` / `JSON.stringify` error | Failure | Shape mismatch in response |
| `process.exit` never called (subprocess hangs) | Regression | Missing exit() call (see CLAUDE.md Pitfall #8) |

---

## Domain Playbook Location

```
plugins/tradingview/references/playbooks/
```

Playbooks document known TradingView UI quirks, stable selectors, timing constants,
and recovery paths so future agents read the solution before hitting the wall.

---

## Evolution Log

```
plugins/tradingview/references/evolution-log.md
```

Append-only table of every self-evolution event: date, tier, failure, patch, outcome.

---

## Key Files for Context (read before patching)

| File | Why it matters |
|------|---------------|
| `tradingview-cdp/core/pine.js` | Pine Editor / Monaco editor automation; React fiber traversal |
| `tradingview-cdp/core/chart.js` | Chart control, Data Window, indicator list |
| `tradingview-cdp/core/trading.js` | Broker panel, order list, order execution |
| `tradingview-cdp/cli.js` | Command router — add new subcommands here |
| `plugins/tradingview/scripts/tv_client.py` | Python CDP bridge; `tv_call()` entry point |
| `.claude/CLAUDE.md` (Pitfalls section) | 16 known failure patterns with root causes |

---

## Git Hygiene for Self-Evolution Patches

After any autonomous edit:
1. Run `git diff <file>` and append the output to `evolution-log.md`
2. Do **not** commit autonomously — leave staged changes for the user to review and commit
3. Exception: reference file updates (`.md` files in `references/`) may be committed
   with message `docs(self-evolution): update <filename> — <one-line summary>`
