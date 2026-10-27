# Mode: setup

This mode combines `tv-setup` and `tv-onboarding`.

## Part: tv-setup (`/tv-setup`)

Diagnoses and guides setup of TradingView CDP dependency and debugging port. Trigger on /tv-setup or 'diagnose tradingview connection'.
Allowed tools: Bash, Read, Write.

Diagnoses and guides setup of TradingView CDP dependency and debugging port.


## Constraints

- Port 9222 check: Verifies HTTP connectivity to `http://localhost:9222/json/version`.
- Node CDP dependency: Ensures `tradingview-cdp/` has node modules installed.
- Read-only diagnostic: Does not alter system network configuration.

## Quick start

```bash
python3 investment_screener/backend/py_services/tv_health_check.py
```

## Workflow

1. Check if Node.js runtime and `tradingview-cdp/` packages exist.
2. Test HTTP response on `http://localhost:9222`.
3. Provide actionable remediation steps if connection fails:
   - Launch TradingView with `--remote-debugging-port=9222`.
   - Run `npm ci` in `tradingview-cdp/`.
4. Report diagnostic status.

## Verification

- Confirm `tv_health_check.py` returns OK.
- Validate routing cases against `evals/evals.json`.

## Part: tv-onboarding (`/tv-onboarding`)

Setup and diagnostic guide for TradingView Desktop and remote debugging port 9222. Trigger on /tv-onboarding or 'connect tradingview'.
Allowed tools: Bash, Read, Write.

Setup and diagnostic guide for TradingView Desktop and remote debugging port 9222.


## Constraints

- Port 9222 requirement: TradingView Desktop must launch with `--remote-debugging-port=9222`.
- Broker login prerequisite: Broker panel must be connected to enable portfolio sync.
- Read-only diagnostic: Health checks do not mutate user settings.

## Quick start

```bash
python3 investment_screener/backend/py_services/tv_health_check.py
```

## Workflow

1. Check if TradingView Desktop is installed.
2. Launch TradingView with debugging enabled:
   `open -a 'TradingView' --args --remote-debugging-port=9222`
3. Run automated health check:
   `python3 investment_screener/backend/py_services/tv_health_check.py`
4. Report connectivity status across chart engine and broker panel.

## Verification

- Confirm `tv_health_check.py` outputs 'OK (port 9222 open)'.
- Validate routing cases against `evals/evals.json`.
