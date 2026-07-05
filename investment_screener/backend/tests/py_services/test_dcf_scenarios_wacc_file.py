import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from dcf_scenarios import _resolve_discount_rate  # noqa: E402


def test_resolve_discount_rate_uses_explicit_override_when_given(tmp_path):
    wacc_file = tmp_path / "wacc.json"
    wacc_file.write_text(json.dumps({"wacc": 0.12}))
    assert _resolve_discount_rate(0.08, str(wacc_file)) == 0.08


def test_resolve_discount_rate_uses_wacc_file_when_no_explicit_override(tmp_path):
    wacc_file = tmp_path / "wacc.json"
    wacc_file.write_text(json.dumps({"wacc": 0.12}))
    assert _resolve_discount_rate(None, str(wacc_file)) == 0.12


def test_resolve_discount_rate_defaults_to_ten_percent_when_neither_given():
    assert _resolve_discount_rate(None, None) == 0.10
