# observations.jsonl Durability — Investigation & Recommendation

## Question

Should `observations.jsonl` be committed as authoritative source data, or generated/stored
elsewhere?

## Evidence

1. **The architecture's own `.gitignore` comment already declares the intended design.** Line 89:
   `# Intelligence read-model DB (derived/rebuildable from observations.jsonl, never committed —
   ADRs/026-028)`, immediately above the rule that excludes `intelligence.sqlite`. The comment's
   own wording — singling out the *DB* as "never committed" and naming `observations.jsonl` as
   the thing it's derived *from* — only makes sense if the JSONL itself was always intended to be
   tracked. Nobody wrote a gitignore comment explaining why the DB is excluded "because the JSONL
   is also excluded." The current untracked state of `observations.jsonl` is an omission (nobody
   ran `git add` on it after the migration ran), not a considered design decision.
2. **Direct repo precedent.** Two other `.jsonl` files already live in tracked, committed state
   in this exact pattern: `investment_screener/backend/data/predictions.jsonl` and
   `context/events.jsonl`. This project already treats git as its persistence layer for
   structured data (`target-portfolio.json`, `projections/*.json`, etc.) — `observations.jsonl`
   fits that established pattern exactly, not an exception to it.
3. **It is not a one-time migration artifact — it is the permanent operational store going
   forward.** Confirmed via `plugins/stock-valuation/skills/stock-research/SKILL.md` and
   `stock_valuation/SKILL.md`: every future research import already calls
   `intelligence.event_store --event-type RESEARCH_IMPORT ... && intelligence.view_generator
   {TICKER}`. If `observations.jsonl` stays untracked, *every future event this architecture
   generates* — not just this session's 80-row backfill — exists only on one local disk, with no
   git history, no backup, no way to recover from a lost or corrupted worktree.
4. **A related, previously unreported gap found while investigating this:**
   `investment_screener/backend/data/research/archive/` — the 80 original dated research files
   the migration moved (not deleted) as its stated safety guarantee — is **silently excluded from
   git** by a pre-existing, unrelated `.gitignore` rule: line 65's bare `archive/` pattern (under
   a "# folders to ignore" section listing personal-workspace directories like `kittywindsurf/`,
   `kittyclaude/`, `InvestmentStrategy/`). That rule predates this migration by a wide margin —
   `research/archive/` is currently the *only* directory in the entire repo named `archive`, and
   it was never the rule's intended target. Confirmed via `git status --short --ignored`: the
   directory is ignored (`!!`), not merely unstaged. Net effect: the migration's "nothing is
   deleted, only moved" safety claim is currently **not actually durable** — those 80 files exist
   solely on this worktree's local disk, with zero git-history protection, same exposure as
   `observations.jsonl`.

## Recommendation

**Commit both `observations.jsonl` and `research/archive/`.** Specifically:

1. Narrow the `.gitignore` rule on line 65 so it no longer catches
   `investment_screener/backend/data/research/archive/` — either scope it to the specific
   personal-workspace paths it was actually written for, or add an explicit negation
   (`!investment_screener/backend/data/research/archive/`) immediately after it.
2. Commit `observations.jsonl` (812 KB) and the 80 files in `research/archive/` (888 KB).
3. Leave `intelligence.sqlite` gitignored exactly as-is — it is genuinely derived/rebuildable, and
   this session proved that twice with byte-level parity checks. No change needed there.

This is not a cleanup or retirement action — it makes assets already designated to remain (per
`cleanup-readiness-review-final.md` §5) durable, which is a prerequisite for eventually retiring
anything else with confidence. `package-lock.json` (the other untracked file, npm-lockfile churn
unrelated to this migration) is out of scope for this recommendation and left for the user to
handle separately.

## Action Taken

Implemented as recommended: narrowed the gitignore rule, committed `observations.jsonl` and
`research/archive/`. See commit history for this change.
