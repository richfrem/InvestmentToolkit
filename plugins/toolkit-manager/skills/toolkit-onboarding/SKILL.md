---
name: toolkit-onboarding
plugin: toolkit-manager
description: >
  Master onboarding coordinator for InvestmentToolkit. Orients new users,
  verifies dependencies, and initializes private configuration files.
  Trigger on /toolkit-onboarding or "help me set up the toolkit".
allowed-tools: Bash, Read, Write
---

# InvestmentToolkit Onboarding Guide

**Trigger:** `/toolkit-onboarding` or `help me set up the toolkit`

---

## Purpose
Orients new users, verifies runtime dependencies (Node.js 18+, Python 3.11+), and ensures private data files are initialized.

---

## Step 1 — Dependency Check
Run the version check in your terminal:
```bash
node --version       # Required: 18.0+
python3 --version    # Required: 3.11+
```

---

## Step 2 — Initialize Private Data Files
If missing from `investment_screener/backend/data/`, copy the example templates:
```bash
python3 -c "
import os, shutil
base = 'investment_screener/backend/data'
for f in ['cash_flows.json', 'portfolio-config.json']:
    src = os.path.join(base, f + '.example')
    dst = os.path.join(base, f)
    if not os.path.exists(dst) and os.path.exists(src):
        shutil.copy(src, dst)
        print(f'Initialized: {f}')
"
```

---

## Step 3 — Launch the Application
Start the unified full-stack application:
```bash
python3 run_investment_toolkit.py
```
This launches:
- **Backend API**: Port `3001`
- **Frontend Dashboard**: Port `5173`
- **TradingView CDP**: Port `9222`
