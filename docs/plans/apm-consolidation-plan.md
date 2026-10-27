# APM Consolidation Plan: 6 plugins, ~64 skills -> 4 plugins, 11 hubs

Status: PROPOSED (revision 2). Nothing here is executed except etf-analysis (moved to `.apm/`, 0 symlinks, 5/5 tests pass).
Method: `packaging-with-apm`, convert mode, **Track A** (modal hubs, real co-located files, no symlinks, no copy manifests), Full APM layout.
Gate: no file moves until you approve (a) this plan, (b) each wave's mapping table.

## 0. What the packaging skill requires (reviewed in full)

Sources read: `SKILL.md`; `modes/convert-plugin-to-apm.md`, `install-apm-package.md`, `create-apm-package.md`; `legacy-plugin-conversion-guide.md`; `apm-alignment-fixes.md` (SF-1..SF-12); `acceptance-criteria.md`; `fallback-tree.md`; `agent-package-manager-overview.md`; `scaffold_apm.py`, `validate_apm_package.py`.

Rules that drive this plan:

1. **Never restructure autonomously.** Run the 5-dimension intake (answered in section 3), then review one wave at a time with a mapping table, then execute.
2. **Track A, 8-step lifecycle per wave**: (1) inventory ledger CSV, (2) build hub `SKILL.md` under 100 lines plus `references/modes/<mode>.md`, (3) co-locate scripts/assets/references as real files, (4) `evals/evals.json` and `evals/task-success.json` as root JSON arrays, (5) `audit_skill.py` plus pytest, (6) pre-purge accounting (100% of old files exist at new paths), (7) consumer transition matrix, (8) `git rm` old folders only after 1-7 pass.
3. **Knowledge parity**: every DO NOT / NEVER / confirmation-token guard, every CLI flag, every review delimiter (`PLAN REVIEW:`, `VERIFICATION:`), every fallback tree and every relative link from a retiring skill appears verbatim in the hub's mode file.
4. **Full layout** (the recommended standard): primitives only inside `.apm/` (`skills/`, `agents/`, `hooks/`, `prompts/`, `instructions/`), `type: full`, no duplicate root `skills/` or `agents/`, `.apm/` tracked in git. Agents are `*.agent.md`; `commands/` become `.apm/prompts/*.prompt.md`.
5. **Link semantics (SF-3, SF-8)**: APM rewrites **markdown links** that leave a skill folder to point into its package cache, so a markdown link from one hub to a sibling hub's file in the same plugin works after install. Paths in inline code, code blocks and plain text that climb out of the skill folder do **not** get rewritten and break. A link that leaves the plugin is not rewritten: refer to the other plugin's skill by name. A script a skill tells the agent to run must live inside that skill (`scripts/x.py`).
6. **Governance docs** (team lane): each package needs `README.md` and `docs/governance.md`; the scaffold also writes `docs/attribution.md`, `docs/package-lifecycle.md` and `.gitignore`. The validator already warns about the missing README on etf-analysis and questrade.
7. **Dual manifest risk**: a package with both `plugin.json` (or `.claude-plugin/plugin.json`) and `apm.yml` is flagged unless hybrid is documented. All 6 plugins have both today (see Decision 4).
8. **One installer per plugin**: never install the same plugin with APM and with the legacy sync (`plugin-syncer` / `.agents/ownership/*.json`); duplicate skill names result. Each converted plugin must switch installers (Decision 5).
9. **Scope discipline**: domain packages install project-locally, never `--global`. Targets: pick the smallest set (`agent-skills` or one harness); `all,agent-skills` is a routing smoke test only, and installing both `.agents/skills/` and `.claude/skills/` can show duplicate skills.
10. **Never edit deployed copies** (`.agents/skills/`, `.claude/skills/`); change the source and redeploy. Compiled files (`AGENTS.md`) are outputs.
11. **SF-12**: an agent file that mirrors a skill's `SKILL.md` carries broken relative links; write agents as short definitions that use the skill by name.
12. **Optional delegation**: the playbook pairs an orchestrator with a worker (Codex CLI) that edits files directly and never commits. Not required here; I do the work in this repo, one wave at a time, and I never commit.

Found in the full read (all references, the overview, every script docstring, the validator and the pipeline):

13. **`apm.yml` must declare `includes: auto`**, otherwise `apm install` does not deploy the local `.apm/` tree. The validator reads `metadata.packaging_mode` (`full|hybrid|overlay`) and `metadata.governance_lane`; with no `packaging_mode` it skips every structure check, including the "duplicate root primitives" check. **My earlier `apm.yml` files for etf-analysis and questrade have neither, so their "VALIDATION PASSED" was vacuous.** They get `includes: auto`, `metadata.packaging_mode: full`, `metadata.governance_lane: team` (section 12).
14. **Claude marketplace conflict.** The repo has `.claude-plugin/marketplace.json` listing all 6 plugins with `"strict": true`. `strict: true` requires each plugin's own `plugin.json` and Claude Code's plugin loader auto-discovers `skills/` at the plugin root, not `.apm/skills/`. Moving skills into `.apm/` therefore stops Claude's `/plugin` flow from finding them (my etf-analysis and questrade moves already did). `strict: false` would forbid a `plugin.json` that declares components. `apm pack` produces a plugin-format bundle (`skills/ agents/ plugin.json` synthesized) in `build/`, so the marketplace can only point at packed bundles, not at `./plugins/<name>`. See Decision 4.
15. **Deployment target**: `apm install` deploys skills to the converged `.agents/skills/<skill>/` (and `.claude/skills/` for Claude), the same folders the repo already uses. `.agents/` and `.claude/` are gitignored here, so deployed copies are ephemeral by design. `apm_modules/_local/` holds links to local packages (generated, gitignored; this is not a source symlink). A root `apm.yml` plus committed `apm.lock.yaml` would replace the legacy sync; the exact local-path dependency syntax for 0.33.0 is verified in a Wave 0 spike.
16. **MCP servers** belong in `apm.yml` under `dependencies.mcp`, and APM writes each harness's MCP config at install time. Questrade's root `.mcp.json` (one HTTP server, `https://mcp.questrade.com/v1/brokerage/mcp`) moves there.
17. **Dev-only primitives** (release checklists, internal tools) live outside `.apm/` (for example `dev/`) and are listed under `devDependencies`; `apm pack` excludes them. The migration tooling and maintenance audits can use this.
18. **Tools in the skill I will use, and not use.**
    - Use: `validate_apm_package.py` (after the manifest fix in rule 13), `apm install --dry-run` and a real install into a temp git fixture (patterned on `run_test_deploy` in `apm_build_pipeline.py`, because the pipeline itself only inspects plugins that still have a root `skills/`), `check_for_broken_symlinks.py` to cross-check my inventory, `audit_marketplace_sources.py`, and `decouple_agent_paths.py` (dry-run today: 5 rewrites, 44 mentions needing review; it handles `.agents/skills/...` install-folder paths, so the new tool reuses its rules R1-R3 and its exclusion list).
    - Do not use: `materialize_copies.py`, `convert_symlinks_to_manifest.py`, `fix_inside_plugin_symlinks.py`, `apply_symlink_repairs.*`. They are Track B copy-manifest and symlink tooling, and the last two create symlinks, which contradicts Track A.
    - Optional: `apm_consumer.py` only for global, pinned installs of universal tooling; domain plugins never go global.

## 1. Target architecture

| Plugin | Absorbs | Skills now | Hubs |
|---|---|---|---|
| `questrade` | (unchanged) | 9 | 2 |
| `toolkit-manager` | (unchanged) | 3 | 1 |
| `tradingview` | (unchanged, stays a separate integration) | 27 | 3 |
| `portfolio-advisor` | + `stock-valuation` + `etf-analysis` | 20 + 4 + 1 | 5 |

Totals: 6 plugins -> 4, 64 skills -> 11 hubs. Agents (4 in portfolio-advisor, 1 in tradingview) move to `.apm/agents/*.agent.md`.
Why tradingview stays separate: a CDP broker/chart integration with its own runtime (TradingView Desktop, debug port 9222). `broker_sources.py` treats it as a peer of questrade. Analysis skills should not carry that prerequisite.
Old plugin names that disappear: `stock-valuation` and `etf-analysis` (both into `portfolio-advisor`).

### Target package layout (each of the 4 plugins)

```
plugins/<plugin>/
  apm.yml                      (type: full, targets, governance_lane: team)
  README.md  .gitignore
  docs/governance.md  docs/attribution.md  docs/package-lifecycle.md
  .apm/
    skills/<hub>/SKILL.md (<100 lines)
                 references/modes/<mode>.md   references/<owned docs>
                 scripts/  assets/  tests/  evals/evals.json  evals/task-success.json
    agents/<name>.agent.md
    prompts/<command>.prompt.md   (only if a command file exists today)
    hooks/  instructions/         (only if needed)
  .mcp.json (questrade only)
```
No `scripts/ assets/ references/ tests/ skills/ agents/` at plugin level.

## 2. Rules that apply to every wave

1. **No symlinks in any plugin.** `symlinks.json` has 212 entries, 103 portfolio-advisor / 33 tradingview / 30 stock-valuation / 14 questrade / 7 toolkit-manager on-disk symlinks. Entries are deleted as each plugin converts; the file is removed when empty.
2. **Hub `SKILL.md` under 100 lines**: constraints, a mode dispatch table, verification. One mode file per absorbed skill.
3. **Slash commands survive as mode names** (`/update-stock-analysis`, `/tv-place-order`, ...). Skill folder names change, so every consumer gets a 1:1 transition matrix.
4. **Repo-root discovery**: no `Path(__file__).parents[N]`. Use the inline marker walk (nearest ancestor containing `investment_screener/`), as `persist_etf_analysis.py` already does. Known offenders: comps_valuation, dcf_scenarios, persist_research, rebase_equity_valuations, persist_valuation, fetch_financials, the portfolio-advisor scripts using `repo_root.py`, and any test using `parents[3]`.
5. **Script placement rule** (Decision 1): a script is **engine** if the backend imports it, or two or more hubs use it. Engine scripts become real files in `investment_screener/backend/py_services/` (27 symlinks go away). Every other script is **skill-owned**, in its hub's `scripts/`.
6. **Tests live with the code**: engine tests to `investment_screener/backend/tests/py_services/`, skill-owned tests to the hub's `tests/`.
7. **Shared documents** (Decision 2): one owner hub per document. Because portfolio-advisor becomes one plugin, other hubs can link to the owner's file with a relative **markdown** link (`../setting-portfolio-targets/references/recommendation-coherence.md`), which APM rewrites on install and which also resolves in the repo's own `.agents/skills/` copy. Cross-plugin needs (tradingview, questrade) refer by skill name. No copies.
8. **Historical records are not rewritten**: `evolution-log.md` files, ADRs, handovers, `ARCHIVE/`, `temp/`. An append-only log that is rewritten stops being a record. The rewrite tool excludes them and, where useful, appends a one-line "paths moved in <wave>" note.
9. **Generated documents are regenerated, not edited**: `docs/architecture/json-discovery-audit.*`, `allowed-json-register.*`, `file-dependency-register.json`. They come from `plugins/toolkit-manager/scripts/audit_file_dependencies.py`, `audit_sqlite_usage.py` and `test_audit_json_usage.py`. These two scripts are **not orphans** (corrected from revision 1): they are the regenerators and belong in `managing-the-toolkit` as the `maintenance-audits` mode.
10. **Per-wave exit**: ledger complete, rewrite tool `verify` clean, full test suites pass against the baseline (section 5), `audit_skill.py` on every hub, `validate_apm_package.py` on the plugin, `apm install --dry-run`, regenerated registers, regenerated `.agents/skills` (Decision 5).

## 3. Intake (the playbook's 5 dimensions, answered from the analysis)

1. **Repo / baseline**: `/Users/richardfremmerlid/Projects/InvestmentToolkit`, branch `main`, **not a clean tree**: uncommitted work already exists (my etf-analysis and questrade moves, the news-sweep template and test edits, `symlinks.json`, the KOID database flag). Needs your decision: commit or stash a checkpoint before wave 1 so each wave's diff is reviewable.
2. **Footprint**: 6 plugins, ~64 skills, 212 `symlinks.json` entries, ~190 plugin symlinks, 27 backend symlinks into plugins, 268 files referencing plugin paths (153 `.py`, 95 `.md`, 12 `.json`, 4 `.ts`, 2 `.js`, 1 `.tsx`, `.gitignore`), 100 deployed skills in `.agents/skills/` generated by the plugin sync.
3. **Design aspiration**: 4 plugins, 11 modal hubs (section 1).
4. **Pitfalls**: backend and ~15 backend tests import valuation modules through `py_services` symlinks; TS/JS code references plugin paths; scripts use fixed-depth root detection; several skills cite files that do not exist (section 9); append-only logs must not be rewritten; TradingView needs Desktop on port 9222; Questrade needs an interactive browser sign-in.
5. **Consumers and data boundaries**: the backend app and its tests; `AGENTS.md`; `.agents/skills`; `.agents/ownership/*.json`; `docs/`. Strictly untouched: `domain_model.sqlite`, `intelligence.sqlite`, `investment_screener/backend/data/**`, `.runtime/`, `context/`, `temp/`, `ARCHIVE/`, `tradingview/audit/*.jsonl` (moved out only after the writer path is confirmed).

## 4. Decisions needed from you

1. **Engine home** (blocks waves 3 and 4): real files in `py_services` (recommended), versus inside a skill with the backend re-pointed, versus copies.
2. **Shared documents**: owner hub plus relative markdown link within the plugin, refer-by-name across plugins (recommended), versus a copy per skill.
3. **Orphan disposition** (section 8).
4. **Distribution channel and manifests** (changed by the full read, rule 14). The repo's `.claude-plugin/marketplace.json` lists 6 plugins with `strict: true`. Options:
   - **A. APM only (recommended):** retire the hand-written `plugin.json` and `.claude-plugin/plugin.json`, replace the marketplace file with 4 entries that point at `apm pack` bundles (or drop the marketplace if you do not use `/plugin install` from this repo), and deploy through APM. One layout, no dual manifest.
   - **B. Keep the Claude marketplace working from source:** requires plugin-native `skills/` at each plugin root, which is the deprecated Hybrid layout and a duplicate of `.apm/skills`. Contradicts "no duplicates".
   - Do you install any of these plugins via `/plugin install ...@investment-toolkit-plugins` today? If not, A costs nothing.
5. **Deployment**: after conversion, deploy with APM (a root `apm.yml` listing the 4 local plugins plus a committed `apm.lock.yaml`, `--target agent-skills` and `claude`), replacing the legacy sync and retiring `.agents/ownership/*.json` for converted plugins, versus teaching the legacy sync to read `.apm/skills`. Never both for the same plugin. The local-path dependency syntax is confirmed in a Wave 0 spike before you decide.
6. **Checkpoint**: commit (or stash) current changes before wave 1.
7. **Governance lane**: `team` (README plus `docs/governance.md`; recommended), `experimental`, or `enterprise` (adds `apm-policy.yml`).

## 5. Wave 0: baseline, ledger, rewrite tool (before any move)

**Status: DONE (2026-10-26).** Everything is under `docs/plans/apm-migration/`; no other file was touched by Wave 0.
- `baseline-tests.md` + `baseline/`: 1,771 backend Python, 237 backend TypeScript, ~590 plugin tests pass; **9 expected failures**, all pre-existing and unrelated to moved files (live data, live TradingView, one that also fails on a clean `HEAD`).
- `inventory-before.csv`: 581 entries at `HEAD` (390 files, 191 symlinks); `external-links-before.csv`: 27 backend symlinks into plugins.
- `mapping.yaml` -> `master_migration_inventory.csv` (581 rows, **0 unmapped**, 2 collisions, 9 items pending your decision) and `name-map.csv` (515 rows). Correction to the plan: the "typo duplicate" reference file is a symlink, so it is simply retired.
- `reference-index.csv`: 4,753 occurrences in 861 files after excluding the data boundary and generated files. Outside `plugins/`, only 206 hard path references in 88 files need rewriting (plus the retired `symlinks.json`).
- `tools/rewrite_references.py` (`scan`, `plan`, `apply`, `rollback`, `verify`) with 13 passing tests in `tools/test_rewrite_references.py`; `tools/build_inventory.py`, `tools/build_ledger.py`, `tools/run_baseline.sh`.
- `spike-results.md`: relative `apm install ./plugins/<x>` works; hubs deploy to `.agents/skills/<hub>/` and `.claude/skills/<hub>/`; cross-hub markdown links are rewritten and resolve after install; uninstall is clean; `apm pack` writes a generated `.claude-plugin/plugin.json` into the package (gitignore it).
- Open collisions: `plugins/stock-valuation/tests/test_comps_valuation.py` and `test_reverse_dcf.py` already exist in `investment_screener/backend/tests/py_services/` (wave 4 must merge them).
- Nothing is committed; the working tree still holds my earlier etf-analysis/questrade moves, so Decision 6 (checkpoint) is needed before wave 1.

Deliverables as originally specified:

Deliverables, all under `docs/plans/apm-migration/` (new folder; nothing else is touched):

1. **Baseline test run** recorded in `baseline-tests.md`: backend pytest, plugin pytest (6 plugins), the TypeScript/JS tests, `verify_refresh.py`, link check. Regressions after each wave are measured against this, not against assumptions.
2. **`inventory-before.csv`**: every file under `plugins/` (including symlinks, with link target), generated by script. Columns: `old_path, old_plugin, old_skill (or "-"), kind (script|asset|reference|test|eval|agent|manifest|skill-md|data|other), type (file|symlink), symlink_target, size, sha256, tracked, imported_by_backend, used_by_skills`.
3. **`master_migration_inventory.csv`** (the playbook's ledger, extended): `Old Path, New Path, Action, Notes` plus `wave, new_plugin, new_hub, new_mode, scope (engine|skill), policy`. `Action` is one of `MOVED_TO_SKILL`, `CONSOLIDATED_INTO_SKILL`, `MOVED_TO_ENGINE`, `RETIRED_SYMLINK`, `DELETED_DUPLICATE`, `ARCHIVED`, `KEPT`. Initialised from the baseline; the `New Path` column is filled per wave from the approved mapping table.
4. **`name-map.csv`** (identifier map used by the rewrite tool). Columns: `kind (plugin|skill|mode|command|script|asset|reference|agent|test|eval), old_id, old_path, new_id, new_path, hub, mode, wave, policy (rewrite|keep|retire)`. Covers:
   - old plugin names: `stock-valuation`, `etf-analysis` -> `portfolio-advisor`; the four surviving names map to themselves;
   - every old skill name (64) -> hub plus mode; slash commands are `policy=keep`;
   - every script basename and path -> new location (engine or skill);
   - every asset and reference -> new owner path;
   - every agent file -> `.apm/agents/<name>.agent.md`.
5. **`reference-index.csv`** (stale-reference inventory) produced by the tool's `scan`: every occurrence across the repo of any old path, plugin name, skill name, script basename, asset, reference or command. Columns: `file, line, token, context (path|relative-path|name|command|code|prose|json-value|python-path-expr), rule, proposed_replacement, status`.
6. **`rewrite_references.py`** with unit tests (spec in section 6).
7. **Mapping tables for all four plugins** written into the ledger, approved wave by wave.
8. **APM spike** in a temp git fixture under `build/` (nothing in the repo): on 0.33.0 confirm (a) the local-path dependency syntax for a root `apm.yml`, (b) that `includes: auto` plus `metadata.packaging_mode: full` deploys a hub with `references/modes/` to `.agents/skills/<hub>/` and `.claude/skills/<hub>/`, (c) that markdown links between sibling hubs are rewritten and resolve, (d) what `apm pack` emits for the marketplace option, (e) why `apm uninstall _local/etf-analysis` failed in the earlier pipeline run ("No apm.yml found" in the fixture).
9. **Cross-check**: run `check_for_broken_symlinks.py` and `decouple_agent_paths.py` (dry-run) and reconcile their inventories with `inventory-before.csv`, so the three agree before anything moves.

## 6. Reference rewrite tool (`docs/plans/apm-migration/tools/rewrite_references.py`)

Purpose: update every stale reference in documentation, code, tests, diagrams and config after each wave, deterministically and reversibly.

**Scope**: tracked and untracked non-ignored files with extensions `.md .mmd .py .js .ts .tsx .json .yml .yaml .sh .ps1 .toml .txt .template .sql .html .csv` plus `.gitignore` and extensionless scripts. Excluded: `.git`, `node_modules`, `venv`, `build`, `ARCHIVE`, `temp`, `.agents/` and `.claude/` (generated, gitignored), historical records (`evolution-log.md`, `map-debt.md`, `CHANGELOG.md`, `backlog.md`, `research/`, ADRs, handovers; the same set `decouple_agent_paths.py` excludes). Unlike that tool, `tests/` and `docs/plans/` are **in scope**, because tests and plans carry plugin paths that must be updated (`docs/plans/apm-migration/` itself is excluded). The tool reuses the skill's `decouple_agent_paths.py` rules R1-R3 for install-folder paths (`.agents/skills/<self>/scripts/x.py` -> `scripts/x.py`) and runs after it, not instead of it.

**Subcommands**
- `scan`: builds `reference-index.csv` (no writes to source files).
- `plan --wave N`: unified diff per file plus a summary; exits non-zero when ambiguous matches remain.
- `apply --wave N`: refuses unless the git tree is clean apart from the wave's own files; writes `patches/wave-N.patch` (rollback); idempotent (a second run changes nothing).
- `verify`: fails if any old token remains outside the exclusion list, or if any new path does not resolve.

**Rule classes (longest match first, identifier boundaries respected, so `update_targets` never matches `update_targets_v2`)**
1. Repo-relative paths (`plugins/stock-valuation/scripts/wacc.py` -> its engine or hub path).
2. Plugin-relative and skill-relative fragments (`skills/update-stock-analysis/...`, `../../scripts/x.py`), resolved against the containing file's own location.
3. Plugin-name tokens (`plugins/<old>`, frontmatter `plugin: <old>`, `symlinks.json`, JSON `canonical_path`).
4. Skill-name tokens: slash commands kept; prose and frontmatter references rewritten to `<hub>` plus mode; ambiguous contexts are reported, never guessed.
5. `symlinks.json` entries are deleted by rule, not rewritten; ownership manifests are regenerated by the deployer, not rewritten.
6. TypeScript/JavaScript string paths and spawn arguments (4 `.ts`, 2 `.js`, 1 `.tsx` files reference plugin paths today).
7. Mermaid `.mmd` labels and Markdown links (relative links recomputed for the new location).
8. **Non-greppable path construction** (cannot be rewritten safely, so reported for manual edit): `Path(__file__).parents[N]`, `os.path.join(..., "plugins", ...)`, f-strings building paths, `glob` patterns, `sys.path.insert(...)`.

**`verify` checks**: zero remaining old tokens; every rewritten path exists; relative-link resolution across all `.md` (the `checking-links` skill is the independent second check); `py_compile` on all `.py`; import smoke test of every moved module; JSON and YAML parse; `rg` for old paths in `.ts/.js/.tsx`; the non-greppable-construction report is empty or each item signed off; no symlink remains under `plugins/`.

**Tests for the tool**: fixture mini-repo with every rule class, golden diffs, idempotence check, exclusion check, and a round-trip (apply then verify).

## 7. Wave 1: questrade (9 skills -> 2 hubs)

**Status: DONE (2026-10-26)** on branch `apm-consolidation`. Evidence in `docs/plans/apm-migration/waves/wave-1/` (`summary.md`, `transition-matrix.md`, test output). Open: deploying the new hubs in place of the nine stale copies in `.agents/skills/` (Decision 5, see the transition matrix).

| Legacy skill | Hub | Mode |
|---|---|---|
| questrade-setup | `syncing-questrade-accounts` | `setup` |
| questrade-get-balances | same | `balances` |
| questrade-get-positions | same | `positions` |
| questrade-activities | same | `activities` |
| questrade-sync-portfolio | same | `sync-portfolio` |
| questrade-refresh-prices | same | `refresh-prices` |
| questrade-order-draft | `trading-with-questrade` | `order-draft` (human-approval flow) |
| questrade-deposit-funds | same | `deposit-funds` |
| norberts-gambit | same | `norberts-gambit` |

- Scripts -> `syncing-questrade-accounts/scripts/`: `questrade_sync.py`, `questrade_trades_import.py`, `questrade_price_refresh.py`; tests (3) with them.
- References: `questrade-tool-schemas.md` (8 skills) and `questrade-mcp-ai-integration.md` (setup, order-draft) are owned by `syncing-questrade-accounts`; `trading-with-questrade` links to them across hubs with a relative markdown link (same plugin). `norberts-gambit-questrade.md` -> `trading-with-questrade`.
- The root `.mcp.json` (single HTTP server `https://mcp.questrade.com/v1/brokerage/mcp`) moves into `apm.yml` under `dependencies.mcp`, so APM writes each harness's MCP config at install time. The plugin root keeps `apm.yml`, `README.md` and `docs/`. `plugin.yaml` is retired (Decision 4).
- **First fix (my earlier breakage):** three SKILL.md references still point at `plugins/questrade/skills/...`; `.agents/ownership/questrade.json` describes the old layout.
- Orphans (Decision 3): `scaffold_skill.py`, `assets/templates/SKILL.md.template` (unused; overlaps `authoring-skills`), `references/evolution-log.md` (history, kept as the hub log).
- Engine scripts: none.

## 8. Wave 2: toolkit-manager (3 skills -> 1 hub)

| Legacy skill | Hub | Mode |
|---|---|---|
| toolkit-onboarding | `managing-the-toolkit` | `onboarding` |
| run-screener | same | `run-app` |
| sqlite-admin | same | `sqlite-admin` |
| (no skill; 2 scripts) | same | `maintenance-audits` (regenerates the `docs/architecture` registers) |

- `sqlite_admin.py` is skill-owned. `db_backup.py` is engine (the backend links it as `py_services/domain_model/db_backup.py`).
- Maintenance mode owns `audit_file_dependencies.py`, `audit_sqlite_usage.py`, and also `app_smoke_test.py`, `archive_temp_json.py`, `extract_ecosystem_yaml.py` if you keep them (Decision 3).
- References: `data-architecture/` docs and SQL schemas are symlinks to `docs/architecture/`; canonical stays in `docs/`, the plugin-side links are deleted, the hub refers to the repo path. `agent-quick-reference.md` goes into the hub's `references/`.

## 9. Wave 3: tradingview (27 skills -> 3 hubs, 1 agent)

| Hub | Modes (legacy skills) |
|---|---|
| `operating-tradingview-charts` | `setup` (tv-setup + tv-onboarding, true duplicates), `change-symbol`, `change-type`, `chart-setup`, `chart-snapshot`, `draw`, `add-indicator`, `manage-indicators`, `save-indicator`, `pine-inject`, `author-pine-script`, `thesis-overlay`, `alert-list`, `alert-reconcile`, `alert-sync` |
| `trading-via-tradingview` | `place-order`, `modify-order`, `cancel-order`, `get-orders`, `portfolio-sync`, `price-refresh`, `manage-watchlists` |
| `analyzing-charts` | `ta-daily-sweep`, `ta-snapshot`, `ta-red-team`, `technical-analysis-expert` |

- **Engine (Decision 1):** `tv_client.py` (imported by 18 scripts), `tv_launch.py`, `tv_health_check.py`, `place_order.py`, `fetch_broker_data.py` (both already app-linked), `tv_account_coverage.py`.
- Skill-owned, hub A: `tv_draw`, `tv_manage_indicators`, `tv_pine_inject`, `tv_pine_manager`, `pine_linter`, `pine_source_reader`, `tv_thesis_overlay`, `tv_create_alerts`, `tv_list_alerts`, `tv_quote`; all `pinescript-indicators/` assets (9 `.pine` plus `registry.json`); references `PineScript_Agent_Skill_Rules`, `Top_TradingView_Indicators_Reference`, `pinescript_overview`, `chart-types-reference`, `playbooks/`.
- Skill-owned, hub B: `tv_get_orders`, `tv_modify_order`, `tv_cancel_order`, `tv_trades_import`, `tv_batch_quotes`, `tv_price_refresh`, `watchlist_manager`.
- Skill-owned, hub C: `ta_sweep_batch`, `ta_sweep_single`; asset `ta_thesis_template.md`.
- Agent `ta-guide.md` -> `.apm/agents/ta-guide.agent.md`, rewritten as its own short definition (SF-12) using skills by name. Its paths to `author-pine-script`, `pine-inject`, `technical-analysis-expert` are stale today (the real names carry the `tv-` prefix).
- Fix: `tv-chart-snapshot` cites a non-existent `tv_snapshot.py`; `tv-manage-watchlists` cites `manage_watchlists.py` but the real file is `watchlist_manager.py sync`.
- `audit/orders-*.jsonl` (22 runtime logs) is data: confirm the writer path, then move it out of the plugin.
- 18 tests: engine tests to `py_services` tests, the rest with their hubs; `tv_test_harness.py` goes with the engine tests.

## 10. Wave 4: portfolio-advisor (absorbs stock-valuation + etf-analysis; 25 skills -> 5 hubs, 4 agents)

| Hub | Modes (legacy skills) |
|---|---|
| `valuing-investments` | `update-analysis` (update-stock-analysis), `research-sweep` (stock-research), `forward-challenge`, `math-validation`, `fund-analysis` (etf-analysis, already converted), `stock-intake` |
| `running-portfolio-reviews` | `daily-loop`, `weekly-review`, `news-sweep`, `external-review` (adversarial-review + external-review merged, one bundler) |
| `setting-portfolio-targets` | `update-targets`, `calibrate-targets`, `rebalance`, `strategic-review`, `portfolio-health`, `thesis-review`, `set-thesis-breakers`, `pre-trade-analysis`, `ytd-return` |
| `tracking-13f-filings` | `track` (13f-tracker), `analyze` (13f-analyze) |
| `auditing-portfolio-data` | `data-quality` + `coverage` (same script, `audit_coverage.py`), `screener-integrity` |

**Engine (to `py_services`):**
- Backend-imported, stock-valuation (11): `comps_valuation`, `dcf_scenarios`, `dcf_sensitivity`, `fetch_financials`, `leverage`, `persist_research`, `price_changes`, `recalculate_forward_valuation`, `reverse_dcf`, `standardize_metrics`, `wacc` (`market_data` is already a real copy there).
- Backend-imported, portfolio-advisor (13): `apply_catalyst`, `daily_brief`, `generate_news_prompt`, `generate_portfolio_blueprint`, `generate_reports`, `generate_review_json`, `manage_watchlist`, `portfolio_action`, `recommendation`, `refresh_all`, `relabel_actions`, `update_thesis`, `ytd_return`.
- Shared by two or more hubs or imported by engine: `update_targets`, `validate_weights`, `verify_refresh`, `review_gate`, `thesis_currency`, `set_standing_decision`, `portfolio_io`, `recent_trades`, `risk_reward`, `standing_decision_check`, `generate_sub_strategy_blocks`, `update_price_levels`, `sync_portfolio_roles`, `rebaseline_targets` (also called by questrade).

**Skill-owned:**
- `valuing-investments`: `validate_projection`, `persist_valuation`, `list_strategy_pillars`, `fetch_fund_data`, `persist_etf_analysis`, `validate_etf_analysis`.
- `running-portfolio-reviews`: `run_daily`, `verify_daily_run`, `daily_receipts`, `news_sweep`, `record_news_sweep`, `weekly_review`, `bundle.py`.
- `setting-portfolio-targets`: `generate_review`, `scan_opportunities`.
- `tracking-13f-filings`: `fetch_13f`.
- `auditing-portfolio-data`: `audit_coverage`.

**Assets -> hub:**
- `valuing-investments`: `projection_template.json`, `etf_analysis_template.json`.
- `running-portfolio-reviews`: `daily_sweep`, `weekly_sweep` (used by no skill today, only an agent), `daily_report`, `weekly_report`, `thesis-challenge-prompt`.
- `setting-portfolio-targets`: `PortfolioAnalysisRecommendations.md` (5 skills, one hub), `portfolio_analysis_recommendations_template.json`, `target_portfolio_template.json`, `thesis_proposal_template.md`, `ytd_performance_report_template.json`.

**References -> hub:**
- `valuing-investments`: `ai-forward-valuation`, `valuation-method-and-discount-rate`, `valuation-benchmarks`, `analysis_prompt`, `api_reference`, `ADR-dcf-calculator`, `valuation-persistence`, `interaction_flow`, `stock_valuation_sequence.mmd`, the AI-augmented doc, the Opus-version doc, one merged acceptance-criteria file (two near-identical files exist), the stock-valuation fallback tree.
- `running-portfolio-reviews`: `daily-brief-methodology`, `news-sweep-model-assessment`, `evolution-log`.
- `setting-portfolio-targets`: `rebalance_prompt`, `strategic_review_prompt`, `fallback-tree`, `thesis-page-currency`, `recommendation-coherence`.
- `recommendation-coherence.md` (7+ skills in both old plugins) and `thesis-page-currency.md` (5 skills plus agents): owner is `setting-portfolio-targets`; other hubs use a relative markdown link (Decision 2). `ai-forward-valuation.md`: owner `valuing-investments`.

**Agents** (`portfolio-advisor-orchestrator`, `red-team-agent`, `risk-officer-agent`, `thesis-review-agent`) -> `.apm/agents/*.agent.md`; script and template paths updated to hub and engine locations; skills used by name.
**Tests**: 27 (portfolio-advisor) + 13 (stock-valuation) + 1 (etf-analysis): engine tests to `py_services` tests, hub-owned tests with their hubs.
**Other**: `investment_thesis.md` symlinks (4 skills) become references to the canonical path under `investment_screener/backend/data/theses/`. `README.md` and `CONNECTORS.md` are merged. `plugin.json` files per Decision 4.

## 11. Orphans and duplicates (proposed disposition; nothing deleted without your approval)

| Item | Finding | Proposed |
|---|---|---|
| `defininitive_professional_investment_framework.md` | typo duplicate of `definitive_...` (both 339 lines) | delete the typo copy |
| `triage-history.json` (portfolio-advisor references) | data, used by no skill | move to a data folder |
| `test_portfolio_action.py` in `scripts/` | a test in the wrong place | move to tests |
| `consolidate_research.py`, `research_parity_report.py` | used by no skill, have tests | decide: mode or archive |
| `rebase_equity_valuations.py` | used by no skill, has tests | `valuing-investments` mode, or archive |
| `forward-valuation-reviews/` (BE, MU) | review data in references | move to data/evals fixtures |
| `scripts/cache/*.json` | gitignored runtime cache | stays out of the package |
| stock-valuation ADR docs | docs used by no skill | leave in `docs/architecture/ADRs/` |
| `tradingview/audit/*.jsonl` | runtime logs | move out of the plugin |
| questrade scaffolder and template | unused | delete or archive |
| `app_smoke_test.py`, `archive_temp_json.py`, `extract_ecosystem_yaml.py` | used by no skill | keep in `maintenance-audits` or archive |

## 12. Existing breakage this plan must repair

- questrade: 3 stale SKILL.md paths (my earlier move); `.agents/ownership/questrade.json` and `etf-analysis.json` describe the old layout.
- `plugins/etf-analysis/apm.yml` and `plugins/questrade/apm.yml` (created by me from pipeline staging) lack `includes: auto`, `metadata.packaging_mode: full` and `metadata.governance_lane`; there is no README, `docs/governance.md`, `docs/attribution.md`, `docs/package-lifecycle.md` or `.gitignore`. The earlier validator pass did not check structure (rule 13), and the "dual manifest" condition (`plugin.json` plus `apm.yml`) is present.
- `.claude-plugin/marketplace.json` still lists `stock-valuation` and `etf-analysis` as separate plugins, and its entries for etf-analysis and questrade no longer expose skills to Claude's plugin loader (skills moved under `.apm/`); `audit_marketplace_sources.py` reports "valid" because it only checks that the directories exist.
- `symlinks.json` was edited by me: one etf-analysis entry removed, plus a trailing-newline change at the end of the file (checked with `git diff`; no other reformatting).
- `docs/architecture/json-discovery-audit.{md,json}` and `allowed-json-register.{md,json}` list old paths (~1,500 lines); regenerate after each wave.
- 71 `symlinks.json` entries still mention stock-valuation paths.
- tradingview: `ta-guide.md` cites four skill paths that do not exist; two scripts named in SKILL.md files do not exist.
- portfolio-advisor: `adversarial-review` and `external-review` name a bundler path that does not exist; `ytd-return` names `cash_flows.json`, which does not exist.

## 13. Risks

- Renaming skills breaks anything that invokes old skill names (portfolio-advisor skills chain to `/update-stock-analysis`; the agents; evals; AGENTS.md). Mitigation: slash commands kept as modes, the transition matrix, the rewrite tool.
- Moving engine scripts changes import paths for the backend and ~15 backend tests. Mitigation: full backend suite after each wave that moves engine scripts, compared with the Wave 0 baseline.
- Hubs with 9 to 15 modes need disciplined mode files to stay under 100 lines in `SKILL.md`; routing precision is checked with the merged evals.
- The rewrite tool can mangle prose. Mitigation: ambiguous matches are reported, never guessed; plan/dry-run diff is reviewed before `apply`; each wave writes a rollback patch.
- Two installers for one plugin produce duplicate skills (Decision 5).

## 14. Order

Wave 0 (baseline, ledger, tool) -> Wave 1 questrade -> Wave 2 toolkit-manager -> Wave 3 tradingview -> Wave 4 portfolio-advisor (largest, last). Waves 1 and 2 do not depend on Decision 1 beyond `db_backup`.
