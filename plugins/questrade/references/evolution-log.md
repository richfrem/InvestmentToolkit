# Evolution Log — questrade

Append-only record of every self-evolution event. Written by the `self-evolution` skill.
Do not edit manually except to correct a factual error.

| Date | Tier | Friction / Failure | Patch | Edit Type | Outcome |
|------|------|-------------------|-------|-----------|---------|
| 2026-10-04 | Tier 1 | questrade skills had non-canonical sections, legacy headings, and missing evals | Retrofitted all 7 skills to 6 canonical sections within lean budget, added missing evals for price refresh and portfolio sync | fix | PASS |
| 2026-10-08 | Tier 1 (Gap) | Executed Questrade trades were never saved: the Trade Log's newest rows were cancelled entries from May, so recommendations repeated TRIM on positions already trimmed. | Added `questrade_trades_import.py` (filled rows, stable ids, no duplicates, owner edits kept, invalid rows rejected with reasons) and a trades step in `questrade-sync-portfolio`; `questrade-activities` stays display-only and points to it. | New script + managed symlink + skill workflow + tests | Importer and CLI tests pass on real SQLite. The raw `Trades` activity field mapping is not yet captured from a live session. |
