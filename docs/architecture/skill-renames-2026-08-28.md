# Skill Renames — 2026-08-28: Intent-Based Naming

## Why

Five skills across `portfolio-advisor` and `stock-valuation` overlapped in single-stock and
thesis-review analysis, named around *mechanism* (wizard vs. autonomous vs. bundler) rather than
*intent* (net-new ticker vs. updating an existing one). Investigating the overlap also surfaced two
real duplications, not just naming confusion:

1. `stock-intake` (net-new onboarding wizard) independently re-implemented the same
   `fetch_financials.py`/`dcf_scenarios.py` call sequence that `stock_valuation` already owned, for
   its "existing ticker thesis refresh" branch.
2. `adversarial-review` duplicated `thesis-challenge-bundler`'s prompt-generation logic with
   **hardcoded ticker names baked into the skill doc** (`CLSK, IONQ, VRT, DRAM, CRWV, PSIX` /
   `CORZ, OKLO, PANW, BE`) — the same staleness-prone pattern as the `portfolio.json` bug fixed
   earlier the same day — instead of reusing the bundler script directly.

Renamed per user decision, not to merge plugins (see reasoning below) or delete anything (per
`.agent/rules/skill-deletion-guard.md`, only renamed with explicit confirmation) — to make the
net-new-vs-existing distinction the actual command name, and to fix the two duplications alongside it.

## Old → New Mapping

| Old skill folder / name | New skill folder / name | Plugin | Primary trigger | Legacy trigger aliases (still work) |
|---|---|---|---|---|
| `skills/stock_valuation` (`stock_valuation`) | `skills/update-stock-analysis` (`update-stock-analysis`) | stock-valuation | `/update-stock-analysis` | `/evaluate-stock`, `/perform-stock-valuation` |
| `skills/thesis-challenge-bundler` (`thesis_challenge_bundler`) | `skills/external-review` (`external-review`) | portfolio-advisor | `/external-review` | `/bundle-thesis-review` |
| `skills/stock-intake` (`stock_intake`) | *(unchanged — name was already clear)* | portfolio-advisor | `/stock-intake`, `/onboard-stock` | — |
| `skills/adversarial-review` (`adversarial_review`) | *(unchanged — distinct behavior, not a duplicate: see below)* | portfolio-advisor | `/adversarial-review` | — |
| `skills/stock-research` (`stock_research`) | *(unchanged — already names its intent correctly)* | stock-valuation | `/research-stock` | — |

## Intent Map (the actual goal of this rename)

| Intent | Skill |
|---|---|
| Net-new ticker, not yet tracked | `/stock-intake` (a.k.a. `/onboard-stock`) |
| Update/augment an existing holding's full analysis | `/update-stock-analysis` |
| Quick "did something happen?" pre-check before the row above | `/research-stock` |
| Portfolio-wide external-LLM critique, scoped interactively | `/external-review` |
| Portfolio-wide external-LLM critique, fixed daily-brief-driven, no scoping question | `/adversarial-review` |
| New strategic pillar/thesis pitch (not a single ticker) | `/pitch-thesis` |

`adversarial-review` was kept as its own skill (not merged into `external-review`) because it has a
genuinely different behavior confirmed by its own eval contract: it **never asks a scoping question**
and always bundles the current daily-brief-driven payload, while `external-review` always asks the
user to scope the review first. What was fixed is that `adversarial-review` now derives its ticker
lists from live `daily_brief.py` output instead of hardcoding them, and calls `external-review`'s own
`bundle.py` script (Phase 2) instead of a parallel implementation.

## Why the plugins were NOT merged

A related question during this rename was whether `stock-valuation` should move into
`portfolio-advisor` entirely. Decided against it: `stock-valuation` is a generic "value any stock"
engine (DCF math, financials fetch, comps) with no knowledge of portfolio pillars, target weights, or
accounts — `portfolio-advisor` depends on its output, not the reverse. `.agent/rules/plugin-architecture-policy.md`
mandates loose coupling ("a plugin MUST function completely in isolation"); merging would blur that
boundary and make `portfolio-advisor` (already the largest plugin) more monolithic for no
architectural benefit — the actual problems (duplicated DCF calls, a stale hardcoded ticker list)
were fixed without needing to collapse the plugin boundary.

## What Changed, Concretely

- Two skill directories renamed via `git mv` (preserves history).
- `symlinks.json`: 11 manifest `dst`/`src` entries repointed to the new directory names.
- `plugin.json` skill lists (both plugins) updated.
- SKILL.md frontmatter (`name:`) and body text updated in both renamed skills, plus every
  cross-referencing skill/agent/eval file found via repo-wide grep (`stock-research`, `stock-intake`,
  `calibrate-targets`, `portfolio-health`, `red-team-agent`, `etf_analysis`, `x-news-sweep`,
  `adversarial-review`, both plugins' `README.md`/`CONNECTORS.md`, root `architecture.md`).
- Legacy trigger phrases (`/evaluate-stock`, `/perform-stock-valuation`, `/bundle-thesis-review`)
  intentionally left working as documented aliases — this is a rename, not a breaking change.
- **Not touched**: auto-generated tracking artifacts (`skills-lock.json`, `ecosystem_yaml_summary.md`,
  `docs/architecture/json-discovery-audit.json`, `docs/architecture/allowed-json-register.json`,
  `docs/architecture/migration-inventory-and-strategy.md`) — these are owned by their own
  regeneration tooling (e.g. the ecosystem-index-agent) and will pick up the rename on their next run
  rather than being hand-edited here.

## Verification

- `python3 .agents/skills/symlink-manager/scripts/symlink_manager.py diagnose` — all links resolve.
- `grep -rn "stock_valuation\b" plugins/ | grep -v "renamed 2026-08-28"` — only intentional historical-note mentions remain.
- Local plugin reinstall (`python3 .agents/skills/plugin-syncer/scripts/sync_with_inventory.py`) run after this change.
