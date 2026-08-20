# Contributing to InvestmentToolkit

Thank you for your interest in contributing to **InvestmentToolkit**! We welcome contributions from developers, quantitative analysts, and retail investors.

To maintain institutional code quality and ensure strict compliance with broker and platform terms of service, please review the following guidelines before submitting issues or pull requests.

---

## 🏛️ Guiding Principles

1. **100% Human-in-the-Loop (HITL) Decision Support**:
   - In strict compliance with TradingView's Terms of Use, AI agents and scripts **never** execute, modify, or cancel live orders autonomously.
   - All trade suggestions must remain strictly advisory, staged on-screen for explicit human review and confirmation.
2. **Test-Driven Development & Math Parity**:
   - Python calculations (`py_services/`) and Frontend mirrors (`valuationMath.ts`) must maintain strict mathematical parity within $0.01 tolerance (verified via `python3 run_tests.py`).
   - No financial calculation may be performed inline—always extract to versioned Python services.
3. **Strict Privacy by Design**:
   - Private broker files (`domain_model.sqlite`, `intelligence.sqlite`, `trade-log.json`, `cash_flows.json`, `.env`) are gitignored and must never be committed.
   - Always use **Demo / Privacy Mode** (`formatPrivateMoney`) for any user-facing screenshots or demo assets.

---

## 🤖 Contributing with AI Agents & Agent Skills

This repository uses an **Agentic AI Operating System** with specialized skills to automate issue triage, taxonomy enforcement, and PR lifecycle management:

### 1. Logging Issues & Execution Friction (`github-issue-agent`)
If you encounter a repeatable bug, unexpected friction, or architectural issue while running the toolkit:
- You can trigger the **`github-issue-agent`** skill via your AI assistant (Claude Code, Gemini CLI, or Copilot).
- It performs **secret redaction**, validates issue taxonomy (`type:*`, `tier:*`, `area:*`), and ensures a complete evidence section before opening a GitHub Issue.

### 2. Escalating Tasks to Issues (`github-issue-backlog-agent`)
- To promote local task scratchpad items or feature blueprints into tracked GitHub Issues, use the **`github-issue-backlog-agent`** skill.

### 3. Priority Triage & Labeling (`github-issue-prioritizer`)
- Automated issue ranking (P0–P3) is computed using the **`github-issue-prioritizer`** skill based on friction tier, occurrence frequency, and blocking severity.

---

## 🛠️ Development Setup & Workflow

### 1. Prerequisites
- **Node.js**: v20+ and npm
- **Python**: v3.11+
- **TradingView Desktop** *(Optional)*: Launched with `--remote-debugging-port=9222` for live CDP DOM automation.

### 2. Fork & Clone
```bash
git clone https://github.com/YOUR_USERNAME/InvestmentToolkit.git
cd InvestmentToolkit
```

### 3. Launch the Application
```bash
python3 run_investment_toolkit.py
```
This unified orchestrator creates a virtual environment, installs dependencies, builds the backend, and launches both frontend (`localhost:5173`) and backend (`localhost:3001`).

### 4. Running the Test Suite
Before opening a Pull Request, verify that all compile, syntax, and bridge gates pass:
```bash
python3 run_tests.py
```

---

## 🌿 Git Worktree & Pull Request Workflow

We use a worktree-first workflow for clean branch isolation:

1. **Create a Feature Branch**:
   ```bash
   git checkout -b feat/my-new-feature
   ```
2. **Commit Changes**: Follow conventional commits (`feat:`, `fix:`, `docs:`, `chore:`).
3. **Run Pre-Push Verification**:
   - Ensure `npm run build -w frontend` and `npm run build -w backend` succeed.
   - Ensure `python3 run_tests.py` passes all T0/T0.5 gates.
4. **Open a Pull Request**: Provide a clear summary of changes, motivation, and test evidence.

---

## ⚖️ Financial & Legal Notice

By contributing to InvestmentToolkit, you agree that your contributions are licensed under the [MIT License](LICENSE) and adhere to the project's non-autonomous, human-in-the-loop architecture.
