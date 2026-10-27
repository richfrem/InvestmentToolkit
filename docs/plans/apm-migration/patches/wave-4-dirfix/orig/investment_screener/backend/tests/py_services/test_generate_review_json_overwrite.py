"""generate_review_json.py --yes overwrites a same-day review without prompting,
so the closing refresh can run unattended at the end of a review session."""

import builtins
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

import generate_review_json as grj  # noqa: E402

FAKE_REVIEW = {
    "thesisName": "Investment Thesis",
    "summary": {"holdingsWithChanges": 1, "holdingsUnchanged": 0, "urgentActions": 0,
                "normalActions": 1, "lowActions": 0, "totalWeightShifted": 1.0},
}


def _prepare(tmp_path, monkeypatch, argv):
    monkeypatch.setattr(grj, "REVIEWS_DIR", tmp_path)
    monkeypatch.setattr(grj, "generate", lambda date_str: dict(FAKE_REVIEW, reviewDate=date_str))
    monkeypatch.setattr(sys, "argv", ["generate_review_json.py", "--date", "2026-10-04", *argv])
    out = tmp_path / "2026-10-04-PortfolioAnalysisRecommendations.json"
    out.write_text(json.dumps({"stale": True}))
    return out


def test_yes_overwrites_existing_same_day_file_without_prompting(tmp_path, monkeypatch):
    out = _prepare(tmp_path, monkeypatch, ["--yes"])

    def no_prompt(*_args):
        raise AssertionError("--yes must not prompt")

    monkeypatch.setattr(builtins, "input", no_prompt)
    grj.main()
    assert json.loads(out.read_text())["reviewDate"] == "2026-10-04"


def test_without_yes_an_existing_file_is_kept_when_the_user_declines(tmp_path, monkeypatch):
    out = _prepare(tmp_path, monkeypatch, [])
    monkeypatch.setattr(builtins, "input", lambda *_args: "n")
    try:
        grj.main()
    except SystemExit:
        pass
    assert json.loads(out.read_text()) == {"stale": True}
