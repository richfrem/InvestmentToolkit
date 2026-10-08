"""
broker_sources.py — which broker connections may be used to refresh trades and positions.

Purpose:
    One answer to "may this install use Questrade, or TradingView only?". TradingView
    is the baseline every user has; Questrade is an optional augment that a user
    turns on during setup. Skills, scripts and the web app all read this instead of
    guessing from whether a Questrade session happens to be connected.
Layer:
    Configuration (reads the repo .env and the process environment; no network).
Usage:
    python3 investment_screener/backend/py_services/broker_sources.py --json
    from broker_sources import trade_sources, questrade_enabled
Key Functions:
    questrade_enabled(env_path, environ)   True only when QUESTRADE_ENABLED is a clear yes
    trade_sources(env_path, environ)       {"default", "available", "questrade"}
Key Input Dependencies:
    .env at the repository root (QUESTRADE_ENABLED); process environment overrides it.

Setting:
    QUESTRADE_ENABLED=false   (default) refresh from TradingView only
    QUESTRADE_ENABLED=true    Questrade may also be used; TradingView stays the default
                              and the owner is asked which to use for a refresh
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Mapping

SETTING = "QUESTRADE_ENABLED"
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
_YES = {"1", "true", "yes", "on"}


def _file_value(env_path: Path) -> str | None:
    """Value of the setting in a KEY=VALUE env file; comments and other keys are ignored."""
    try:
        lines = env_path.read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        key, separator, value = line.strip().partition("=")
        if separator and key.strip() == SETTING:
            return value.split("#", 1)[0].strip().strip("\"'")
    return None


def questrade_enabled(env_path: Path | str | None = None, environ: Mapping[str, str] | None = None) -> bool:
    """True only when the setting is a clear yes; the process environment wins over the file."""
    env = os.environ if environ is None else environ
    value = env.get(SETTING)
    if value is None:
        value = _file_value(Path(env_path) if env_path else ENV_PATH)
    return str(value or "").strip().strip("\"'").lower() in _YES


def trade_sources(env_path: Path | str | None = None, environ: Mapping[str, str] | None = None) -> dict:
    """Sources allowed for refreshing trades: TradingView always, Questrade only when enabled."""
    enabled = questrade_enabled(env_path, environ)
    return {"default": "tradingview", "available": ["tradingview"] + (["questrade"] if enabled else []),
            "questrade": enabled}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Show which broker connections may be used for refreshes")
    parser.add_argument("--json", action="store_true", help="Print as JSON")
    parser.add_argument("--env-file", default=None, help="Env file to read (default: repository .env)")
    arguments = parser.parse_args()
    sources = trade_sources(arguments.env_file)
    print(json.dumps(sources) if arguments.json else
          f"Default: {sources['default']}. Available: {', '.join(sources['available'])}.")
