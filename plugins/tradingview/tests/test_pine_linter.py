"""Tests for pine_linter.py.

Run from repo root:
    python3 -m pytest plugins/tradingview/tests/test_pine_linter.py -v
"""

import subprocess
import tempfile
import os
import unittest

LINTER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "pine_linter.py"
)


def run_linter(script_content: str):
    """Write content to a temp .pine file, run the linter, return (exit_code, stdout)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pine", delete=False) as tmp:
        tmp.write(script_content)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["python3", LINTER_PATH, tmp_path],
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout
    finally:
        os.remove(tmp_path)


class TestPineLinterPassing(unittest.TestCase):

    def test_valid_perfect_script(self):
        code, stdout = run_linter(
            """//@version=6
indicator("Perfect Script", overlay=true)
var float my_ma = ta.sma(close, 14)
// request.security(syminfo.tickerid, "1D", close) -- commented should not trigger
var my_label = label.new(bar_index, high, "Top")
my_ma := close
"""
        )
        self.assertEqual(code, 0, stdout)
        self.assertIn("Passed: Perfect Script!", stdout)

    def test_strategy_declaration_accepted(self):
        code, stdout = run_linter(
            """//@version=6
strategy("My Strat", overlay=true)
"""
        )
        self.assertEqual(code, 0, stdout)

    def test_library_declaration_accepted(self):
        code, stdout = run_linter(
            """//@version=6
library("MyLib")
"""
        )
        self.assertEqual(code, 0, stdout)


class TestPineLinterErrors(unittest.TestCase):

    def test_missing_version(self):
        code, stdout = run_linter(
            """indicator("No Version")
plot(close)
"""
        )
        self.assertEqual(code, 1, stdout)
        self.assertIn("Missing version declaration", stdout)

    def test_wrong_version(self):
        code, stdout = run_linter(
            """//@version=5
indicator("Old Version")
plot(close)
"""
        )
        self.assertEqual(code, 1, stdout)
        self.assertIn("must use //@version=6", stdout)

    def test_missing_declaration(self):
        code, stdout = run_linter(
            """//@version=6
plot(close)
"""
        )
        self.assertEqual(code, 1, stdout)
        self.assertIn("Missing script declaration", stdout)

    def test_double_declaration(self):
        code, stdout = run_linter(
            """//@version=6
indicator("A")
strategy("B")
"""
        )
        self.assertEqual(code, 1, stdout)
        self.assertIn("2 declarations", stdout)

    def test_unsafe_request_security(self):
        code, stdout = run_linter(
            """//@version=6
strategy("Bad Lookahead")
c = request.security(syminfo.tickerid, "1D", close)
"""
        )
        self.assertEqual(code, 1, stdout)
        self.assertIn("Unsafe request.security()", stdout)

    def test_safe_request_security_passes(self):
        code, stdout = run_linter(
            """//@version=6
indicator("Safe Lookahead")
c = request.security(syminfo.tickerid, "1D", close, lookahead=barmerge.lookahead_off)
"""
        )
        self.assertEqual(code, 0, stdout)

    def test_strict_boolean_na(self):
        code, stdout = run_linter(
            """//@version=6
indicator("Bad Bool")
val = na(close > open) ? 1 : 0
"""
        )
        self.assertEqual(code, 1, stdout)
        self.assertIn("Cannot pass boolean expressions to na()", stdout)


class TestPineLinterWarnings(unittest.TestCase):

    def test_drawing_without_var_warns(self):
        code, stdout = run_linter(
            """//@version=6
indicator("Drawing Warning")
my_label = label.new(bar_index, high, "Top")
"""
        )
        self.assertEqual(code, 0, stdout)
        self.assertIn("[WARNING]", stdout)
        self.assertIn("without 'var'", stdout)

    def test_drawing_with_var_no_warning(self):
        _, stdout = run_linter(
            """//@version=6
indicator("Drawing OK")
var my_label = label.new(bar_index, high, "Top")
"""
        )
        self.assertNotIn("Drawing object", stdout)

    def test_comment_does_not_trigger_errors(self):
        """Commented-out request.security must not fire the error."""
        code, stdout = run_linter(
            """//@version=6
indicator("Comment Safe")
// c = request.security(syminfo.tickerid, "1D", close)
"""
        )
        self.assertEqual(code, 0, stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
