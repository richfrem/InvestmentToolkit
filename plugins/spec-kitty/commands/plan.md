---
description: Generate implementation plan from specification
---

# Plan Implementation

Create the `plan.md` artifact — the **How** of a feature.

## Usage
```bash
spec-kitty plan
```

## Verification
```bash
python3 plugins/spec-kitty/scripts/verify_workflow_state.py --feature <SLUG> --phase plan
```

**STOP**: Do NOT proceed to Tasks until verification passes.
