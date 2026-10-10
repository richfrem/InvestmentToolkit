"""Tests for archive_temp_json.py on a throwaway temp/ folder."""
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/toolkit-manager/scripts"))

import archive_temp_json as archiver  # noqa: E402


def _file(path: Path, age_days: float, text="{}"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    stamp = time.time() - age_days * 86400
    os.utime(path, (stamp, stamp))
    return path


def test_only_old_json_directly_in_temp_and_evaluations_are_candidates(tmp_path):
    old_top = _file(tmp_path / "amat_raw.json", 30)
    old_eval = _file(tmp_path / "evaluations" / "NVDA_raw.json", 30)
    _file(tmp_path / "evaluations" / "NEW_raw.json", 1)
    _file(tmp_path / "daily_run_X" / "run_manifest.json", 30)
    _file(tmp_path / "news-sweep-responses" / "grok" / "daily.json", 30)
    _file(tmp_path / "notes.md", 30, "x")
    assert archiver.find_candidates(tmp_path, 7) == [old_top, old_eval]


def test_dry_run_moves_nothing(tmp_path):
    _file(tmp_path / "a.json", 30)
    result = archiver.archive(tmp_path, 7, move=False, today="2026-10-10")
    assert result["candidates"] == 1 and result["moved"] == 0
    assert (tmp_path / "a.json").exists() and not (tmp_path / "archive").exists()


def test_move_keeps_the_relative_path_and_content_and_deletes_nothing(tmp_path):
    _file(tmp_path / "a.json", 30, '{"k": 1}')
    _file(tmp_path / "evaluations" / "b.json", 30, '{"k": 2}')
    result = archiver.archive(tmp_path, 7, move=True, today="2026-10-10")
    assert result["moved"] == 2
    assert (tmp_path / "archive/2026-10-10/a.json").read_text() == '{"k": 1}'
    assert (tmp_path / "archive/2026-10-10/evaluations/b.json").read_text() == '{"k": 2}'
    assert not (tmp_path / "a.json").exists()


def test_a_second_run_does_not_re_archive_the_archive_or_overwrite(tmp_path):
    _file(tmp_path / "a.json", 30)
    archiver.archive(tmp_path, 7, move=True, today="2026-10-10")
    _file(tmp_path / "a.json", 30, '{"new": true}')
    result = archiver.archive(tmp_path, 7, move=True, today="2026-10-10")
    assert result["moved"] == 0
    assert (tmp_path / "archive/2026-10-10/a.json").read_text() == "{}"
