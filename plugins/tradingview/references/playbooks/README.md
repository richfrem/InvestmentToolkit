# TradingView Domain Playbooks

Each file here documents a specific TradingView UI workflow or known quirk — the exact
selectors, timing constants, and recovery paths that empirical testing confirmed work.

Agents read the relevant playbook **before** attempting the covered operation. If the
playbook says a selector works, that was verified on a real TV session. If the playbook
has a Known Failure Mode entry, check it before debugging from scratch.

## Index

*(Populated automatically by the `self-evolution` skill as playbooks are created.)*

## Playbook Naming Convention

`<domain>-<action>-playbook.md`

Examples:
- `pine-editor-inject-playbook.md`
- `indicators-dialog-source-read-playbook.md`
- `broker-panel-order-execution-playbook.md`
- `data-window-read-playbook.md`

## When to Create a New Playbook

Create a playbook when:
- A workflow required non-obvious timing, multi-step state management, or fallback logic
- A DOM selector changed and you discovered the stable replacement
- You found a TV behaviour that would surprise a future agent

Do not create a playbook for:
- Simple single-step operations already documented in CLAUDE.md
- Operations fully covered by existing `tradingview-cdp/core/` function docstrings
