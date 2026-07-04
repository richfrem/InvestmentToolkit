import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
FIXTURES = REPO_ROOT / "investment_screener/backend/tests/fixtures"
sys.path.insert(0, str(SCRIPT_DIR))

from edgar_facts import get_company_facts  # noqa: E402


def _fixture():
    return json.loads((FIXTURES / "edgar_companyfacts_aapl.json").read_text())


def test_get_company_facts_extracts_revenue_with_filing_date():
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _fixture()
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000320193")

    assert "revenue" in result
    assert result["revenue"]["value"] > 0
    assert "asOf" in result["revenue"]


def test_get_company_facts_sends_required_user_agent_header():
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _fixture()
    with patch("edgar_facts.requests.get", return_value=fake_response) as mock_get:
        get_company_facts("0000320193")

    _, kwargs = mock_get.call_args
    assert "InvestmentToolkit" in kwargs["headers"]["User-Agent"]


def test_get_company_facts_returns_empty_dict_on_404():
    fake_response = MagicMock()
    fake_response.status_code = 404
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000000000")

    assert result == {}
