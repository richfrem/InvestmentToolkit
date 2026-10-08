"""Purpose: contract tests for which broker connections may be used to refresh trades.

Layer: Tests. No network; reads a temporary .env file.
Key Functions: default, opt-in, precedence and truthiness cases; real CLI subprocess.
Key Input Dependencies: broker_sources.py.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "investment_screener/backend/py_services"))
from broker_sources import questrade_enabled, trade_sources  # noqa: E402

SCRIPT = ROOT / "investment_screener/backend/py_services/broker_sources.py"


def env_file(tmp_path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text)
    return path


def test_tradingview_only_is_the_default(tmp_path):
    """No setting, a missing file or an unrelated file all mean TradingView only."""
    assert trade_sources(tmp_path / "missing.env", environ={}) == {"default": "tradingview", "available": ["tradingview"], "questrade": False}
    assert questrade_enabled(env_file(tmp_path, "BACKEND_PORT=3001\n# QUESTRADE_ENABLED=true\n"), environ={}) is False


@pytest.mark.parametrize("value,expected", [("true", True), ("TRUE", True), ("1", True), ("yes", True), ('"true"', True),
                                            ("false", False), ("0", False), ("", False), ("maybe", False)])
def test_only_clear_yes_values_enable_questrade(tmp_path, value, expected):
    assert questrade_enabled(env_file(tmp_path, f"QUESTRADE_ENABLED={value}\n"), environ={}) is expected


def test_enabling_questrade_adds_it_but_tradingview_stays_the_default(tmp_path):
    sources = trade_sources(env_file(tmp_path, "QUESTRADE_ENABLED=true  # set by questrade-setup\n"), environ={})
    assert sources == {"default": "tradingview", "available": ["tradingview", "questrade"], "questrade": True}


def test_process_environment_overrides_the_file(tmp_path):
    path = env_file(tmp_path, "QUESTRADE_ENABLED=true\n")
    assert questrade_enabled(path, environ={"QUESTRADE_ENABLED": "false"}) is False
    assert questrade_enabled(env_file(tmp_path, "QUESTRADE_ENABLED=false\n"), environ={"QUESTRADE_ENABLED": "1"}) is True


def test_cli_prints_the_sources_as_json(tmp_path):
    result = subprocess.run([sys.executable, str(SCRIPT), "--json", "--env-file", str(env_file(tmp_path, "QUESTRADE_ENABLED=true\n"))],
                            capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["available"] == ["tradingview", "questrade"]
