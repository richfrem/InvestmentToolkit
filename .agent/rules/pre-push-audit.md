---
description: Run compliance, coding conventions, and structural audits on all modified plugins and skills, and resolve errors before pushing to GitHub.
globs:
  - "plugins/**/*"
---

# Pre-Push Audit & Verification Rule

Before pushing any changes to GitHub or concluding updates to plugins or skills, you MUST run standard compliance, coding conventions, and structural audits on all affected plugins, and resolve any flagged errors or symlink issues.

## Verification Commands

Run the following checks from the repository root:

1. **Workspace Coding Conventions Audit**:
   Ensure all file headers, Purpose, Key Input Dependencies, and function docstrings match codebase policies:
   ```bash
   python3 plugins/dev-utils/scripts/workspace_conventions_auditor.py
   ```

2. **Compliance Audit**:
   ```bash
   python plugins/agent-scaffolders/scripts/audit.py --path plugins/<plugin-name>
   ```

3. **Structural Audit**:
   Verify symlink and resource compliance:
   ```bash
   python plugins/agent-scaffolders/scripts/audit_plugin_structure.py plugins/<plugin-name>
   ```

4. **Cross-Platform Symlink Check**:
   ```bash
   python .agents/skills/symlink-manager/scripts/symlink_manager.py diagnose
   ```

5. **Portfolio Cash & Valuation Invariant Check**:
   Verify that portfolio total calculations always include uninvested cash (`CASH_USD` / `PSU-U.TO`) alongside equities:
   ```bash
   python3 investment_screener/backend/py_services/verify_portfolio_total.py
   ```

## Resolution Action

If any errors, missing references, or duplicate files are reported:
- Resolve them immediately before proposing a commit or push.
- Move duplicates to the plugin root `references/` folder and symlink them back to the individual skills using `symlink_manager.py`.
- If portfolio totals show a discrepancy vs. broker totals, verify that cash balances across all accounts (TFSA, RRSP, CASH) are included in the total equity rollup.
