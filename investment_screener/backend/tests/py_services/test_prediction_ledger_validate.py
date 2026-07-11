"""Tests for prediction_ledger.py's --validate mode (schema wiring)."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"


def _run_validate(predictions_content: str, graded_content: str, tmp_path, monkeypatch) -> subprocess.CompletedProcess:
    predictions_path = tmp_path / "predictions.jsonl"
    predictions_path.write_text(predictions_content)
    graded_path = tmp_path / "graded.jsonl"
    graded_path.write_text(graded_content)

    script = f'''
import sys
from pathlib import Path
sys.path.insert(0, "{PY_SERVICES}")
import prediction_ledger
prediction_ledger.PREDICTIONS_PATH = Path("{predictions_path}")
prediction_ledger.GRADED_PATH = Path("{graded_path}")
prediction_ledger.main()
'''
    return subprocess.run(
        [sys.executable, "-c", script, "--validate"], capture_output=True, text=True,
    )


class TestValidate:
    def test_valid_records_pass(self, tmp_path, monkeypatch):
        valid_prediction = json.dumps({
            "v": 1, "id": "CORZ:action_rating:2026-01-01", "date": "2026-01-01", "ticker": "CORZ",
            "type": "action_rating", "claim": {"action": "ACCUMULATE"}, "direction": "bullish",
            "horizonDays": 90, "basePrice": 5.0, "baseSpyPrice": 500.0, "confidence": None,
            "inputsHash": "abc123", "harvestedAt": "2026-01-01T00:00:00Z",
        })
        valid_grade = json.dumps({
            "v": 1, "predictionId": "CORZ:action_rating:2026-01-01", "gradedAt": "2026-04-02",
            "tickerReturn": 0.1, "spyReturn": 0.02, "relativeReturn": 0.08, "verdict": "correct",
        })
        result = _run_validate(valid_prediction + "\n", valid_grade + "\n", tmp_path, monkeypatch)
        assert result.returncode == 0
        assert "All prediction/grade records valid" in result.stdout

    def test_invalid_prediction_fails(self, tmp_path, monkeypatch):
        invalid_prediction = json.dumps({"id": "missing-required-fields"})
        result = _run_validate(invalid_prediction + "\n", "", tmp_path, monkeypatch)
        assert result.returncode == 1
        assert "INVALID prediction" in result.stdout
