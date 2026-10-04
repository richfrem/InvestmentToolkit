---
name: run-screener
plugin: toolkit-manager
description: Launch the Investment Screener suite (backend + frontend). Trigger when user says "run the screener", "start the app", "launch investment toolkit", "start servers", or "run investment screener".
allowed-tools: Bash, Read, Write
---

# Run Screener

Orchestrates startup of the backend and frontend services via the unified python runner.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- **Port readiness barrier**: Never provide URLs or declare success until both Backend (port 3001) and Frontend (port 5173) are confirmed listening.
- **Port conflicts**: If ports 3001 or 5173 are occupied, identify active process owners before restarting; never create orphan processes.
- **Workspace execution**: Always execute `run_investment_toolkit.py` from repository root.

## Quick start

Launch the entire suite from repository root:

```bash
python3 run_investment_toolkit.py
```

## Workflow

1. **Invoke Runner**:
   Execute `python3 run_investment_toolkit.py` to activate venv, compile backend, run SQLite migrations, and launch servers.
2. **Monitor Startup Stream**:
   Observe dependency installations and build steps. Withhold final URLs while builds are in flight.
3. **Confirm Service Liveness**:
   Wait for `✅ Services Running!` confirmation that Backend (3001) and Frontend (5173) are actively accepting connections.
4. **Present Operational Summary**:
   Provide local links to the user:
   - Frontend Dashboard: `http://localhost:5173`
   - Express Backend API: `http://localhost:3001`
   - Inform user that `Ctrl+C` terminates the processes.

## Verification

- Confirm HTTP 200 response on `http://localhost:5173` and `http://localhost:3001/api/health`.
- Test routing evaluations against `evals/evals.json`.
