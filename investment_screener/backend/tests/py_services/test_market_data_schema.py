import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import get_fundamentals  # noqa: E402

SCHEMA = json.loads((REPO_ROOT / "schemas/market_data_response.schema.json").read_text())


def test_get_fundamentals_output_matches_schema(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    edgar_facts = {
        "revenue": {"value": 391035000000.0, "asOf": "2025-11-01"},
        "netIncome": {"value": 93736000000.0, "asOf": "2025-11-01"},
    }
    fake_yf = MagicMock()
    fake_yf.info = {"totalRevenue": 391000000000.0, "netIncomeToCommon": 93700000000.0}
    with patch("market_data.get_company_facts", return_value=edgar_facts), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    jsonschema.validate(instance=result, schema=SCHEMA["definitions"]["fundamentals"], resolver=jsonschema.RefResolver.from_schema(SCHEMA))
