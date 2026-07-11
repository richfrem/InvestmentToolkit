"""Tests for daily_brief.py's E3 prediction-harvest integration."""
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
SCRIPTS_DIR = REPO_ROOT / "plugins/portfolio-advisor/scripts"
sys.path.insert(0, str(PY_SERVICES))
sys.path.insert(0, str(SCRIPTS_DIR))

import daily_brief  # noqa: E402


class TestHarvestPredictionsStep:
    @patch("harvest_predictions.harvest_rebalance_and_breaker_claims", return_value=[])
    @patch("harvest_predictions.harvest_action_and_dcf_claims", return_value=[{"id": "A"}, {"id": "B"}])
    def test_returns_total_harvested_count(self, _mock_action_dcf, _mock_rebalance_breaker):
        result = daily_brief._harvest_predictions_step()
        assert result == 2

    @patch("harvest_predictions.harvest_action_and_dcf_claims", side_effect=RuntimeError("boom"))
    def test_degrades_to_none_on_failure(self, _mock_action_dcf):
        result = daily_brief._harvest_predictions_step()
        assert result is None
