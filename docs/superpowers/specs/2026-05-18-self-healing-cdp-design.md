# Self-Healing & Self-Evolving CDP Agents — Design Spec

**Date:** 2026-05-18
**Task:** 0008
**Branch:** feature/self-healing-cdp-evolution
**Status:** APPROVED

---

## 1. Problem Statement

TradingView ships DOM updates 2–4 times per year. When a selector changes, every
CDP-dependent skill fails with a cryptic `null` error until a developer manually
patches the selector. This is purely reactive and requires human intervention for
what is essentially a find-and-replace operation.

Beyond selector regressions, agents regularly hit capability boundaries (no function
exists for an action) or code bugs (wrong argument shape). Currently all three failure
types surface as the same opaque subprocess error, leading agents to retry blindly
or escalate unnecessarily.

The goal is to give agents a formal, bounded protocol for handling all three
failure types autonomously — with appropriate evidence collection, permission gates,
and mandatory reference file updates so each fix makes future agents smarter.

---

## 2. Architecture

### 2.1 Two-Layer Design

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — Generic Skill (portable, multi-repo)             │
│  agent-agentic-os / skills / self-evolution / SKILL.md      │
│                                                             │
│  • Gap / Failure / Regression taxonomy                      │
│  • Evidence collection protocol per tier                    │
│  • Permission gates (add: auto | modify: auto+log |         │
│    delete: confirm)                                         │
│  • Verify → Update Map → Log loop                           │
│  • Escalation template (after 3 failed attempts)            │
└─────────────────────────────────────────────────────────────┘
                          │ reads
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — Repo Profile (repo-specific, InvestmentToolkit)  │
│  plugins/tradingview/references/self-evolution-profile.md   │
│                                                             │
│  • Allowed edit directories                                 │
│    - tradingview-cdp/core/                                  │
│    - plugins/tradingview/scripts/                           │
│    - plugins/tradingview/references/                        │
│  • Error pattern → tier classification table                │
│  • Domain playbook location                                 │
│  • Evolution log path                                       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Failure Tier Taxonomy

| Tier | Name | Definition | Evidence required | Patch approach |
|------|------|-----------|-------------------|----------------|
| 1 | **Gap** | Capability doesn't exist. No prior success to compare against. | None | Build the missing function/helper |
| 2 | **Failure** | Code exists but is broken (logic bug, wrong args, wrong shape). | Error + stack trace | Diagnose and patch the code |
| 3 | **Regression** | Previously worked; external system (TV DOM) changed it. | Screenshot + DOM snapshot + git log | Fallback selector + patch; document change in Map |

**Ambiguity rule:** When Failure vs Regression is unclear, default to Regression and
collect evidence. The cost of a screenshot is lower than patching the wrong layer.

### 2.3 Permission Gates

| Edit type | Gate |
|-----------|------|
| Add new function / export / selector | Auto-approved |
| Modify existing function logic | Auto-approved; append `git diff` to evolution log |
| Rename or move a file | Confirm with user |
| Delete any file or function | Hard stop — always confirm |
| Edit outside allowed directories | Hard stop — always escalate |

### 2.4 "The Map, Not the Diary" Reference System

Every fix must update at least one persistent reference artifact:

- **`evolution-log.md`** — append-only table row: date, tier, what failed, what was
  patched, edit type, outcome.
- **Domain playbooks** (`references/playbooks/<topic>-playbook.md`) — created or
  updated when a workflow has non-obvious mechanics, timing quirks, or a selector
  changed. Format: Status, Last verified, Relevant files, The Mechanics, Known Failure
  Modes, Change History.
- **Inline selector comments** — modified files get a comment noting the old selector
  and the regression date: `// updated 2026-05-18: old=[...] new=[...] TV regression`

---

## 3. Components Delivered

### 3.1 New — `self-evolution` Skill (agent-agentic-os)

**File:** `agent-plugins-skills/plugins/agent-agentic-os/skills/self-evolution/SKILL.md`

7-phase workflow:
- Phase 0: Read repo profile (bootstrap if missing)
- Phase 1: Classify tier (Gap / Failure / Regression)
- Phase 2: Collect tier-appropriate evidence
- Phase 3: Plan the repair (3–5 bullet points before any edit)
- Phase 4: Execute with permission gates
- Phase 5: Verify (max 3 attempts, then escalate)
- Phase 6: Update The Map (playbook + inline comments)
- Phase 7: Log the evolution

### 3.2 New — Repo Profile (InvestmentToolkit)

**File:** `plugins/tradingview/references/self-evolution-profile.md`

Defines allowed dirs, 10-entry error pattern classification table, playbook location,
evolution log path, and key files for context.

### 3.3 New — Domain Playbooks Infrastructure

**Files:**
- `plugins/tradingview/references/playbooks/README.md` — naming convention, index
- `plugins/tradingview/references/evolution-log.md` — append-only fix log

### 3.4 Updated — Existing Skills Wired to Self-Evolution

The following skills have a "Self-Evolution" section added that instructs agents
to invoke the skill on failure:

- `plugins/tradingview/skills/author-pine-script/SKILL.md` (Phase 3 already had
  informal self-heal — replaced with formal `self-evolution` reference)
- `plugins/tradingview/skills/technical-analysis-expert/SKILL.md`
- `plugins/tradingview/skills/ta-guide.md` (agent — gets a Rules entry)

---

## 4. What Is NOT in Scope

- Automatic git commits for code patches (user reviews and commits code changes)
- Self-evolution for non-tradingview plugins (each plugin needs its own profile)
- Modifying `investment_screener/` backend or frontend code
- AI model selection or prompt tuning (this is purely a process/permission spec)

---

## 5. Success Criteria

1. An agent encountering a stale TV selector can classify it as Regression, collect
   a DOM snapshot, patch a fallback selector in `tradingview-cdp/core/`, verify it
   works, and update the relevant playbook — without any human intervention.
2. An agent encountering a missing capability can build the helper, add it to
   `tradingview-cdp/core/`, verify it, and create a domain playbook — without
   human intervention.
3. Every autonomous edit is visible in `evolution-log.md` within 60 seconds of
   the fix being verified.
4. No edit ever touches a file outside the allowed directories without explicit
   user confirmation.

---

## 6. Related

- ADR-024: Thin Skill + Thick Engine (`tradingview-cdp/` as shared runtime)
- CLAUDE.md Pitfalls section: 16 known CDP failure patterns
- `tv_test_harness.py` Section 0.5: DOM selector smoke tests (preventive layer)
- Task 0003: Temp file migration (in progress)
