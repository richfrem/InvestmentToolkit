# ADR-038: Portfolio data lives only in SQLite, and a guard test enforces it

Date: 2026-10-09
Status: Proposed

## Problem

Portfolio data moved to `domain_model.sqlite`, but the retirement of the JSON files
was done script by script from grep lists. Nothing checked that no reader or writer
was left. An audit of `main` at `415b9d3a` found 31 live reads, writes and stat
calls on `portfolio.json`, `target-portfolio.json` and related files in 14 Python
files, plus file fallbacks in Express routes, the UI position editor and the CDP
CLI. Some tools crash without the files; others silently do nothing (an empty
thesis, no price levels, a freshness gate that is always stale). The JSON audit
tool and `allowed-json-register` still labelled these files
`ALLOWED_AUTHORITATIVE_JSON`.

## Decision

1. **Portfolio data is SQLite only.** Holdings, targets, thesis state, standing
   decisions, price levels, trades, cash flows, alerts, valuations, policy and
   thesis breakers have one home, `domain_model.sqlite`, reached through the
   repositories. No JSON file, no JSON fallback.
2. **Research and analysis have one home**, the ledger `intelligence.sqlite`.
   Markdown, JSONL and JSON copies are generated exports, never read as a source.
3. **A guard test enforces it.** `plugins/toolkit-manager/scripts/audit_sqlite_usage.py`
   follows each retired file name through constants, defaults and call arguments
   and classifies every use. `plugins/toolkit-manager/tests/test_no_retired_file_access.py`
   fails on any read, stat, write, vestigial parameter or unused path constant for
   the retired files, and on any TypeScript/JavaScript reference to them or to
   `PORTFOLIO_FILE`, `THESIS_FILE`, `TARGET_PORTFOLIO_FILE`, `readPortfolio(`.
   Four one-time migration tools are allow-listed: `migrate_portfolio_to_sqlite.py`,
   `migrate_target_portfolio_to_sqlite.py`, `migrate_wave4_to_sqlite.py`,
   `migrate_account_policy_to_sqlite.py`.
   Adding to the list needs a new ADR. `run_tests.py` runs the guard in the T0 gate.
4. **Governance matches.** `audit_json_usage.py` classifies the retired names as
   `RETIRED_PORTFOLIO_DATA`, not allowed, and `ALLOWED_AUTHORITATIVE_JSON` no longer
   exists. `allowed-json-register` lists none of them.
5. **Retirement moves files, never deletes.** A retired file moves to `ARCHIVE/`
   only with the owner's explicit approval for that file.

## Consequences

- The guard is red when it lands. It turns green as the tool ports, the Express
  and React changes and the CDP CLI change complete; the T0 gate blocks until then.
- Skills and agent copies under `.agents/` are regenerated from `plugins/` by the
  plugin sync and are not audited.
- The guard is a heuristic. Python is checked by AST; TypeScript and JavaScript by
  regular expression, so a new file-name constant could slip past it.

## Alternatives rejected

- **Keep a JSON fallback for an empty database.** It hides an empty state and
  re-creates the second source of truth.
- **Retire files without a guard.** That is how the current state arose.
