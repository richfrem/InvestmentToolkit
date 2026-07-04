import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
FIXTURES = REPO_ROOT / "investment_screener/backend/tests/fixtures"
sys.path.insert(0, str(SCRIPT_DIR))

from edgar_facts import get_company_facts, _throttled_get  # noqa: E402


def _fixture():
    return json.loads((FIXTURES / "edgar_companyfacts_aapl.json").read_text())


def test_get_company_facts_extracts_revenue_with_filing_date(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _fixture()
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000320193")

    assert "revenue" in result
    assert result["revenue"]["value"] > 0
    assert "asOf" in result["revenue"]


def test_get_company_facts_sends_required_user_agent_header(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _fixture()
    with patch("edgar_facts.requests.get", return_value=fake_response) as mock_get:
        get_company_facts("0000320193")

    _, kwargs = mock_get.call_args
    assert "InvestmentToolkit" in kwargs["headers"]["User-Agent"]


def test_get_company_facts_returns_empty_dict_on_404(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_response = MagicMock()
    fake_response.status_code = 404
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000000000")

    assert result == {}


def test_get_company_facts_skips_malformed_val_field(tmp_path, monkeypatch):
    """Test that malformed val fields (missing or non-numeric) are skipped, not crashed."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fixture = _fixture()

    # Corrupt NetIncomeLoss to have a missing 'val' field in the latest record
    fixture["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"][0].pop("val", None)

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = fixture
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000320193")

    # Revenues should still be present and correct (good data unaffected)
    assert "revenue" in result
    assert result["revenue"]["value"] > 0
    assert "asOf" in result["revenue"]

    # NetIncomeLoss should be absent (skipped due to missing val)
    assert "netIncome" not in result


def test_get_company_facts_skips_non_numeric_val_field(tmp_path, monkeypatch):
    """Test that non-numeric val fields are skipped gracefully."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fixture = _fixture()

    # Corrupt OperatingIncomeLoss to have a non-numeric 'val'
    fixture["facts"]["us-gaap"]["OperatingIncomeLoss"]["units"]["USD"][0]["val"] = "not_a_number"

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = fixture
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000320193")

    # Revenues and NetIncome should still be present
    assert "revenue" in result
    assert "netIncome" in result

    # OperatingIncomeLoss should be absent (skipped due to non-numeric val)
    assert "operatingIncome" not in result


# --- Finding 1 Part A: asOf decoupled from reported period (annual value, latest filing date) ---


def test_get_company_facts_asof_reflects_latest_10q_filing_not_10k(tmp_path, monkeypatch):
    """asOf should reflect the most recent filing of either form (10-K or 10-Q),
    while the reported value still comes from the latest 10-K (annual figure) —
    a company actively filing 10-Qs between annual reports should show a fresh
    asOf even though the number itself is last year's annual total (this is
    what makes check_staleness() correctly read 'not stale' for an actively
    reporting filer)."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fixture = _fixture()
    revenues_usd = fixture["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
    ten_k_filed = revenues_usd[0]["filed"]
    # Add a 10-Q filed after the 10-K, same tag, different (quarterly) val.
    revenues_usd.append({
        "end": "2025-12-27",
        "val": 95000000000,
        "fy": 2026,
        "fp": "Q1",
        "form": "10-Q",
        "filed": "2026-01-30",
    })

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = fixture
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000320193")

    assert result["revenue"]["asOf"] == "2026-01-30"
    assert result["revenue"]["asOf"] != ten_k_filed
    # value still comes from the 10-K (annual figure), not the 10-Q quarterly figure
    assert result["revenue"]["value"] == 391035000000.0


def test_get_company_facts_asof_ignores_older_10q_than_10k(tmp_path, monkeypatch):
    """A 10-Q filed BEFORE the latest 10-K must not override the 10-K's own
    filed date — asOf is always the MOST RECENT filing among 10-K/10-Q."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fixture = _fixture()
    revenues_usd = fixture["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
    ten_k_filed = revenues_usd[0]["filed"]
    revenues_usd.append({
        "end": "2025-06-28",
        "val": 90000000000,
        "fy": 2025,
        "fp": "Q3",
        "form": "10-Q",
        "filed": "2025-08-01",  # earlier than the 10-K's 2025-11-01
    })

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = fixture
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000320193")

    assert result["revenue"]["asOf"] == ten_k_filed
    assert result["revenue"]["value"] == 391035000000.0


# --- Finding 2: revenue tag fallback ---


def test_get_company_facts_falls_back_to_alternate_revenue_tag_when_revenues_tag_absent(
    tmp_path, monkeypatch
):
    """Some issuers (real recent Apple filings included) report top-line
    revenue under RevenueFromContractWithCustomerExcludingAssessedTax instead
    of Revenues. When the Revenues tag is entirely absent, get_company_facts()
    must still extract revenue via the fallback tag rather than silently
    omitting it."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fixture = _fixture()
    revenues_usd = fixture["facts"]["us-gaap"].pop("Revenues")
    fixture["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"] = revenues_usd

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = fixture
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000320193")

    assert "revenue" in result
    assert result["revenue"]["value"] == 391035000000.0


def test_get_company_facts_prefers_revenues_tag_when_both_present(tmp_path, monkeypatch):
    """When both tags are present, the primary 'Revenues' tag wins over the
    fallback tag — fallback is only for when the primary is absent/unusable."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fixture = _fixture()
    fixture["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"] = {
        "units": {
            "USD": [
                {
                    "end": "2025-09-27",
                    "val": 1,  # deliberately different/wrong so we can prove it's ignored
                    "fy": 2025,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2025-11-01",
                }
            ]
        }
    }

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = fixture
    with patch("edgar_facts.requests.get", return_value=fake_response):
        result = get_company_facts("0000320193")

    assert result["revenue"]["value"] == 391035000000.0


# --- Finding 3 Part A: caching wired into cache.py's "edgar" data class ---


def test_get_company_facts_second_call_served_from_cache_no_network(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _fixture()
    with patch("edgar_facts.requests.get", return_value=fake_response) as mock_get:
        first = get_company_facts("0000320193")
        second = get_company_facts("0000320193")

    assert mock_get.call_count == 1
    assert first == second
    assert second["revenue"]["value"] > 0


def test_get_company_facts_different_ciks_each_hit_network(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _fixture()
    with patch("edgar_facts.requests.get", return_value=fake_response) as mock_get:
        get_company_facts("0000320193")
        get_company_facts("0000789019")  # different CIK — must not be a cache hit

    assert mock_get.call_count == 2


# --- Finding 3 Part B: client-side throttle (defense-in-depth) ---


def test_throttled_get_sleeps_when_calls_are_too_close_together(monkeypatch):
    monkeypatch.setattr("edgar_facts._last_request_time", 100.0)
    monkeypatch.setattr("edgar_facts.time.monotonic", lambda: 100.05)
    fake_response = MagicMock(status_code=200)
    with patch("edgar_facts.requests.get", return_value=fake_response), \
         patch("edgar_facts.time.sleep") as mock_sleep:
        _throttled_get("https://example.com")

    mock_sleep.assert_called_once()
    slept_for = mock_sleep.call_args[0][0]
    assert abs(slept_for - 0.10) < 1e-9


def test_throttled_get_does_not_sleep_when_enough_time_has_elapsed(monkeypatch):
    monkeypatch.setattr("edgar_facts._last_request_time", 100.0)
    monkeypatch.setattr("edgar_facts.time.monotonic", lambda: 100.5)
    fake_response = MagicMock(status_code=200)
    with patch("edgar_facts.requests.get", return_value=fake_response), \
         patch("edgar_facts.time.sleep") as mock_sleep:
        _throttled_get("https://example.com")

    mock_sleep.assert_not_called()


def test_throttled_get_not_invoked_on_cache_hit(tmp_path, monkeypatch):
    """Only actual network calls are throttled — a cache hit must never sleep."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _fixture()
    with patch("edgar_facts.requests.get", return_value=fake_response):
        get_company_facts("0000320193")

    with patch("edgar_facts._throttled_get") as mock_throttled_get:
        get_company_facts("0000320193")

    mock_throttled_get.assert_not_called()
