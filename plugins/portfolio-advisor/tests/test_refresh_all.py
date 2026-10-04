"""refresh_all.run_refresh() is the one closing step every review workflow runs.

By default it only refreshes roles and the thesis pages (unchanged behaviour,
relied on by update_targets.py, update_thesis.py and the broker sync scripts).
With publish=True it also regenerates today's review JSON, republishes the
daily brief and runs the consistency check, so the Portfolio Advisor and Daily
Brief pages match what the session decided.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))

import refresh_all  # noqa: E402


def _record_runs(monkeypatch, exit_codes=None):
    calls = []

    def fake_run(script, extra_args=None):
        calls.append((Path(script).name, list(extra_args or [])))
        return (exit_codes or {}).get(Path(script).name, 0)

    monkeypatch.setattr(refresh_all, "_run", fake_run)
    return calls


THESIS_STEPS = [
    ("sync_portfolio_roles.py", []),
    ("generate_portfolio_blueprint.py", ["--write"]),
    ("generate_sub_strategy_blocks.py", []),
]
PUBLISH_STEPS = [
    ("generate_review_json.py", ["--yes"]),
    ("daily_brief.py", ["--skip-ta"]),
    ("verify_refresh.py", []),
]


def test_default_refresh_runs_only_the_thesis_steps(monkeypatch):
    calls = _record_runs(monkeypatch)
    assert refresh_all.run_refresh() == 0
    assert calls == THESIS_STEPS


def test_publish_adds_review_json_brief_and_verify_after_the_thesis_steps(monkeypatch):
    calls = _record_runs(monkeypatch)
    assert refresh_all.run_refresh(publish=True) == 0
    assert calls == THESIS_STEPS + PUBLISH_STEPS


def test_publish_keeps_going_and_reports_failure_when_a_step_fails(monkeypatch):
    calls = _record_runs(monkeypatch, exit_codes={"daily_brief.py": 2})
    assert refresh_all.run_refresh(publish=True) == 2
    assert [name for name, _ in calls][-1] == "verify_refresh.py"


def test_publish_flag_on_the_command_line(monkeypatch):
    calls = _record_runs(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["refresh_all.py", "--publish"])
    try:
        refresh_all.main()
    except SystemExit as exit_info:
        assert exit_info.code == 0
    assert calls == THESIS_STEPS + PUBLISH_STEPS
