"""Tests for pine_source_reader.py.

Run from repo root:
    python3 -m pytest plugins/tradingview/tests/test_pine_source_reader.py -v

Live tests (require TradingView Desktop on port 9222) are skipped automatically
when TV is not reachable.
"""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
READER_PATH = SCRIPTS_DIR / "pine_source_reader.py"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tv_is_running() -> bool:
    """Return True if TradingView Desktop is reachable on port 9222."""
    try:
        result = subprocess.run(
            ["node", str(Path(__file__).resolve().parents[3] / "tradingview-cdp" / "cli.js"), "status"],
            capture_output=True, text=True, timeout=8,
            cwd=str(Path(__file__).resolve().parents[3]),
        )
        data = json.loads(result.stdout.strip())
        return bool(data.get("success"))
    except Exception:
        return False


def _run_reader(*args: str, timeout: int = 15) -> tuple[int, str, str]:
    """Run pine_source_reader.py with given args; return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        ["python3", str(READER_PATH)] + list(args),
        capture_output=True, text=True, timeout=timeout,
        cwd=str(Path(__file__).resolve().parents[3]),
    )
    return result.returncode, result.stdout, result.stderr


SKIP_IF_TV_DOWN = unittest.skipUnless(_tv_is_running(), "TradingView Desktop not running on port 9222")


# ---------------------------------------------------------------------------
# Unit tests — no TV required
# ---------------------------------------------------------------------------

class TestSaveSource(unittest.TestCase):
    """Tests for save_source() — pure filesystem, no CDP needed."""

    def _import_save_source(self):
        spec = importlib.util.spec_from_file_location("pine_source_reader", str(READER_PATH))
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod.save_source

    def test_saves_file_with_safe_name(self):
        save_source = self._import_save_source()
        data = {"name": "SuperTrend v4 [KivancOzbilgic]", "source": "//@version=6\nindicator('ST')\n"}
        with tempfile.TemporaryDirectory() as tmp:
            path = save_source(data, Path(tmp))
            self.assertTrue(path.exists(), "File was not created")
            self.assertIn("SuperTrend_v4__KivancOzbilgic_", path.name)
            self.assertTrue(path.name.endswith(".pine"))
            self.assertEqual(path.read_text(), data["source"])

    def test_safe_name_truncated_to_60_chars(self):
        save_source = self._import_save_source()
        long_name = "A" * 100
        data = {"name": long_name, "source": "// test"}
        with tempfile.TemporaryDirectory() as tmp:
            path = save_source(data, Path(tmp))
            self.assertLessEqual(len(path.stem), 60, "Stem should be at most 60 chars")

    def test_creates_output_dir(self):
        save_source = self._import_save_source()
        data = {"name": "Test", "source": "// hello"}
        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp) / "a" / "b" / "c"
            save_source(data, nested)
            self.assertTrue(nested.exists())

    def test_special_chars_replaced(self):
        save_source = self._import_save_source()
        data = {"name": "Test: Foo/Bar [Author]", "source": "// x"}
        with tempfile.TemporaryDirectory() as tmp:
            path = save_source(data, Path(tmp))
            self.assertNotIn(":", path.name)
            self.assertNotIn("/", path.name)
            self.assertNotIn("[", path.name)


class TestCliArgParsing(unittest.TestCase):
    """Test that the CLI rejects invalid invocations without touching TV."""

    def test_no_args_exits_nonzero(self):
        code, _, _ = _run_reader()
        self.assertNotEqual(code, 0)

    def test_top_zero_produces_empty_output(self):
        code, stdout, _ = _run_reader("--top", "0")
        self.assertEqual(code, 0, stdout)
        self.assertIn("Done: 0/0", stdout)

    def test_json_flag_with_top_zero(self):
        code, stdout, _ = _run_reader("--top", "0", "--json")
        self.assertEqual(code, 0, stdout)
        parsed = json.loads(stdout.strip())
        self.assertEqual(parsed, [])

    def test_mutually_exclusive_name_and_current(self):
        code, _, stderr = _run_reader("--name", "RSI", "--current")
        self.assertNotEqual(code, 0)


# ---------------------------------------------------------------------------
# Integration tests — require TradingView Desktop
# ---------------------------------------------------------------------------

class TestFetchSourceLive(unittest.TestCase):
    """Integration tests that call the real CDP pipeline."""

    @SKIP_IF_TV_DOWN
    def test_current_returns_source(self):
        code, stdout, _err = _run_reader("--current", "--json", timeout=40)
        self.assertEqual(code, 0, stdout)
        # JSON block starts at first '[' — progress lines precede it
        json_start = stdout.find("[")
        self.assertGreater(json_start, -1, "No JSON array in output")
        results = json.loads(stdout[json_start:])
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertTrue(r.get("success"), r)
        self.assertIn("//@version=", r.get("source", ""))

    @SKIP_IF_TV_DOWN
    def test_name_saves_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, stdout, _err = _run_reader(
                "--name", "SuperTrend", "--out", tmp, timeout=60
            )
            self.assertEqual(code, 0, stdout)
            files = list(Path(tmp).glob("*.pine"))
            self.assertGreater(len(files), 0, "No .pine file saved")
            source = files[0].read_text()
            self.assertIn("//@version=", source, "Source missing version declaration")


if __name__ == "__main__":
    unittest.main()
